"""Retry and rate limiting utilities for robust LLM calls.

This module provides:
1. Exponential backoff with jitter for retries
2. Rate limit detection and handling
3. Retry logging for observability

Task: S2-01 - Escalado Prefect + retries/backoff + rate-limit aware
"""

import random
import time
from typing import Any, Callable, Dict, Optional


class RateLimitError(Exception):
    """Exception raised when API rate limit is hit."""

    pass


class RetryableError(Exception):
    """Exception for errors that should be retried."""

    pass


def exponential_backoff_with_jitter(
    attempt: int, base_delay: float = 1.0, max_delay: float = 60.0, jitter: bool = True
) -> float:
    """
    Calculate exponential backoff delay with optional jitter.

    Args:
        attempt: Current retry attempt (0-indexed)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        jitter: Whether to add random jitter (default: True)

    Returns:
        Delay in seconds to wait before next retry

    Examples:
        >>> exponential_backoff_with_jitter(0, jitter=False)
        1.0
        >>> exponential_backoff_with_jitter(1, jitter=False)
        2.0
        >>> exponential_backoff_with_jitter(2, jitter=False)
        4.0
    """
    # Calculate exponential delay: base_delay * 2^attempt
    delay = base_delay * (2**attempt)

    # Cap at max_delay
    delay = min(delay, max_delay)

    # Add jitter (uniform random between 0 and delay)
    if jitter:
        delay = random.uniform(0, delay)

    return delay


def is_rate_limit_error(error: Exception) -> bool:
    """
    Check if an error is a rate limit error.

    Args:
        error: Exception to check

    Returns:
        True if error is related to rate limiting
    """
    error_str = str(error).lower()

    # Common rate limit indicators
    rate_limit_indicators = [
        "rate limit",
        "rate_limit",
        "ratelimit",
        "429",
        "too many requests",
        "quota exceeded",
        "throttle",
    ]

    return any(indicator in error_str for indicator in rate_limit_indicators)


def is_retryable_error(error: Exception) -> bool:
    """
    Check if an error should be retried.

    Args:
        error: Exception to check

    Returns:
        True if error is retryable (network, timeout, rate limit, etc.)
    """
    if isinstance(error, (RateLimitError, RetryableError)):
        return True

    error_str = str(error).lower()

    # Retryable error patterns
    retryable_patterns = [
        "timeout",
        "connection",
        "network",
        "temporary",
        "unavailable",
        "503",
        "502",
        "500",
        "overloaded",
    ]

    return is_rate_limit_error(error) or any(pattern in error_str for pattern in retryable_patterns)


def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    logger: Optional[Any] = None,
    **kwargs,
) -> Any:
    """
    Execute a function with exponential backoff retry logic.

    Args:
        func: Function to execute
        max_retries: Maximum number of retries (default: 3)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        jitter: Whether to add jitter (default: True)
        logger: Optional logger for retry events
        **kwargs: Arguments to pass to func

    Returns:
        Result of successful function call

    Raises:
        Exception: Last exception if all retries fail

    Examples:
        >>> def flaky_api_call():
        ...     # Simulated API call
        ...     return {"result": "success"}
        >>> result = retry_with_backoff(flaky_api_call, max_retries=3)
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            # Try to execute the function
            result = func(**kwargs)
            return result

        except Exception as e:
            last_exception = e

            # Check if we should retry
            if not is_retryable_error(e):
                # Non-retryable error, raise immediately
                if logger:
                    logger.error(f"Non-retryable error on attempt {attempt}: {e}")
                raise

            # If this was the last attempt, raise
            if attempt >= max_retries:
                if logger:
                    logger.error(f"Max retries ({max_retries}) exceeded. Last error: {e}")
                raise

            # Calculate backoff delay
            delay = exponential_backoff_with_jitter(
                attempt, base_delay=base_delay, max_delay=max_delay, jitter=jitter
            )

            # Log retry attempt
            if logger:
                error_type = "rate_limit" if is_rate_limit_error(e) else "retryable"
                logger.warning(
                    f"Retry attempt {attempt + 1}/{max_retries} "
                    f"after {delay:.2f}s delay. "
                    f"Error type: {error_type}. "
                    f"Error: {str(e)[:100]}"
                )

            # Wait before retrying
            time.sleep(delay)

    # Should never reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry logic failed without exception")


def create_retry_log_entry(
    attempt: int,
    max_retries: int,
    delay: float,
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a structured log entry for a retry event.

    Args:
        attempt: Current attempt number
        max_retries: Maximum retry attempts
        delay: Delay before next retry
        error: The error that triggered the retry
        context: Optional context information

    Returns:
        Dictionary with retry event information
    """
    return {
        "event_type": "retry",
        "attempt": attempt,
        "max_retries": max_retries,
        "delay_seconds": round(delay, 3),
        "error_type": type(error).__name__,
        "error_message": str(error)[:200],
        "is_rate_limit": is_rate_limit_error(error),
        "is_retryable": is_retryable_error(error),
        "timestamp": time.time(),
        **(context or {}),
    }


# Prefect-specific retry configuration
PREFECT_RETRY_CONFIG = {
    "retries": 3,
    "retry_delay_seconds": [1, 2, 4],  # Exponential: 1s, 2s, 4s
}


def get_prefect_retry_delays(max_retries: int = 3, base_delay: float = 1.0) -> list[float]:
    """
    Generate retry delays for Prefect task configuration.

    Args:
        max_retries: Number of retries
        base_delay: Base delay in seconds

    Returns:
        List of delays for each retry attempt

    Examples:
        >>> get_prefect_retry_delays(3, 1.0)
        [1.0, 2.0, 4.0]
    """
    return [base_delay * (2**i) for i in range(max_retries)]
