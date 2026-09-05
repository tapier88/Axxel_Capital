"""Small, deterministic, memory-aware hypothesis proposal generator."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from src.utils.hashing import content_hash
from src.utils.serialization import read_json
from src.value.research_value import research_value_v2

FAMILIES = ("TEMPORAL", "VOLATILITY", "RANGE", "MOMENTUM", "REVERSAL", "CONTINUATION",
            "BREAKOUT", "MEAN_REVERSION", "REGIME", "COST", "CROSS_FEATURE", "DATA_QUALITY")

def _condition(kind: str, field: str, value: Any, second: Any = None) -> dict:
    if kind == "minute_range": return {"type": kind, "field": field, "start": value, "end": second}
    if kind in {"quantile_gte", "quantile_lte"}: return {"type": kind, "field": field, "quantile": value}
    return {"type": kind, "field": field, "value": value}

def _catalog() -> list[dict[str, Any]]:
    rows = [
      ("TEMPORAL","MID_MORNING_VOL",_condition("minute_range","state_minute_of_session",60,90),"label_realized_volatility_30m","WAIT","GREATER",[85,95]),
      ("TEMPORAL","LATE_SESSION_VOL",_condition("minute_range","state_minute_of_session",180,210),"label_realized_volatility_30m","WAIT","GREATER",[205,215]),
      ("VOLATILITY","HIGH_VOL_SHORT_HORIZON",_condition("quantile_gte","state_volatility_15m_causal",.80),"label_realized_volatility_15m","WAIT","GREATER",[.75,.85]),
      ("VOLATILITY","LOW_VOL_LONG_HORIZON",_condition("quantile_lte","state_volatility_60m_causal",.20),"label_realized_volatility_60m","WAIT","LESS",[.15,.25]),
      ("RANGE","HIGH_RANGE_UP_EXCURSION",_condition("quantile_gte","state_bar_range",.80),"label_up_excursion_30m","WAIT","GREATER",[.75,.85]),
      ("RANGE","HIGH_RANGE_DOWN_EXCURSION",_condition("quantile_gte","state_bar_range",.80),"label_down_excursion_30m","WAIT","LESS",[.75,.85]),
      ("MOMENTUM","POSITIVE_MOMENTUM_LONG",_condition("quantile_gte","state_return_15m",.80),"outcome_tradable_return_30m","LONG","GREATER",[.75,.85]),
      ("MOMENTUM","NEGATIVE_MOMENTUM_SHORT",_condition("quantile_lte","state_return_15m",.20),"outcome_tradable_return_30m","SHORT","GREATER",[.15,.25]),
      ("REVERSAL","UP_MOVE_REVERSES",_condition("quantile_gte","state_return_15m",.85),"outcome_tradable_return_15m","SHORT","GREATER",[.80,.90]),
      ("REVERSAL","DOWN_MOVE_REVERSES",_condition("quantile_lte","state_return_15m",.15),"outcome_tradable_return_15m","LONG","GREATER",[.10,.20]),
      ("CONTINUATION","UP_CONTINUES",_condition("quantile_gte","state_return_60m",.80),"outcome_tradable_return_60m","LONG","GREATER",[.75,.85]),
      ("CONTINUATION","DOWN_CONTINUES",_condition("quantile_lte","state_return_60m",.20),"outcome_tradable_return_60m","SHORT","GREATER",[.15,.25]),
      ("BREAKOUT","NEAR_HIGH_BREAKS",_condition("quantile_lte","state_distance_recent_high",.10),"outcome_tradable_return_30m","LONG","GREATER",[.05,.15]),
      ("BREAKOUT","NEAR_LOW_BREAKS",_condition("quantile_lte","state_distance_recent_low",.10),"outcome_tradable_return_30m","SHORT","GREATER",[.05,.15]),
      ("MEAN_REVERSION","NEAR_HIGH_REVERTS",_condition("quantile_lte","state_distance_recent_high",.10),"outcome_tradable_return_30m","SHORT","GREATER",[.05,.15]),
      ("MEAN_REVERSION","NEAR_LOW_REVERTS",_condition("quantile_lte","state_distance_recent_low",.10),"outcome_tradable_return_30m","LONG","GREATER",[.05,.15]),
      ("REGIME","UP_REGIME_EXPANDS",_condition("field_equals","state_regime_v0","TREND_UP"),"label_realized_volatility_30m","WAIT","GREATER",[]),
      ("REGIME","RANGE_REGIME_QUIET",_condition("field_equals","state_regime_v0","RANGE"),"label_realized_volatility_30m","WAIT","LESS",[]),
      ("COST","LOW_SPREAD_LONG",_condition("quantile_lte","state_spread_points",.20),"outcome_tradable_return_15m","LONG","GREATER",[.15,.25]),
      ("COST","HIGH_SPREAD_LONG",_condition("quantile_gte","state_spread_points",.80),"outcome_tradable_return_30m","LONG","LESS",[.75,.85]),
      ("CROSS_FEATURE","LATE_HIGH_VOL",{"type":"all","clauses":[_condition("minute_range","state_minute_of_session",150,210),_condition("quantile_gte","state_volatility_15m_causal",.75)]},"label_realized_volatility_30m","WAIT","GREATER",[]),
      ("CROSS_FEATURE","UP_REGIME_HIGH_RANGE",{"type":"all","clauses":[_condition("field_equals","state_regime_v0","TREND_UP"),_condition("quantile_gte","state_bar_range",.75)]},"outcome_tradable_return_30m","LONG","GREATER",[]),
      ("DATA_QUALITY","HIGH_TICK_ACTIVITY",_condition("quantile_gte","state_tick_volume",.80),"label_realized_volatility_30m","WAIT","GREATER",[.75,.85]),
      ("DATA_QUALITY","LOW_TICK_ACTIVITY",_condition("quantile_lte","state_tick_volume",.20),"label_realized_volatility_30m","WAIT","LESS",[.15,.25]),
    ]
    proposals = []
    for number, (family, name, condition, target, action, direction, neighbors) in enumerate(rows, 1):
        returns = target.startswith("outcome_tradable_return")
        proposals.append({"id": f"HYPOTHESIS-DISC-{number:02d}-{name}-V1", "family": family,
          "question": f"Does {name.lower().replace('_',' ')} change {target} versus its DEV base rate?",
          "target_variable": target, "population": "GOLD M1 decisions 08:00-12:30 COT in DEV",
          "temporal_window": "2015-01-01/2020-01-01 exclusive", "condition": condition,
          "primary_metric": "session-weighted difference in mean outcome",
          "secondary_metrics": ["base rate","median bootstrap","MFE/MAE context","temporal and regime stability"],
          "null": "Conditioned and baseline session-level outcomes are exchangeable",
          "expected_direction": direction, "rejection_criterion": "Any mandatory evidence or falsification gate fails",
          "survival_criterion": "Material effect survives FDR, dependence-aware resampling, stability and negative controls",
          "planned_comparisons": 1+len(neighbors), "action": action, "effect_unit": "return" if returns else "return-derived",
          "minimum_effect": .00005 if returns else .00001, "parameter_neighbors": neighbors,
          "minimum_rows": 5000, "minimum_sessions": 200, "minimum_years": 3})
    return proposals

class HypothesisGenerator:
    def __init__(self, project_root: Path | str): self.root = Path(project_root)
    def generate(self, limit: int = 24, *, include_existing_campaign: bool = False) -> list[dict[str, Any]]:
        registry = read_json(self.root / "hypotheses/evidence_registry.json", [])
        memory = read_json(self.root / "memory_db/semantic/records.json", [])
        known_signatures = {content_hash({"condition": x.get("condition"), "target": x.get("target_variable"), "action": x.get("action")}): x["id"]
                            for x in registry}
        rejected_by_family = {family: sum(x.get("family") == family and x.get("status") == "REJECTED" for x in registry) for family in FAMILIES}
        proposals = []
        for item in _catalog():
            signature = content_hash({"condition": item["condition"], "target": item["target_variable"], "action": item["action"]})
            same_campaign_record = known_signatures.get(signature) == item["id"]
            duplicate = signature in known_signatures
            related = item["family"] in {"VOLATILITY", "TEMPORAL"}
            item["proposal_type"] = "REFINEMENT" if related else "NOVEL"
            item["memory_consulted"] = len(memory); item["prior_hypotheses_consulted"] = len(registry)
            item["semantic_signature"] = signature; item["duplicate_rejected_idea"] = duplicate
            complexity = .5 if item["condition"]["type"] == "all" else .2
            value = research_value_v2(expected_information_gain=.8, uncertainty_reduction=.75,
                novelty=.55 if related else .85, prior_evidence=.45 if related else .15,
                contradiction_value=1.0 if related else .3, economic_relevance=1.0 if item["action"] != "WAIT" else .65,
                data_quality=.9, estimated_compute_cost=.35+complexity*.2,
                redundancy_penalty=1.0 if duplicate else .05, family_saturation_penalty=min(1,rejected_by_family[item["family"]]/4),
                complexity_penalty=complexity)
            item["initial_research_value"] = value
            if not duplicate or (include_existing_campaign and same_campaign_record): proposals.append(item)
        return sorted(proposals, key=lambda x: (-x["initial_research_value"]["score"], x["id"]))[:limit]
