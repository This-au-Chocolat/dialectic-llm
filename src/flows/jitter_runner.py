import logging

from utils.backoff import RetryableError, retry_with_backoff

logger = logging.getLogger("jitter")
logger.setLevel(logging.DEBUG)


def simulated_llm_call(param: str) -> dict:
    import random

    if random.random() < 0.7:
        raise RetryableError("Simulated transient failure")
    return {"result": f"Successful response for {param}"}


def jitter():
    params = ["prompt1", "prompt2", "prompt3"]
    results = []
    for param in params:
        try:
            result = retry_with_backoff(
                func=simulated_llm_call,
                max_retries=5,
                base_delay=1.0,
                max_delay=10.0,
                jitter=True,
                logger=logger,
                param=param,
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Final failure for {param}: {e}")
            results.append(None)
    return results
