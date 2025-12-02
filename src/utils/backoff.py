import random
import time
from functools import wraps


class RetryableError(Exception):
    """Exception for retryable errors."""

    pass


def retry_with_backoff(max_retries=5, base_delay=1.0, max_delay=60.0, exceptions=(RetryableError,)):
    """
    Decorator to retry a function with exponential backoff.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = base_delay
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries == max_retries:
                        raise
                    sleep_time = min(delay * (2**retries) + random.uniform(0, 1), max_delay)
                    print(
                        f"[Backoff] Retry {retries}/{max_retries} after error: {e}. "
                        f"Sleeping for {sleep_time:.2f}s."
                    )
                    time.sleep(sleep_time)

        return wrapper

    return decorator
