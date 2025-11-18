"""Tests for the T-A-S flow."""
import pytest
from unittest.mock import patch, MagicMock
from flows.tas import solve_tas_problem, TASFlowConfig

@patch('flows.tas.get_run_logger')
@patch('flows.tas.run_tas_k1')
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

    # Mock the output of the T-A-S sub-flow (run_tas_k1)
    mock_tas_output = {
        "answer": "This is the thesis. This is the antithesis. This is the synthesis. The final answer is #### 123.0",
        "meta": {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
    }
    mock_run_tas_k1.return_value = mock_tas_output

    # 2. Execute
    result = solve_tas_problem.fn(
        problem=problem,
        run_id="test-run-123",
        flow_config=flow_config
    )

    # 3. Assert
    # Check that the main T-A-S fields are present
    assert "tas_final_text" in result
    assert result["tas_final_text"] == mock_tas_output["answer"]

    # Check that the final answer was extracted correctly
    assert "predicted_answer_raw" in result
    assert result["predicted_answer_raw"] == "123.0"

    # Check that the success/correctness flag is set
    assert "is_correct" in result
    assert result["is_correct"] is True

    # Check that token usage is correctly reported
    assert "tas_usage" in result
    assert result["tas_usage"]["total_tokens"] == 150

    # Check that other important fields are present
    assert result["run_id"] == "test-run-123"
    assert result["problem_id"] == "gsm8k-001"
    assert result["true_answer"] == 123.0
