"""Evaluation functions."""

import math
from dialectic_llm.data import normalize_answer

def evaluate_exact_match(y_true: float, y_pred_raw: str) -> bool:
    """
    Evaluate exact match between a float ground truth and a raw predicted string.

    This function normalizes the predicted string to extract a numerical value and
    compares it to the ground truth float using math.isclose for robust float comparison.

    Args:
        y_true: The ground truth float value.
        y_pred_raw: The raw predicted string.

    Returns:
        True if the normalized prediction is close to the ground truth, False otherwise.
    """
    normalized_pred = normalize_answer(y_pred_raw)
    if not normalized_pred:
        return False
    try:
        pred_float = float(normalized_pred)
        return math.isclose(y_true, pred_float)
    except (ValueError, TypeError):
        return False