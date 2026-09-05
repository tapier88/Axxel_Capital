"""Research-value V0, deliberately separate from trading profit."""


def research_value(
    *, uncertainty: float, information: float, reproducibility: float, cost: float,
    weights: dict[str, float] | None = None,
) -> float:
    weights = weights or {"uncertainty": 0.35, "information": 0.40, "reproducibility": 0.25}
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Research-value weights must sum to more than zero")
    cost = max(0.0, min(1.0, cost))
    raw = (
        weights["uncertainty"] * uncertainty + weights["information"] * information
        + weights["reproducibility"] * reproducibility
    ) / total
    return round(max(0.0, min(1.0, raw * (1.0 - 0.5 * cost))), 6)


def research_value_v1(*, expected_information_gain: float, uncertainty_reduction: float,
                      novelty: float, cost: float, relevance: float,
                      previous_evidence: float) -> dict:
    """Priority for learning, with diminishing value for already-resolved questions."""
    inputs = {"expected_information_gain": expected_information_gain,
              "uncertainty_reduction": uncertainty_reduction, "novelty": novelty,
              "relevance": relevance, "previous_evidence": previous_evidence}
    bounded = {key: max(0.0, min(1.0, float(value))) for key, value in inputs.items()}
    cost = max(0.0, min(1.0, float(cost)))
    unresolved = 1.0-bounded["previous_evidence"]
    raw = (.30*bounded["expected_information_gain"] + .25*bounded["uncertainty_reduction"]
           + .15*bounded["novelty"] + .20*bounded["relevance"] + .10*unresolved)
    score = raw*(1-.5*cost)*(.5+.5*unresolved)
    return {"score": round(max(0.0, min(1.0, score)), 6), "components": bounded,
            "cost": cost, "resolved_question_discount": round(.5+.5*unresolved, 6),
            "purpose": "research prioritization only; not trade value"}


def research_value_v2(*, expected_information_gain: float, uncertainty_reduction: float,
                      novelty: float, prior_evidence: float, contradiction_value: float,
                      economic_relevance: float, data_quality: float, estimated_compute_cost: float,
                      redundancy_penalty: float, family_saturation_penalty: float,
                      complexity_penalty: float = 0.0) -> dict:
    values = {key: max(0.0, min(1.0, float(value))) for key, value in locals().items()}
    positive = (.22*values["expected_information_gain"] + .16*values["uncertainty_reduction"]
                + .13*values["novelty"] + .12*values["contradiction_value"]
                + .12*values["economic_relevance"] + .10*values["data_quality"]
                + .08*(1-values["prior_evidence"]) + .07*(1-values["estimated_compute_cost"]))
    penalty = (.45*values["redundancy_penalty"] + .30*values["family_saturation_penalty"]
               + .25*values["complexity_penalty"])
    score = positive*(1-.7*penalty)
    return {"score": round(max(0.0, min(1.0, score)), 6), "components": values,
            "penalty": round(penalty, 6), "purpose": "autonomous research priority only"}
