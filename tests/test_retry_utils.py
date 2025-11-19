"""Tests for retry and rate limiting utilities.

Task: S2-01 - Tests for retry/backoff/rate-limit logic
"""

import time
from unittest.mock import MagicMock

import pytest

from src.utils.retry_utils import (
    PREFECT_RETRY_CONFIG,
    RateLimitError,
    RetryableError,
    create_retry_log_entry,
    exponential_backoff_with_jitter,
    get_prefect_retry_delays,
    is_rate_limit_error,
    is_retryable_error,
    retry_with_backoff,
)


class TestExponentialBackoff:
    """Test exponential backoff calculation."""

    def test_backoff_no_jitter(self):
        """Test exponential backoff without jitter."""
        assert exponential_backoff_with_jitter(0, base_delay=1.0, jitter=False) == 1.0
        assert exponential_backoff_with_jitter(1, base_delay=1.0, jitter=False) == 2.0
        assert exponential_backoff_with_jitter(2, base_delay=1.0, jitter=False) == 4.0
        assert exponential_backoff_with_jitter(3, base_delay=1.0, jitter=False) == 8.0

    def test_backoff_with_jitter(self):
        """Test that jitter produces values in expected range."""
        for attempt in range(5):
            delay = exponential_backoff_with_jitter(attempt, base_delay=1.0, jitter=True)
            expected_max = 1.0 * (2**attempt)
            assert 0 <= delay <= expected_max

    def test_backoff_respects_max_delay(self):
        """Test that backoff respects maximum delay."""
        delay = exponential_backoff_with_jitter(10, base_delay=1.0, max_delay=30.0, jitter=False)
        assert delay == 30.0

    def test_backoff_custom_base(self):
        """Test backoff with custom base delay."""
        assert exponential_backoff_with_jitter(0, base_delay=2.0, jitter=False) == 2.0
        assert exponential_backoff_with_jitter(1, base_delay=2.0, jitter=False) == 4.0
        assert exponential_backoff_with_jitter(2, base_delay=2.0, jitter=False) == 8.0


class TestErrorDetection:
    """Test error detection functions."""

    def test_is_rate_limit_error_positive(self):
        """Test detection of rate limit errors."""
        rate_limit_errors = [
            Exception("Rate limit exceeded"),
            Exception("rate_limit error"),
            Exception("HTTP 429: Too many requests"),
            Exception("Quota exceeded"),
            Exception("RateLimit: throttled"),
        ]
        for error in rate_limit_errors:
            assert is_rate_limit_error(error)

    def test_is_rate_limit_error_negative(self):
        """Test non-rate-limit errors are not detected."""
        other_errors = [
            Exception("Invalid API key"),
            Exception("Not found"),
            Exception("Bad request"),
        ]
        for error in other_errors:
            assert not is_rate_limit_error(error)

    def test_is_retryable_error_with_rate_limit(self):
        """Test that rate limit errors are retryable."""
        error = Exception("Rate limit exceeded")
        assert is_retryable_error(error)

    def test_is_retryable_error_with_network(self):
        """Test that network errors are retryable."""
        retryable = [
            Exception("Connection timeout"),
            Exception("Network error"),
            Exception("Service unavailable (503)"),
            Exception("Bad gateway (502)"),
            Exception("Internal server error (500)"),
        ]
        for error in retryable:
            assert is_retryable_error(error)

    def test_is_retryable_error_negative(self):
        """Test that certain errors are not retryable."""
        non_retryable = [
            Exception("Invalid API key"),
            Exception("Authentication failed"),
            Exception("Bad request (400)"),
        ]
        for error in non_retryable:
            assert not is_retryable_error(error)

    def test_custom_exception_types(self):
        """Test custom exception types."""
        assert is_retryable_error(RateLimitError("rate limit"))
        assert is_retryable_error(RetryableError("temporary failure"))


