"""Tests for the T-A-S flow."""

from unittest.mock import MagicMock, patch

from flows.tas import TASFlowConfig, solve_tas_problem


@patch("flows.tas.get_run_logger")
@patch("flows.tas.run_tas_k1")
def test_solve_tas_problem(mock_run_tas_k1, mock_get_run_logger):
    """
    Tests the solve_tas_problem function, ensuring it correctly processes
    the output of the T-A-S flow and returns a structured result.
    """
    # 1. Setup
    # Mock logger
    mock_get_run_logger.return_value = MagicMock()

    # Mock problem dictionary
    problem = {
        "problem_id": "gsm8k-001",
        "question": "A test question.",
        "answer": 123.0,
    }

    # Mock flow configuration
    flow_config = TASFlowConfig(run_id="test-run-123")

    # Mock the output of the T-A-S sub-flow (run_tas_k1) to match the new structure
    mock_tas_output = {
        "thesis": {
            "answer": "This is the thesis.",
            "meta": {"usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70}},
        },
        "antithesis": {
            "critique": "This is the critique.",
            "meta": {"usage": {"prompt_tokens": 40, "completion_tokens": 20, "total_tokens": 60}},
        },
        "synthesis": {
            "answer": "This is the synthesis. The final answer is #### 123.0",
            "meta": {"usage": {"prompt_tokens": 60, "completion_tokens": 30, "total_tokens": 90}},
        },
    }
    mock_run_tas_k1.return_value = mock_tas_output

    # 2. Execute
    result = solve_tas_problem.fn(problem=problem, run_id="test-run-123", flow_config=flow_config)

    # 3. Assert
    # Check that the new text fields are present
    assert "thesis_text" in result
    assert result["thesis_text"] == mock_tas_output["thesis"]["answer"]
    assert "synthesis_text" in result
    assert result["synthesis_text"] == mock_tas_output["synthesis"]["answer"]

    # Check that the main T-A-S final text is the synthesis answer
    assert "tas_final_text" in result
    assert result["tas_final_text"] == mock_tas_output["synthesis"]["answer"]

    # Check that the final answer was extracted correctly
    assert "predicted_answer_raw" in result
    assert result["predicted_answer_raw"] == "123.0"

    # Check that the success/correctness flag is set
    assert "is_correct" in result
    assert result["is_correct"] is True

    # Check that token usage is correctly aggregated from all stages
    assert "tas_usage" in result
    expected_total_tokens = (
        mock_tas_output["thesis"]["meta"]["usage"]["total_tokens"]
        + mock_tas_output["antithesis"]["meta"]["usage"]["total_tokens"]
        + mock_tas_output["synthesis"]["meta"]["usage"]["total_tokens"]
    )
    assert result["tas_usage"]["total_tokens"] == expected_total_tokens

    # Check that other important fields are present
    assert result["run_id"] == "test-run-123"
    assert result["problem_id"] == "gsm8k-001"
    assert result["true_answer"] == 123.0
