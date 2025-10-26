"""Tests for evaluation functions."""

from src.utils.evaluation import evaluate_exact_match


def test_evaluate_exact_match_casos_borde():
    """Test evaluate_exact_match with edge cases."""
    # --- Casos esperados (True) ---
    # Caso 1: Coincidencia simple
    assert evaluate_exact_match(y_true=12.0, y_pred_raw="La respuesta es #### 12")

    # Caso 2: Coincidencia con decimales
    assert evaluate_exact_match(y_true=5.5, y_pred_raw="El resultado final es #### 5.5")

    # Caso 3: Caso Borde - Comas (mencionado en S1-04)
    assert evaluate_exact_match(y_true=1200.0, y_pred_raw="#### 1,200")

    # Caso 4: Caso Borde - Espacios (mencionado en S1-04)
    assert evaluate_exact_match(y_true=12.0, y_pred_raw="   #### 12   ")

    # Caso 5: Caso Borde - Texto extra despuÃ©s del nÃºmero
    assert evaluate_exact_match(y_true=12.0, y_pred_raw="#### 12. Es obvio.")

    # --- Casos de Falla (False) ---

    # Caso 6: NÃºmero incorrecto
    assert not evaluate_exact_match(y_true=12.0, y_pred_raw="#### 13")

    # Caso 7: Falla de normalizaciÃ³n (formato incorrecto)
    assert not evaluate_exact_match(y_true=12.0, y_pred_raw="La respuesta no la sÃ©.")

    # Caso 8: Falla de normalizaciÃ³n (string vacÃ­o)
    assert not evaluate_exact_match(y_true=12.0, y_pred_raw="")