class TestRetryWithBackoff:
    """Test retry with backoff function."""

    def test_successful_first_call(self):
        """Test function succeeds on first call."""
        mock_func = MagicMock(return_value="success")
        result = retry_with_backoff(mock_func, max_retries=3)
        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_on_retryable_error(self):
        """Test retry occurs on retryable errors."""
        mock_func = MagicMock(
            side_effect=[
                Exception("Connection timeout"),
                Exception("Network error"),
                "success",
            ]
        )
        result = retry_with_backoff(mock_func, max_retries=3, base_delay=0.01)
        assert result == "success"
        assert mock_func.call_count == 3

    def test_no_retry_on_non_retryable_error(self):
        """Test that non-retryable errors raise immediately."""
        mock_func = MagicMock(side_effect=Exception("Invalid API key"))
        with pytest.raises(Exception, match="Invalid API key"):
            retry_with_backoff(mock_func, max_retries=3)
        assert mock_func.call_count == 1

    def test_max_retries_exceeded(self):
        """Test that function raises after max retries."""
        mock_func = MagicMock(side_effect=Exception("Rate limit exceeded"))
        with pytest.raises(Exception, match="Rate limit exceeded"):
            retry_with_backoff(mock_func, max_retries=2, base_delay=0.01)
        assert mock_func.call_count == 3  # Initial + 2 retries

    def test_retry_with_logger(self):
        """Test that logger is called during retries."""
        mock_logger = MagicMock()
        mock_func = MagicMock(side_effect=[Exception("Network error"), "success"])

        result = retry_with_backoff(mock_func, max_retries=3, base_delay=0.01, logger=mock_logger)

        assert result == "success"
        assert mock_logger.warning.called

    def test_retry_timing(self):
        """Test that retries respect delay timing."""
        mock_func = MagicMock(side_effect=[Exception("Timeout"), "success"])

        start = time.time()
        retry_with_backoff(mock_func, max_retries=3, base_delay=0.1, jitter=False)
        elapsed = time.time() - start

        # Should have at least one delay of ~0.1s
        assert elapsed >= 0.1

    def test_retry_with_kwargs(self):
        """Test retry passes kwargs to function."""

        def func_with_args(a, b, c=None):
            if not hasattr(func_with_args, "called"):
                func_with_args.called = True
                raise Exception("Rate limit")
            return {"a": a, "b": b, "c": c}

        result = retry_with_backoff(func_with_args, max_retries=3, base_delay=0.01, a=1, b=2, c=3)

        assert result == {"a": 1, "b": 2, "c": 3}


class TestRetryLogEntry:
    """Test retry log entry creation."""

    def test_create_basic_log_entry(self):
        """Test creating basic retry log entry."""
        error = Exception("Test error")
        log_entry = create_retry_log_entry(attempt=1, max_retries=3, delay=2.5, error=error)

        assert log_entry["event_type"] == "retry"
        assert log_entry["attempt"] == 1
        assert log_entry["max_retries"] == 3
        assert log_entry["delay_seconds"] == 2.5
        assert log_entry["error_type"] == "Exception"
        assert "Test error" in log_entry["error_message"]
        assert "timestamp" in log_entry

    def test_create_log_entry_with_context(self):
        """Test creating log entry with additional context."""
        error = Exception("Rate limit")
        context = {"model": "gpt-4", "stage": "thesis"}

        log_entry = create_retry_log_entry(
            attempt=2, max_retries=3, delay=4.0, error=error, context=context
        )

        assert log_entry["model"] == "gpt-4"
        assert log_entry["stage"] == "thesis"
        assert log_entry["is_rate_limit"] is True

    def test_log_entry_rate_limit_detection(self):
        """Test rate limit detection in log entry."""
        rate_error = Exception("Rate limit exceeded")
        log_entry = create_retry_log_entry(0, 3, 1.0, rate_error)
        assert log_entry["is_rate_limit"] is True

        other_error = Exception("Network timeout")
        log_entry = create_retry_log_entry(0, 3, 1.0, other_error)
        assert log_entry["is_rate_limit"] is False

    def test_log_entry_truncates_long_messages(self):
        """Test that long error messages are truncated."""
        long_message = "Error: " + "x" * 300
        error = Exception(long_message)
        log_entry = create_retry_log_entry(0, 3, 1.0, error)
        assert len(log_entry["error_message"]) <= 200


class TestPrefectConfiguration:
    """Test Prefect-specific configuration helpers."""

    def test_prefect_retry_config(self):
        """Test PREFECT_RETRY_CONFIG has expected structure."""
        assert "retries" in PREFECT_RETRY_CONFIG
        assert "retry_delay_seconds" in PREFECT_RETRY_CONFIG
        assert isinstance(PREFECT_RETRY_CONFIG["retry_delay_seconds"], list)

    def test_get_prefect_retry_delays_default(self):
        """Test default Prefect retry delays."""
        delays = get_prefect_retry_delays(3, 1.0)
        assert delays == [1.0, 2.0, 4.0]

    def test_get_prefect_retry_delays_custom(self):
        """Test custom Prefect retry delays."""
        delays = get_prefect_retry_delays(4, 2.0)
        assert delays == [2.0, 4.0, 8.0, 16.0]

    def test_get_prefect_retry_delays_zero(self):
        """Test zero retries returns empty list."""
        delays = get_prefect_retry_delays(0, 1.0)
        assert delays == []


class TestIntegration:
    """Integration tests for retry system."""

    def test_realistic_api_call_simulation(self):
        """Simulate realistic API call with intermittent failures."""
        call_count = 0

        def simulated_api_call():
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                raise Exception("503 Service Unavailable")
            elif call_count == 2:
                raise Exception("Rate limit exceeded")
            else:
                return {"status": "success", "data": "result"}

        result = retry_with_backoff(simulated_api_call, max_retries=3, base_delay=0.01)

        assert result["status"] == "success"
        assert call_count == 3

    def test_exponential_growth_verification(self):
        """Verify exponential growth of delays."""
        delays = []
        for i in range(5):
            delay = exponential_backoff_with_jitter(i, base_delay=1.0, jitter=False)
            delays.append(delay)

        # Verify exponential growth
        assert delays[1] == delays[0] * 2
        assert delays[2] == delays[1] * 2
        assert delays[3] == delays[2] * 2
