"""Information-value V0: uncertainty reduction plus reusable evidence."""


def information_value(uncertainty_before: float, uncertainty_after: float, *, reusable_evidence: bool) -> float:
    reduction = max(0.0, uncertainty_before - uncertainty_after)
    return round(min(1.0, reduction + (0.25 if reusable_evidence else 0.0)), 6)
