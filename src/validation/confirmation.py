"""One-shot, fail-closed confirmation of frozen DEV hypotheses on VALIDATION.

This module deliberately has no discovery or parameter-search entry point.  DEV
is used only to verify the frozen evidence and materialize its declared quantile
as a numeric threshold before the protocol is hashed.  One authorization then
loads VALIDATION once.  LOCKED_OOS is never an accepted argument.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import math
import numpy as np
import pandas as pd

from src.experience_store.parquet_store import ParquetExperienceStore
from src.memory.long_term_memory import LongTermMemory
from src.memory.semantic_memory import SemanticMemory
from src.orchestrator.state_machine import StateStore, utc_now
from src.research.evidence_registry import EvidenceRegistry, OPTIONAL_SCIENTIFIC, REQUIRED
from src.research.hypothesis_generator import HypothesisGenerator
from src.utils.hashing import content_hash, file_hash
from src.utils.serialization import atomic_write_json, read_json
from src.validation.bootstrap import block_bootstrap, session_bootstrap, stationary_bootstrap
from src.validation.multiple_testing import benjamini_hochberg, holm_bonferroni
from src.validation.oos import PartitionGuard
from src.validation.permutation import session_permutation_test
from src.validation.skeptic import run_skeptic

CANDIDATES = (
    "HYPOTHESIS-DISC-09-UP_MOVE_REVERSES-V1",
    "HYPOTHESIS-DISC-10-DOWN_MOVE_REVERSES-V1",
    "HYPOTHESIS-DISC-15-NEAR_HIGH_REVERTS-V1",
    "HYPOTHESIS-DISC-16-NEAR_LOW_REVERTS-V1",
)

VALIDATION_COLUMNS = [
    "experience_id", "session_id", "decision_timestamp_utc", "action", "partition", "state_minute_of_session",
    "state_regime_v0", "state_return_15m", "state_distance_recent_high",
    "state_distance_recent_low", "outcome_gross_return_15m", "outcome_tradable_return_15m",
    "outcome_mfe_15m", "outcome_mae_15m", "cost_spread_return_15m", "cost_method_15m",
    "outcome_gross_return_30m", "outcome_tradable_return_30m", "outcome_mfe_30m",
    "outcome_mae_30m", "cost_spread_return_30m", "cost_method_30m",
]


def replication_ratio(validation_effect: float, dev_effect: float) -> float | None:
    return float(validation_effect/dev_effect) if dev_effect and math.isfinite(dev_effect) else None


def quarantine_post_validation_observation(project_root: Path | str, *, hypothesis_id: str,
                                           observation: str) -> dict[str, Any]:
    """Record a note without testing it or feeding it back into discovery."""
    root=Path(project_root); path=root/"reports/validation/POST_VALIDATION_OBSERVATIONS.json"
    document=read_json(path,{"status":"QUARANTINED","observations":[],
        "policy":"Notes are not confirmatory evidence and must return to DEV as NEW_HYPOTHESIS before testing",
        "validation_reuse_allowed":False,"discovery_feedback_allowed":False})
    payload={"hypothesis_id":hypothesis_id,"observation":observation,"status":"POST_VALIDATION_OBSERVATION",
             "tested":False,"created_at":utc_now()}
    payload["observation_hash"]=content_hash({k:v for k,v in payload.items() if k not in {"created_at","observation_hash"}})
    if not any(x.get("observation_hash")==payload["observation_hash"] for x in document["observations"]):
        document["observations"].append(payload)
    atomic_write_json(path,document)
    return payload


def _scientific(record: dict[str, Any]) -> dict[str, Any]:
    keys = ("id", *REQUIRED, *OPTIONAL_SCIENTIFIC)
    return {key: record[key] for key in keys if key in record}


def _stable_document(path: Path, payload: dict[str, Any], hash_field: str) -> dict[str, Any]:
    scientific = {k: v for k, v in payload.items() if k not in {hash_field, "created_at"}}
    digest = content_hash(scientific)
    document = {**scientific, hash_field: digest, "created_at": utc_now()}
    if path.exists():
        old = read_json(path, {})
        old_scientific = {k: v for k, v in old.items() if k not in {hash_field, "created_at"}}
        if old_scientific != scientific or old.get(hash_field) != digest:
            raise PermissionError(f"Immutable ceremony document changed: {path.name}")
        return old
    atomic_write_json(path, document)
    return document


def _fixed_mask(frame: pd.DataFrame, condition: dict[str, Any], threshold: float) -> pd.Series:
    field = condition["field"]
    if condition["type"] == "quantile_gte": return frame[field].ge(threshold)
    if condition["type"] == "quantile_lte": return frame[field].le(threshold)
    raise ValueError("Confirmation accepts only the four frozen quantile conditions")


def _samples(frame: pd.DataFrame, mask: pd.Series, target: str) -> dict[str, Any]:
    usable = frame.loc[frame[target].notna(), ["session_id", target]].copy()
    usable["condition"] = mask.loc[usable.index].astype(bool).to_numpy()
    grouped = usable.groupby(["session_id", "condition"], sort=True)[target].mean().unstack()
    if True not in grouped or False not in grouped: raise ValueError("Condition or base rate is empty")
    paired = grouped.dropna(subset=[False, True])
    if len(paired) < 20: raise ValueError("Insufficient paired sessions")
    return {"effects": (paired[True]-paired[False]).to_numpy(float),
            "conditioned": paired[True].to_numpy(float), "baseline": paired[False].to_numpy(float),
            "sessions": int(len(paired)), "rows": int(len(usable))}


def _effect_for(frame: pd.DataFrame, mask: pd.Series, target: str) -> float:
    return float(np.mean(_samples(frame, mask, target)["effects"]))


class ValidationCeremony:
    def __init__(self, project_root: Path | str, *, bootstrap_resamples: int = 2000,
                 permutations: int = 4000, seed: int = 20260903):
        self.root = Path(project_root)
        self.registry = EvidenceRegistry(self.root)
        self.store = ParquetExperienceStore(self.root)
        self.guard = PartitionGuard(self.root, "VALIDATION")
        self.bootstrap_resamples = bootstrap_resamples
        self.permutations = permutations
        self.seed = seed
        self.output = self.root / "reports/validation"
        self.manifest_path = self.output / "VALIDATION_CEREMONY_MANIFEST.json"
        self.protocol_path = self.output / "VALIDATION_CEREMONY_PROTOCOL.json"
        self.result_path = self.output / "PROMPT_6_VALIDATION_CEREMONY.json"
        self.state_path = self.root / "state/validation_ceremony_state.json"

    def prepare(self) -> tuple[dict[str, Any], dict[str, Any]]:
        # Integrity checks do not open any market partition.
        records = {r["id"]: r for r in self.registry.repo.all()}
        generated = {r["id"]: r for r in HypothesisGenerator(self.root).generate(24, include_existing_campaign=True)}
        verified = []
        for identifier in CANDIDATES:
            record = records.get(identifier)
            if not record or record.get("status") != "VALIDATION_READY":
                raise PermissionError(f"{identifier} is not VALIDATION_READY")
            scientific = _scientific(record)
            regenerated = _scientific(generated.get(identifier, {}))
            if regenerated != scientific:
                raise PermissionError(f"Frozen specification differs from deterministic source: {identifier}")
            prereg_path = self.root / record["validation_preregistration"]
            prereg = read_json(prereg_path, {})
            evidence_path = self.root / prereg.get("evidence_artifact", "__missing__")
            safe = (prereg.get("hypothesis_id") == identifier and prereg.get("spec_hash") == record["spec_hash"]
                    and prereg.get("partition_authorized") == "VALIDATION"
                    and prereg.get("locked_oos_authorized") is False and evidence_path.is_file()
                    and file_hash(evidence_path) == prereg.get("evidence_hash"))
            evidence = read_json(evidence_path, {}) if evidence_path.is_file() else {}
            safe = safe and evidence.get("spec_hash") == record["spec_hash"] and evidence.get("partition") == "DEV"
            if not safe: raise PermissionError(f"Frozen preregistration integrity failed: {identifier}")
            verified.append((record, scientific, prereg_path, prereg, evidence_path, evidence))

        # Resolve declared quantiles from DEV, never from VALIDATION.
        discovery_guard = PartitionGuard(self.root, "DISCOVERY")
        thresholds: dict[str, float] = {}
        for action in sorted({item[0]["action"] for item in verified}):
            discovery_guard.require("DEV", "ValidationCeremony.threshold_materialization")
            fields = sorted({item[0]["condition"]["field"] for item in verified if item[0]["action"] == action})
            frame = self.store.query(partitions=("DEV",), action=action, columns=["action", *fields])
            for record, *_ in [item for item in verified if item[0]["action"] == action]:
                condition = record["condition"]
                thresholds[record["id"]] = float(frame[condition["field"]].quantile(float(condition["quantile"])))

        candidates = []
        for record, scientific, prereg_path, prereg, evidence_path, evidence in verified:
            candidates.append({
                "hypothesis_id": record["id"], "spec_hash": record["spec_hash"],
                "current_scientific_snapshot_hash": content_hash(scientific),
                "legacy_hash_note": "spec_hash remains the immutable creation-time hash; snapshot hash covers the normalized current scientific fields",
                "preregistration_path": str(prereg_path.relative_to(self.root)).replace("\\", "/"),
                "preregistration_file_hash": file_hash(prereg_path),
                "dev_evidence_path": str(evidence_path.relative_to(self.root)).replace("\\", "/"),
                "dev_evidence_hash": prereg["evidence_hash"], "dev_effect": evidence["effect_size"]["value"],
                "condition": record["condition"], "resolved_dev_threshold": thresholds[record["id"]],
                "action": record["action"], "target": record["target_variable"],
                "primary_metric": record["primary_metric"], "secondary_metrics": record["secondary_metrics"],
                "expected_direction": record["expected_direction"], "minimum_effect": record["minimum_effect"],
                "cost_rule": "frozen V2 gross minus recorded spread cost; slippage unavailable, never assumed zero",
                "success_criteria": "all predictive gates in the hashed ceremony protocol",
                "rejection_criteria": "any mandatory predictive gate fails",
                "frozen_scientific_specification": scientific,
            })
        manifest = _stable_document(self.manifest_path, {
            "ceremony_id": "VALIDATION-CEREMONY-REVERSAL-RELATIVE-V1",
            "family": "REVERSAL_RELATIVE_V1", "dataset_version": self.store.dataset_version,
            "dataset_validation_hash_expected": self.store.manifest["file_hashes"]["VALIDATION"],
            "candidates": candidates, "integrity_verified": True,
            "validation_read_before_manifest": False, "locked_oos_authorized": False,
        }, "manifest_hash")
        protocol = _stable_document(self.protocol_path, {
            "ceremony_id": manifest["ceremony_id"], "manifest_hash": manifest["manifest_hash"],
            "family": "REVERSAL_RELATIVE_V1", "number_of_hypotheses": 4, "partition": "VALIDATION",
            "period": {"from": "2020-01-01T00:00:00Z", "to_exclusive": "2023-01-01T00:00:00Z"},
            "primary_metric": "paired session-weighted difference in mean net tradable return: frozen condition minus same-session complement",
            "secondary_metrics": ["gross/net conditional return", "spread cost", "MFE", "MAE", "hit rate", "payoff", "frequency", "regime stability"],
            "expected_direction": "GREATER for all four frozen effects", "confidence_intervals": [0.90, 0.95],
            "bootstrap": {"session_resamples": self.bootstrap_resamples, "moving_block_resamples": self.bootstrap_resamples,
                          "stationary_resamples": self.bootstrap_resamples, "mean_or_fixed_block_sessions": 20},
            "permutation": {"method": "paired session sign flip", "permutations": self.permutations},
            "multiple_testing": {"primary": "Holm family-wise correction", "complementary": "Benjamini-Hochberg FDR", "alpha": 0.05},
            "predictive_replication_gate": {"same_direction": True, "ci95_lower_bound_gt": 0.0, "holm_p_lte": 0.05,
                "bootstrap_favorable_gte": 0.90, "sign_stability_gte": 0.90, "minimum_rows": 5000,
                "minimum_sessions": 200, "minimum_years": 3, "temporal_sign_consistency_gte": 0.60,
                "year_concentration_lte": 0.60, "skeptic_survival_gte": 0.75, "slow_structure_control_required": True},
            "economic_gate": {"absolute_conditional_net_return_gt": 0.0,
                              "note": "positive relative effect alone never passes this gate"},
            "temporal_windows": ["2020", "2020-H1", "2020-H2", "2021", "2021-H1", "2021-H2", "2022", "2022-H1", "2022-H2"],
            "regimes": ["RANGE", "TREND_UP", "TREND_DOWN"], "cost_multipliers": [1.0, 1.25, 1.5, 2.0],
            "skeptic_tests": ["winsorization", "remove_best_5pct", "remove_worst_5pct", "temporal_concentration",
                "outlier_dependency", "gap_sensitivity", "data_quality", "2x_cost", "shift_7_sessions_slow_structure"],
            "rejection_rule": "VALIDATION_FAILED if any predictive gate fails; no rescue or mutation",
            "verdicts": ["VALIDATION_FAILED", "VALIDATED_PREDICTIVE_RELATIONSHIP_NO_TRADE", "VALIDATED_ECONOMIC_CANDIDATE"],
            "prohibitions": ["discovery", "parameter search", "threshold mutation", "subgroup selection", "LOCKED_OOS", "EA", "orders", "live promotion"],
        }, "protocol_hash")
        state = read_json(self.state_path, {})
        if state and (state.get("manifest_hash") != manifest["manifest_hash"] or state.get("protocol_hash") != protocol["protocol_hash"]):
            raise PermissionError("Ceremony state does not match immutable manifest/protocol")
        if not state:
            atomic_write_json(self.state_path, {"status": "PREPARED", "manifest_hash": manifest["manifest_hash"],
                "protocol_hash": protocol["protocol_hash"], "validation_authorizations": 0,
                "validation_dataset_reads": 0, "locked_oos_reads": 0, "prepared_at": utc_now()})
        return manifest, protocol

    def _confirm_frozen_hypothesis(self, frame: pd.DataFrame, candidate: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
        record = candidate["frozen_scientific_specification"]
        action_frame = frame.loc[frame["action"].eq(candidate["action"])].copy()
        target = candidate["target"]; horizon = int(target.rsplit("_", 1)[1][:-1])
        mask = _fixed_mask(action_frame, candidate["condition"], candidate["resolved_dev_threshold"])
        samples = _samples(action_frame, mask, target); effect = float(np.mean(samples["effects"]))
        direction = record["expected_direction"]
        session = session_bootstrap(samples["effects"], paired=True, resamples=self.bootstrap_resamples,
                                    seed=self.seed, direction=direction)
        block = block_bootstrap(samples["effects"], block_size=20, resamples=self.bootstrap_resamples,
                                seed=self.seed+1, direction=direction)
        stationary = stationary_bootstrap(samples["effects"], mean_block_size=20,
                                          resamples=self.bootstrap_resamples, seed=self.seed+2, direction=direction)
        permutation = session_permutation_test(samples["effects"], paired=True, permutations=self.permutations,
                                               seed=self.seed+3, direction=direction)
        temporal_effects: dict[str, float] = {}
        timestamps = action_frame["decision_timestamp_utc"]
        for year in (2020, 2021, 2022):
            groups = [(str(year), timestamps.dt.year.eq(year)),
                      (f"{year}-H1", timestamps.dt.year.eq(year)&timestamps.dt.month.le(6)),
                      (f"{year}-H2", timestamps.dt.year.eq(year)&timestamps.dt.month.gt(6))]
            for label, selector in groups:
                subset = action_frame.loc[selector]; submask = mask.loc[subset.index]
                try: temporal_effects[label] = _effect_for(subset, submask, target)
                except ValueError: pass
        favorable = {k: v > 0 for k, v in temporal_effects.items()}
        years = {k: v for k, v in temporal_effects.items() if "-H" not in k}
        denom = sum(abs(v) for v in years.values())
        temporal = {"effects": temporal_effects, "favorable": favorable,
                    "sign_consistency": sum(favorable.values())/len(favorable) if favorable else 0.0,
                    "effect_dispersion": float(np.std(list(temporal_effects.values()))) if temporal_effects else None,
                    "year_concentration": max((abs(v) for v in years.values()), default=0.0)/denom if denom else 1.0}
        regime_effects: dict[str, float | None] = {}
        for regime in protocol["regimes"]:
            subset = action_frame.loc[action_frame["state_regime_v0"].eq(regime)]; submask = mask.loc[subset.index]
            try: regime_effects[regime] = _effect_for(subset, submask, target)
            except ValueError: regime_effects[regime] = None
        finite_regime = [v for v in regime_effects.values() if v is not None]
        regime = {"effects": regime_effects, "sign_consistency": sum(v > 0 for v in finite_regime)/len(finite_regime) if finite_regime else 0.0}

        gross_col=f"outcome_gross_return_{horizon}m"; cost_col=f"cost_spread_return_{horizon}m"
        mfe_col=f"outcome_mfe_{horizon}m"; mae_col=f"outcome_mae_{horizon}m"; method_col=f"cost_method_{horizon}m"
        conditioned = action_frame.loc[mask & action_frame[target].notna()].copy()
        cost_sensitivity: dict[str, dict[str, float]] = {}
        for multiplier in protocol["cost_multipliers"]:
            stressed = action_frame[gross_col]-float(multiplier)*action_frame[cost_col]
            cost_sensitivity[str(multiplier)] = {
                "relative_effect": _effect_for(action_frame.assign(_stressed=stressed), mask, "_stressed"),
                "absolute_conditional_net_return": float(stressed.loc[mask & stressed.notna()].mean())}
        by_method = {}
        for method, subset in conditioned.groupby(method_col):
            by_method[str(method)] = {"observations": int(len(subset)), "gross_return": float(subset[gross_col].mean()),
                                      "spread_cost": float(subset[cost_col].mean()), "net_return": float(subset[target].mean())}
        positives=conditioned.loc[conditioned[target]>0,target]; negatives=conditioned.loc[conditioned[target]<0,target]
        payoff=float(positives.mean()/abs(negatives.mean())) if len(positives) and len(negatives) else None
        economic = {"gross_conditional_return": float(conditioned[gross_col].mean()),
                    "spread_cost": float(conditioned[cost_col].mean()),
                    "absolute_conditional_net_return": float(conditioned[target].mean()),
                    "mfe": float(conditioned[mfe_col].mean()), "mae": float(conditioned[mae_col].mean()),
                    "hit_rate": float((conditioned[target]>0).mean()), "payoff": payoff,
                    "expected_value": float(conditioned[target].mean()), "observation_count": int(len(conditioned)),
                    "frequency": float(len(conditioned)/action_frame[target].notna().sum()), "by_cost_method": by_method,
                    "economic_confidence": "LOW" if by_method.get("REAL_TICK_COST", {}).get("observations", 0) < 500 else "MEDIUM"}

        shifted = action_frame.sort_values("decision_timestamp_utc").copy()
        shifted[target] = shifted.groupby("state_minute_of_session", sort=False)[target].shift(7) if "state_minute_of_session" in shifted else shifted[target].shift(7)
        shifted_mask = mask.loc[shifted.index]
        try: shifted_effect = _effect_for(shifted, shifted_mask, target)
        except ValueError: shifted_effect = None
        slow_passed = shifted_effect is not None and abs(shifted_effect) <= 0.5*max(abs(effect), 1e-12)
        quality_report = self.store.data_engine.manifest(self.store.manifest["data_engine_dataset_id"])["quality"]
        data_quality = {"blocking_errors": quality_report["status"] in ("REJECTED", "EXPLORATORY_ONLY"), "gaps_not_imputed": True,
                        "target_null_fraction": float(action_frame[target].isna().mean())}
        skeptic_cost = {"applicable": True, "survives_2x": cost_sensitivity["2.0"]["relative_effect"] > 0}
        skeptic = run_skeptic(samples["effects"], temporal={"favorable_proportion": temporal["sign_consistency"]},
                              cost=skeptic_cost, data_quality=data_quality, direction=direction)
        skeptic["slow_structure_control"] = {"shift_7_sessions_effect": shifted_effect, "passed": slow_passed}
        support = {"condition_rows": int(mask.sum()), "condition_sessions": int(action_frame.loc[mask,"session_id"].nunique()),
                   "condition_years": int(action_frame.loc[mask,"decision_timestamp_utc"].dt.year.nunique()),
                   "paired_sessions": samples["sessions"]}
        return {"hypothesis_id": candidate["hypothesis_id"], "spec_hash": candidate["spec_hash"],
                "dev_effect": candidate["dev_effect"], "validation_effect": effect,
                "replication_ratio": replication_ratio(effect, candidate["dev_effect"]),
                "effect_bps": effect*10000, "expected_direction": direction,
                "confidence_interval_90": session["confidence_interval_90"],
                "confidence_interval_95": session["confidence_interval_95"], "bootstrap": session,
                "block_bootstrap": block, "stationary_bootstrap": stationary, "permutation": permutation,
                "temporal_stability": temporal, "regime_stability": regime, "cost_sensitivity": cost_sensitivity,
                "economic": economic, "support": support, "data_quality": data_quality, "skeptic": skeptic}

    def run(self) -> dict[str, Any]:
        if self.result_path.exists(): return read_json(self.result_path, {})
        manifest, protocol = self.prepare()
        state = read_json(self.state_path, {})
        if state.get("status") != "PREPARED" or state.get("validation_authorizations") != 0:
            raise PermissionError("VALIDATION authorization is one-time and unavailable")
        # Burn authorization before I/O: interruption cannot silently grant a second look.
        state.update({"status": "CONSUMING", "validation_authorizations": 1,
                      "authorization_consumed_at": utc_now()})
        atomic_write_json(self.state_path, state)
        self.guard.require("VALIDATION", "ValidationCeremony.confirm_frozen_hypothesis")
        frame = self.store.query(partitions=("VALIDATION",), columns=VALIDATION_COLUMNS)
        state["validation_dataset_reads"] = 1
        atomic_write_json(self.state_path, state)
        if set(frame["partition"].unique()) != {"VALIDATION"}:
            raise PermissionError("Unexpected partition in ceremony frame")
        timestamps=pd.to_datetime(frame["decision_timestamp_utc"], utc=True)
        if timestamps.min() < pd.Timestamp("2020-01-01", tz="UTC") or timestamps.max() >= pd.Timestamp("2023-01-01", tz="UTC"):
            raise PermissionError("VALIDATION period mismatch")
        raw = [self._confirm_frozen_hypothesis(frame, item, protocol) for item in manifest["candidates"]]
        p_values=[item["permutation"]["p_value"] for item in raw]
        holm=holm_bonferroni(p_values); bh=benjamini_hochberg(p_values)
        gates=protocol["predictive_replication_gate"]
        verdict_counts={"VALIDATION_FAILED":0,"VALIDATED_PREDICTIVE_RELATIONSHIP_NO_TRADE":0,"VALIDATED_ECONOMIC_CANDIDATE":0}
        for item, hp, qp in zip(raw, holm, bh):
            item["holm_adjusted_p"] = hp; item["bh_fdr_q"] = qp
            s=item["support"]; t=item["temporal_stability"]; sk=item["skeptic"]
            checks={"same_direction":item["validation_effect"]>0,
                    "ci95_directional":item["confidence_interval_95"][0]>gates["ci95_lower_bound_gt"],
                    "holm":hp<=gates["holm_p_lte"],
                    "bootstrap_favorable":item["bootstrap"]["favorable_resample_proportion"]>=gates["bootstrap_favorable_gte"],
                    "sign_stability":item["bootstrap"]["sign_stability"]>=gates["sign_stability_gte"],
                    "support":s["condition_rows"]>=gates["minimum_rows"] and s["condition_sessions"]>=gates["minimum_sessions"] and s["condition_years"]>=gates["minimum_years"],
                    "temporal":t["sign_consistency"]>=gates["temporal_sign_consistency_gte"],
                    "not_year_concentrated":t["year_concentration"]<=gates["year_concentration_lte"],
                    "skeptic":sk["survival_proportion"]>=gates["skeptic_survival_gte"],
                    "slow_structure":sk["slow_structure_control"]["passed"]}
            predictive=all(checks.values()); economic=item["economic"]["absolute_conditional_net_return"]>0
            verdict=("VALIDATION_FAILED" if not predictive else
                     "VALIDATED_ECONOMIC_CANDIDATE" if economic else
                     "VALIDATED_PREDICTIVE_RELATIONSHIP_NO_TRADE")
            item["predictive_replication"]={"passed":predictive,"checks":checks}
            item["economic_gate"]={"passed":economic,"threshold":"> 0 after frozen costs"}
            item["verdict"]=verdict; verdict_counts[verdict]+=1

        result={"ceremony_id":manifest["ceremony_id"],"manifest_hash":manifest["manifest_hash"],
                "protocol_hash":protocol["protocol_hash"],"dataset_version":self.store.dataset_version,
                "partition":"VALIDATION","period":"2020-01-01/2023-01-01 exclusive",
                "validation_rows_loaded":int(len(frame)),"validation_sessions":int(frame["session_id"].nunique()),
                "hypotheses":raw,"verdict_counts":verdict_counts,"optimization_on_validation":False,
                "discovery_on_validation":False,"locked_oos_inspected":False,"orders_sent":0,"created_at":utc_now()}
        result["result_hash"]=content_hash({k:v for k,v in result.items() if k not in {"created_at","result_hash"}})
        atomic_write_json(self.result_path,result)
        for item in raw:
            self.registry.update_status(item["hypothesis_id"],item["verdict"],validation_result=str(self.result_path.relative_to(self.root)).replace("\\","/"),
                                        validation_result_hash=result["result_hash"],validation_effect=item["validation_effect"],replication_ratio=item["replication_ratio"])
        self._update_knowledge_and_value(result)
        state.update({"status":"CONSUMED","completed_at":utc_now(),"result_path":str(self.result_path.relative_to(self.root)).replace("\\","/"),
                      "result_hash":result["result_hash"],"locked_oos_reads":0})
        atomic_write_json(self.state_path,state)
        return result

    def _update_knowledge_and_value(self, result: dict[str, Any]) -> None:
        semantic_store=SemanticMemory(self.root/"memory_db"); created=[]
        existing={tuple(x.get("tags",[])) for x in semantic_store.all()}
        for item in result["hypotheses"]:
            tags=sorted(["prompt-6", "validation", item["hypothesis_id"].lower(), item["verdict"].lower()])
            if tuple(tags) in existing: continue
            content=(f"Independent VALIDATION result for {item['hypothesis_id']}: {item['verdict']}; "
                     f"DEV effect={item['dev_effect']:.10g}, VALIDATION effect={item['validation_effect']:.10g}, "
                     f"net conditional={item['economic']['absolute_conditional_net_return']:.10g}.")
            created.append(semantic_store.add_knowledge(content,evidence_ids=[item["hypothesis_id"],result["result_hash"]],
                                                        confidence=.9 if item["predictive_replication"]["passed"] else .8,tags=tags))
        predictive=[x for x in result["hypotheses"] if x["predictive_replication"]["passed"]]
        promoted=[]
        if predictive:
            summary=semantic_store.add_knowledge(
                f"{len(predictive)}/4 frozen reversal-relative hypotheses replicated independently; economic status is preserved separately.",
                evidence_ids=[result["result_hash"],*[x["hypothesis_id"] for x in predictive]],confidence=.9,
                tags=["prompt-6","validation","reversal-relative-v1","independent-replication"])
            created.append(summary); promoted.append(LongTermMemory(self.root/"memory_db").promote(summary))
        states=StateStore(self.root/"state"); current=states.load_all()
        counts={"working":len(read_json(self.root/"memory_db/working/records.json",[])),
                "episodic":len(read_json(self.root/"memory_db/episodic/records.json",[])),
                "semantic":len(semantic_store.all()),"long_term":len(LongTermMemory(self.root/"memory_db").all())}
        states.save("memory_state",{**current["memory_state"],"counts":counts,"last_validation_consolidation":utc_now(),
                                    "validation_semantic_created":len(created),"validation_long_term_created":len(promoted)})
        economic=sum(x["verdict"]=="VALIDATED_ECONOMIC_CANDIDATE" for x in result["hypotheses"])
        knowledge_value=round(.4+.15*len(predictive),6); research_value=round(max(.1,1-.2*len(predictive)),6)
        trade_value=round(economic/4,6)
        states.save("value_model_state",{**current["value_model_state"],"version":"v3-independent-validation",
                    "validation_values":{"knowledge_value":knowledge_value,"research_value":research_value,"trade_value":trade_value,
                    "interpretation":"separate non-interchangeable scores"}})
        states.save("research_state",{**current["research_state"],"validation_ceremony":"CONSUMED",
                    "validation_verdict_counts":result["verdict_counts"],"validation_inspected":True,"locked_oos_inspected":False})


def prepare_validation_ceremony(project_root: Path | str) -> tuple[dict[str, Any], dict[str, Any]]:
    return ValidationCeremony(project_root).prepare()


def run_validation_ceremony(project_root: Path | str) -> dict[str, Any]:
    return ValidationCeremony(project_root).run()
