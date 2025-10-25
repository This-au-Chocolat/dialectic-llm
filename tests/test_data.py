import pytest

from src.dialectic_llm.data import normalize_answer


@pytest.mark.parametrize(
    "answer, expected",
    [
        # Original test cases
        ("1,000", "1000"),
        (" 1 000 ", "1000"),
        ("1,000.00", "1000.00"),
        ("1,000,000", "1000000"),
        ("The answer is 1,000", "1000"),
        ("The answer is 1000", "1000"),
        ("The answer is 1,000.", "1000."),
        ("The answer is 1,000.00", "1000.00"),
        ("The answer is 1,000,000", "1000000"),
        # New test cases for GSM8K format
        ("The answer is 1,000\n#### 1000", "1000"),
        ("The answer is 1,000\n#### 1,000", "1000"),
        ("The answer is 1,000\n#### 1,000.00", "1000.00"),
        ("#### 1,000,000", "1000000"),
        # New edge cases
        ("", ""),
        ("no numbers here", ""),
        ("the answer is 1, but also 2", "2"),
        ("1.000.000", "1000000"),
        ("the answer is: 123,456,789", "123456789"),
        ("the answer is: 123.456.789", "123456789"),
    ],
)
def test_normalize_answer(answer, expected):
    assert normalize_answer(answer) == expected
