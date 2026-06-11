"""Evaluation metric helpers."""
from __future__ import annotations


def foir(monthly_obligations: float, monthly_income: float) -> float:
    """Fixed Obligation to Income Ratio."""
    return monthly_obligations / monthly_income if monthly_income > 0 else 1.0


def emi_accuracy(actual: float, expected: float, tolerance: float = 0.01) -> bool:
    """Return True if actual EMI is within tolerance of expected (default 1%)."""
    return abs(actual - expected) / expected <= tolerance


def escalation_recall(predicted: list[bool], ground_truth: list[bool]) -> float:
    """Fraction of true escalation cases that were correctly triggered."""
    tp = sum(p and g for p, g in zip(predicted, ground_truth))
    fn = sum((not p) and g for p, g in zip(predicted, ground_truth))
    return tp / (tp + fn) if (tp + fn) > 0 else 0.0
