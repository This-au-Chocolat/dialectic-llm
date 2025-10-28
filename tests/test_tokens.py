"""Tests for token counting utilities."""

from utils.tokens import add_token_info, count_tokens, estimate_cost


def test_count_tokens_basic():
    """Test basic token counting functionality."""
    event = {"prompt": "What is 2 + 2?", "completion": "The answer is 4."}

    result = count_tokens(event)

    # Check structure
    assert "prompt_tokens" in result
    assert "completion_tokens" in result
    assert "total_tokens" in result

    # Check types
    assert isinstance(result["prompt_tokens"], int)
    assert isinstance(result["completion_tokens"], int)
    assert isinstance(result["total_tokens"], int)

    # Check logic
    assert result["total_tokens"] == result["prompt_tokens"] + result["completion_tokens"]

    # Check reasonable values (not zero for non-empty text)
    assert result["prompt_tokens"] > 0
    assert result["completion_tokens"] > 0


def test_count_tokens_empty():
    """Test token counting with empty content."""
    event = {"prompt": "", "completion": ""}

    result = count_tokens(event)

    assert result["prompt_tokens"] == 0
    assert result["completion_tokens"] == 0
    assert result["total_tokens"] == 0


def test_count_tokens_missing_keys():
    """Test token counting with missing keys."""
    event = {}

    result = count_tokens(event)

    assert result["prompt_tokens"] == 0
    assert result["completion_tokens"] == 0
    assert result["total_tokens"] == 0


def test_count_tokens_different_models():
    """Test token counting with different model encodings."""
    event = {"prompt": "Hello world", "completion": "Hi there"}

    result_gpt4 = count_tokens(event, model="gpt-4")
    result_gpt35 = count_tokens(event, model="gpt-3.5-turbo")
    result_unknown = count_tokens(event, model="unknown-model")

    # All should return valid token counts
    assert all(
        isinstance(r["total_tokens"], int) for r in [result_gpt4, result_gpt35, result_unknown]
    )
    assert all(r["total_tokens"] > 0 for r in [result_gpt4, result_gpt35, result_unknown])


def test_estimate_cost():
    """Test cost estimation."""
    token_counts = {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}

    cost_gpt4 = estimate_cost(token_counts, "gpt-4")
    cost_gpt35 = estimate_cost(token_counts, "gpt-3.5-turbo")

    # Should return positive floats
    assert isinstance(cost_gpt4, float)
    assert isinstance(cost_gpt35, float)
    assert cost_gpt4 > 0
    assert cost_gpt35 > 0

    # GPT-4 should be more expensive than GPT-3.5
    assert cost_gpt4 > cost_gpt35


def test_add_token_info():
    """Test adding token info to events."""
    event = {
        "prompt": "Calculate 5 * 6",
        "completion": "5 * 6 = 30",
        "run_id": "test-123",
        "problem_id": "math-001",
    }

    result = add_token_info(event.copy())  # Don't modify original

    # Original keys should be preserved
    assert result["run_id"] == "test-123"
    assert result["problem_id"] == "math-001"

    # New keys should be added
    assert "tokens" in result
    assert "estimated_cost_usd" in result

    # Token structure should be correct
    tokens = result["tokens"]
    assert "prompt_tokens" in tokens
    assert "completion_tokens" in tokens
    assert "total_tokens" in tokens

    # Cost should be positive
    assert result["estimated_cost_usd"] > 0
    assert isinstance(result["estimated_cost_usd"], float)


def test_count_tokens_consistency():
    """Test that token counting is consistent across calls."""
    event = {
        "prompt": "This is a test prompt for consistency checking.",
        "completion": "This is the corresponding completion text.",
    }

    result1 = count_tokens(event)
    result2 = count_tokens(event)

    # Results should be identical
    assert result1 == result2
