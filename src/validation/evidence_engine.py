"""DEV-only statistical evidence and rejection engine for preregistered hypotheses."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

from src.experience_store.parquet_store import ParquetExperienceStore
from src.orchestrator.state_machine import utc_now
from src.research.evidence_registry import EvidenceRegistry
from src.research.skeptic_engine import run_skeptic
from src.utils.serialization import read_json
from src.validation.bootstrap import block_bootstrap, session_bootstrap
from src.validation.cost_stress import cost_stability, stressed_return
from src.validation.multiple_testing import benjamini_hochberg
from src.validation.oos import PartitionGuard
from src.validation.permutation import session_permutation_test
from src.validation.stability import stability_summary


DATA_COLUMNS = [
    "experience_id", "session_id", "decision_timestamp_utc", "action", "partition",
    "state_minute_of_session", "state_regime_v0", "state_volatility_15m_causal",
    "state_volatility_60m_causal", "state_bar_range", "state_atr_14_causal", "state_tick_volume",
    "state_return_5m", "state_return_15m", "state_return_30m", "state_return_60m",
    "state_distance_recent_high", "state_distance_recent_low", "state_spread_points",
    "label_realized_volatility_15m", "label_realized_volatility_30m", "label_realized_volatility_60m",
    "label_up_excursion_30m", "label_down_excursion_30m",
    "outcome_gross_return_15m", "outcome_tradable_return_15m", "cost_spread_return_15m",
    "outcome_gross_return_30m", "outcome_tradable_return_30m", "cost_spread_return_30m",
    "outcome_gross_return_60m", "outcome_tradable_return_60m", "cost_spread_return_60m",
]


class EvidenceEngine:
    def __init__(self, project_root: Path | str, *, bootstrap_resamples: int = 2000,
                 permutations: int = 4000, seed: int = 20260903):
        self.root = Path(project_root); self.store = ParquetExperienceStore(self.root)
        self.registry = EvidenceRegistry(self.root); self.guard = PartitionGuard(self.root, "DISCOVERY")
        self.bootstrap_resamples = bootstrap_resamples; self.permutations = permutations; self.seed = seed
        self._cache: dict[str, pd.DataFrame] = {}

    def _data(self, action: str) -> pd.DataFrame:
        self.guard.require("DEV", "EvidenceEngine")
        if action not in self._cache:
            self._cache[action] = self.store.query(partitions=("DEV",), action=action, columns=DATA_COLUMNS)
        return self._cache[action].copy()

    @staticmethod
    def _mask(frame: pd.DataFrame, condition: dict[str, Any], override: float | int | None = None,
              resolved_threshold: float | None = None) -> tuple[pd.Series, float | None]:
        kind = condition["type"]; field = condition.get("field")
        if kind == "minute_equals":
            value = int(condition["value"] if override is None else override)
            return frame[field].eq(value), float(value)
        if kind == "minute_range":
            start, end = condition["start"], condition["end"]
            if override is not None: end = override
            return frame[field].between(start, end), float(end)
        if kind == "quantile_gte":
            quantile = float(condition["quantile"] if override is None else override)
            threshold = float(frame[field].quantile(quantile)) if resolved_threshold is None else resolved_threshold
            return frame[field].ge(threshold), threshold
        if kind == "quantile_lte":
            quantile = float(condition["quantile"] if override is None else override)
            threshold = float(frame[field].quantile(quantile)) if resolved_threshold is None else resolved_threshold
            return frame[field].le(threshold), threshold
        if kind == "field_equals":
            return frame[field].eq(condition["value"]), None
        if kind == "all":
            combined = pd.Series(True, index=frame.index)
            for clause in condition["clauses"]:
                clause_mask, _ = EvidenceEngine._mask(frame, clause)
                combined &= clause_mask
            return combined, None
        if kind == "session_hash_mod":
            modulus = int(condition.get("modulus", 10)); remainder = int(condition.get("remainder", 0))
            hashed = pd.util.hash_pandas_object(frame["session_id"], index=False, hash_key="0123456789123456")
            return (hashed % modulus).eq(remainder), float(remainder)
        raise ValueError(f"Unsupported condition: {kind}")

    @staticmethod
    def _samples(frame: pd.DataFrame, mask: pd.Series, target: str) -> dict[str, Any]:
        usable = frame.loc[frame[target].notna(), ["session_id", target]].copy()
        usable["condition"] = mask.loc[usable.index].astype(bool).to_numpy()
        grouped = usable.groupby(["session_id", "condition"], sort=True)[target].mean().unstack()
        if True not in grouped or False not in grouped: raise ValueError("Condition or base rate is empty")
        paired_rows = grouped.dropna(subset=[False, True])
        if len(paired_rows) >= max(20, int(0.25*len(grouped))):
            effects = (paired_rows[True]-paired_rows[False]).to_numpy(dtype=float)
            return {"paired": True, "effects": effects, "conditioned": paired_rows[True].to_numpy(),
                    "baseline": paired_rows[False].to_numpy(), "sessions": len(paired_rows), "rows": len(usable)}
        conditioned = grouped[True].dropna().to_numpy(dtype=float); baseline = grouped[False].dropna().to_numpy(dtype=float)
        effects = np.concatenate([conditioned-baseline.mean(), conditioned.mean()-baseline])
        return {"paired": False, "effects": effects, "conditioned": conditioned, "baseline": baseline,
                "sessions": len(conditioned)+len(baseline), "rows": len(usable)}

    @staticmethod
    def _effect(samples: dict[str, Any]) -> float:
        return float(samples["effects"].mean()) if samples["paired"] else float(samples["conditioned"].mean()-samples["baseline"].mean())

    def _effect_for(self, frame: pd.DataFrame, condition: dict, target: str,
                    override: float | int | None = None, threshold: float | None = None) -> float:
        mask, _ = self._mask(frame, condition, override, threshold)
        return self._effect(self._samples(frame, mask, target))

    def evaluate_hypothesis(self, specification: dict[str, Any]) -> dict[str, Any]:
        record = self.registry.register(specification); self.registry.update_status(record["id"], "TESTING")
        frame = self._data(record.get("action", "WAIT")); target = record["target_variable"]
        if target not in frame: raise ValueError(f"Target is not permitted: {target}")
        mask, threshold = self._mask(frame, record["condition"])
        samples = self._samples(frame, mask, target); effect = self._effect(samples)
        support = {"condition_rows": int(mask.sum()), "condition_sessions": int(frame.loc[mask, "session_id"].nunique()),
                   "condition_years": int(frame.loc[mask, "decision_timestamp_utc"].dt.year.nunique()),
                   "minimum_rows": int(record.get("minimum_rows", 500)),
                   "minimum_sessions": int(record.get("minimum_sessions", 50)),
                   "minimum_years": int(record.get("minimum_years", 3))}
        support["passed"] = (support["condition_rows"] >= support["minimum_rows"]
                             and support["condition_sessions"] >= support["minimum_sessions"]
                             and support["condition_years"] >= support["minimum_years"])
        direction = record["expected_direction"]
        bootstrap = session_bootstrap(samples["effects"] if samples["paired"] else samples["conditioned"],
                                      None if samples["paired"] else samples["baseline"], paired=samples["paired"],
                                      resamples=self.bootstrap_resamples, seed=self.seed, direction=direction)
        block = block_bootstrap(samples["effects"], block_size=min(20, max(2, len(samples["effects"])//5)),
                                resamples=self.bootstrap_resamples, seed=self.seed+1, direction=direction)
        permutation = session_permutation_test(samples["effects"] if samples["paired"] else samples["conditioned"],
                                               None if samples["paired"] else samples["baseline"], paired=samples["paired"],
                                               permutations=self.permutations, seed=self.seed+2, direction=direction)
        within_adjusted = min(1.0, permutation["p_value"]*int(record["planned_comparisons"]))
        prior = [min(1.0, float(x["last_nominal_p"])*int(x["planned_comparisons"])) for x in self.registry.repo.all()
                 if x["id"] != record["id"] and x.get("last_nominal_p") is not None]
        adjusted = benjamini_hochberg([*prior, within_adjusted])[-1]

        timestamps = frame["decision_timestamp_utc"]
        temporal_effects = {}
        for year in range(2015, 2020):
            subset = frame[timestamps.dt.year.eq(year)]
            if len(subset):
                try: temporal_effects[str(year)] = self._effect_for(subset, record["condition"], target, threshold=threshold)
                except ValueError: pass
        for year in range(2015, 2020):
            for half, months in (("H1", range(1, 7)), ("H2", range(7, 13))):
                subset = frame[timestamps.dt.year.eq(year) & timestamps.dt.month.isin(months)]
                if len(subset):
                    try: temporal_effects[f"{year}-{half}"] = self._effect_for(subset, record["condition"], target, threshold=threshold)
                    except ValueError: pass
        temporal = stability_summary(temporal_effects, direction)
        regime_effects = {}
        for regime, subset in frame.groupby("state_regime_v0"):
            try: regime_effects[str(regime)] = self._effect_for(subset, record["condition"], target, threshold=threshold)
            except ValueError: pass
        regime = stability_summary(regime_effects, direction)

        if target.startswith("outcome_tradable_return_"):
            horizon = int(target.rsplit("_", 1)[1][:-1]); cost_effects = {}
            for multiplier in (1.0, 1.25, 1.5, 2.0):
                stressed = frame.copy(); stressed["_stressed"] = stressed_return(stressed, horizon, multiplier)
                cost_effects[multiplier] = self._effect_for(stressed, record["condition"], "_stressed", threshold=threshold)
            costs = {"applicable": True, **cost_stability(cost_effects, direction)}
        else:
            costs = {"applicable": False, "reason": "Target is not a tradable return", "favorable_proportion": 1.0, "survives_2x": True}

        parameter_effects = {"declared": effect}
        for neighbor in record.get("parameter_neighbors", []):
            try: parameter_effects[str(neighbor)] = self._effect_for(frame, record["condition"], target, override=neighbor)
            except ValueError: pass
        parameters = stability_summary(parameter_effects, direction)

        shifted = frame.copy(); shifted[target] = shifted.groupby("state_minute_of_session")[target].shift(7)
        shifted_effect = self._effect_for(shifted, record["condition"], target, threshold=threshold)
        random_mask, _ = self._mask(frame, {"type": "session_hash_mod", "modulus": 10, "remainder": 3})
        random_effect = self._effect(self._samples(frame, random_mask, target))
        negative_controls = {"timestamp_shift_7_sessions_effect": shifted_effect,
                             "deterministic_random_session_condition_effect": random_effect,
                             "permuted_sessions_p_value": permutation["p_value"]}
        negative_limit = .5*max(abs(effect), 1e-12)
        negative_control_passed = abs(shifted_effect) <= negative_limit and abs(random_effect) <= negative_limit
        negative_controls["maximum_allowed_absolute_effect"] = negative_limit
        negative_controls["passed"] = negative_control_passed
        quality_report = self.store.data_engine.manifest(self.store.manifest["data_engine_dataset_id"])["quality"]
        data_quality = {"blocking_errors": quality_report["status"] in ("REJECTED", "EXPLORATORY_ONLY"),
                        "target_null_fraction": float(frame[target].isna().mean()),
                        "gaps_not_imputed": True, "incomplete_sessions_flagged": quality_report["counts"].get("GAP", 0),
                        "data_engine_dataset_id": self.store.manifest["data_engine_dataset_id"]}
        skeptic = run_skeptic(samples["effects"], temporal=temporal, cost=costs, data_quality=data_quality, direction=direction)
        minimum = float(record.get("minimum_effect", 0.0)); favorable = effect > 0 if direction == "GREATER" else effect < 0
        economic = abs(effect) >= minimum
        components = {"effect_size": min(1.0, abs(effect)/(minimum or max(abs(effect), 1e-12))),
                      "bootstrap_stability": bootstrap["favorable_resample_proportion"],
                      "temporal_stability": temporal["favorable_proportion"], "cost_robustness": costs["favorable_proportion"],
                      "multiple_testing": 1-adjusted, "sample_size": min(1.0, samples["sessions"]/200),
                      "data_quality": 0.0 if data_quality["blocking_errors"] else 1.0,
                      "parameter_stability": parameters["favorable_proportion"],
                      "negative_controls": 1.0 if negative_control_passed else 0.0}
        weights = {"effect_size": .10, "bootstrap_stability": .15, "temporal_stability": .15, "cost_robustness": .10,
                   "multiple_testing": .15, "sample_size": .05, "data_quality": .10, "parameter_stability": .10,
                   "negative_controls": .10}
        score = sum(components[k]*weights[k] for k in weights)
        survives = (favorable and economic and adjusted <= 0.05 and bootstrap["favorable_resample_proportion"] >= .9
                    and temporal["favorable_proportion"] >= .6 and parameters["favorable_proportion"] >= .6
                    and skeptic["survival_proportion"] >= .65 and samples["sessions"] >= 50
                    and negative_control_passed and support["passed"])
        verdict = "DEV_SURVIVOR" if survives and not record.get("negative_control", False) else "REJECTED"
        reasons = []
        if not favorable: reasons.append("effect_direction_failed")
        if not economic: reasons.append("economic_materiality_failed")
        if adjusted > .05: reasons.append("multiple_testing_failed")
        if temporal["favorable_proportion"] < .6: reasons.append("temporal_stability_failed")
        if parameters["favorable_proportion"] < .6: reasons.append("parameter_stability_failed")
        if not negative_control_passed: reasons.append("negative_control_failed")
        if not support["passed"]: reasons.append("minimum_support_failed")
        if record.get("negative_control", False): reasons.append("negative_control_not_eligible")
        unit = record.get("effect_unit", "raw")
        report = {"evidence_report_id": f"EVIDENCE-{record['id'].split('-', 1)[1]}", "created_at": utc_now(),
                  "hypothesis_id": record["id"], "spec_hash": record["spec_hash"], "dataset_version": self.store.dataset_version,
                  "partition": "DEV", "validation_inspected": False, "locked_oos_inspected": False,
                  "effect_size": {"value": effect, "unit": unit, "basis_points": effect*10000 if "return" in target else None,
                                  "minimum_material_effect": minimum},
                  "uncertainty": float(bootstrap["confidence_interval_95"][1]-bootstrap["confidence_interval_95"][0]),
                  "confidence_interval": {"90": bootstrap["confidence_interval_90"], "95": bootstrap["confidence_interval_95"]},
                  "p_value": permutation["p_value"], "within_hypothesis_adjusted_p": within_adjusted,
                  "multiple_testing_adjusted_p": adjusted,
                  "multiple_testing": {"method": "planned-comparison penalty then Benjamini-Hochberg FDR",
                                       "planned_comparisons": record["planned_comparisons"],
                                       "global_hypotheses": len(prior)+1,
                                       "strict_control_note": "Use Holm/Bonferroni when any false positive is unacceptable or the family is small and confirmatory."},
                  "bootstrap_stability": bootstrap, "block_bootstrap": block, "permutation": permutation,
                  "temporal_stability": temporal, "regime_stability": regime, "cost_stability": costs,
                  "parameter_stability": parameters, "negative_controls": negative_controls,
                  "sample_size": {"rows": samples["rows"], "sessions": samples["sessions"], "paired": samples["paired"],
                                  "conditioned_sessions": len(samples["conditioned"]), "baseline_sessions": len(samples["baseline"])},
                  "support": support,
                  "base_rate": {"conditioned": float(np.mean(samples["conditioned"])),
                                "baseline": float(np.mean(samples["baseline"])),
                                "full": float(frame[target].mean())},
                  "data_quality": data_quality, "skeptic": skeptic,
                  "evidence_score": {"value": round(float(score), 6), "components": components, "weights": weights,
                                     "interpretation": "Research evidence only; never a trading decision"},
                  "verdict": verdict, "rejection_reasons": reasons,
                  "state_transition_limit": "At most VALIDATION_READY; never VALIDATED in discovery"}
        artifact = self.registry.record_report(record["id"], report)
        self.registry.update_status(record["id"], verdict, last_evidence_artifact=str(artifact.relative_to(self.root)).replace("\\", "/"),
                                    last_adjusted_p=adjusted, evidence_score=report["evidence_score"]["value"], rejection_reasons=reasons)
        if verdict == "DEV_SURVIVOR" and record.get("request_validation_ready", False):
            self.registry.preregister_validation(record["id"], artifact); report["verdict"] = "VALIDATION_READY"
        return report


def evaluate_hypothesis(project_root: Path | str, hypothesis: dict[str, Any]) -> dict[str, Any]:
    return EvidenceEngine(project_root).evaluate_hypothesis(hypothesis)
