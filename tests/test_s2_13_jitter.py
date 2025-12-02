from src.flows.jitter_runner import jitter


def test_run_s2_13_jitter_returns_expected_format():
    results = jitter()

    # Debe regresar una lista con 3 resultados
    assert isinstance(results, list)
    assert len(results) == 3

    # Cada resultado debe ser None (fallo) o un dict con 'result'
    for r in results:
        if r is not None:
            assert isinstance(r, dict)
            assert "result" in r
