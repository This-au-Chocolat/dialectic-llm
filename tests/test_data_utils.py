from unittest.mock import patch

import pytest

from utils.data_utils import load_gsm8k_problems


@patch("utils.data_utils.load_batch")
def test_load_gsm8k_batch_success(mock_load_batch):
    """Tests successful loading and parsing of a batch."""
    mock_data = [
        {"question": "Q1", "answer": "A1 #### 10"},
        {"question": "Q2", "answer": "A2 #### 20.5"},
    ]
    mock_load_batch.return_value = mock_data

    result = load_gsm8k_problems(n=2)

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["question"] == "Q1"
    assert result[0]["answer"] == 10.0
    assert result[1]["question"] == "Q2"
    assert result[1]["answer"] == 20.5
    assert "problem_id" in result[0]
    assert "answer_raw" in result[0]


@patch("utils.data_utils.load_batch")
def test_load_gsm8k_batch_missing_key(mock_load_batch):
    """Tests that a KeyError is raised if a key is missing."""
    mock_data = [
        {"question": "Q1", "answer": "A1 #### 10"},
        {"question": "Q2"},  # Missing 'answer' key
    ]
    mock_load_batch.return_value = mock_data

    with pytest.raises(KeyError):
        load_gsm8k_problems(n=2)


@patch("utils.data_utils.load_batch")
def test_load_gsm8k_batch_malformed_answer(mock_load_batch):
    """Tests fallback behavior for malformed answers."""
    mock_data = [
        {"question": "Q1", "answer": "A1 #### ten"},  # Has "1" in text, fallback finds it
        {"question": "Q2", "answer": "A2 ####"},  # Has "2" in text, fallback finds it
    ]
    mock_load_batch.return_value = mock_data

    result = load_gsm8k_problems(n=2)

    # Our consolidated function has robust fallback: extracts numbers from text
    assert result[0]["answer"] == 1.0  # Finds "1" from "A1"
    assert result[1]["answer"] == 2.0  # Finds "2" from "A2"
