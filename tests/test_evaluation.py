"""Tests for evaluation functions."""
import pytest
from utils.evaluation import evaluate_exact_match


def test_evaluate_exact_match_edge_cases():
    """Test evaluate_exact_match with edge cases."""
    # --- Expected Cases (True) ---
    # Case 1: Simple match
    assert evaluate_exact_match(y_true=12.0, y_pred_raw="La respuesta es #### 12")

    # Case 2: Match with decimals
    assert evaluate_exact_match(y_true=5.5, y_pred_raw="El resultado final es #### 5.5")

    # Case 3: Edge Case - Commas (mentioned in S1-04)
    assert evaluate_exact_match(y_true=1200.0, y_pred_raw="#### 1,200")

    # Case 4: Edge Case - Spaces (mentioned in S1-04)
    assert evaluate_exact_match(y_true=12.0, y_pred_raw="   #### 12   ")

    # Case 5: Edge Case - Extra text after the number
    assert evaluate_exact_match(y_true=12.0, y_pred_raw="#### 12. Es obvio.")

    # --- Failure Cases (False) ---

    # Case 6: Incorrect number
    assert not evaluate_exact_match(y_true=12.0, y_pred_raw="#### 13")

    # Case 7: Normalization failure (incorrect format)
    assert not evaluate_exact_match(y_true=12.0, y_pred_raw="La respuesta no la sé.")

    # Case 8: Normalization failure (empty string)
    assert not evaluate_exact_match(y_true=12.0, y_pred_raw="")
