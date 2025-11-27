"""Token counting utilities for monitoring costs and usage."""

from typing import Dict, Union

import tiktoken


def count_tokens(event: Dict[str, Union[str, int, float]], model: str = "gpt-4") -> Dict[str, int]:
    """
    Count tokens in an event for prompt and completion.

    This function extracts prompt and completion text from an event and counts
    tokens using tiktoken. It integrates with the logger to track token usage.

    Args:
        event: Event dictionary containing 'prompt' and 'completion' keys
        model: Model name for tiktoken encoding (default: gpt-4)

    Returns:
        Dictionary with token counts: {
            'prompt_tokens': int, 'completion_tokens': int, 'total_tokens': int
        }
    """
    try:
        # Get the appropriate encoding for the model
        if model.startswith("gpt-4"):
            encoding = tiktoken.encoding_for_model("gpt-4")
        elif model.startswith("gpt-3.5"):
            encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        else:
            # Default to cl100k_base encoding (used by gpt-4 and gpt-3.5-turbo)
            encoding = tiktoken.get_encoding("cl100k_base")

        # Extract text from event
        prompt_text = event.get("prompt", "")
        completion_text = event.get("completion", "")

        # Count tokens
        prompt_tokens = len(encoding.encode(str(prompt_text))) if prompt_text else 0
        completion_tokens = len(encoding.encode(str(completion_text))) if completion_text else 0
        total_tokens = prompt_tokens + completion_tokens

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

    except Exception as e:
        # Return zeros if token counting fails
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "error": str(e)}


def estimate_cost(token_counts: Dict[str, int], model: str = "gpt-4") -> float:
    """
    Estimate cost in USD based on token counts and model pricing.

    Args:
        token_counts: Token counts from count_tokens()
        model: Model name for pricing

    Returns:
        Estimated cost in USD
    """
    # Pricing as of 2024 (USD per 1000 tokens)
    pricing = {
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
        "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
        "deepseek-chat": {"prompt": 0.00014, "completion": 0.00028},
        "deepseek-coder": {"prompt": 0.00014, "completion": 0.00028},
    }

    # Default to gpt-4 pricing if model not found
    model_key = model if model in pricing else "gpt-4"
    rates = pricing[model_key]

    prompt_cost = (token_counts.get("prompt_tokens", 0) / 1000) * rates["prompt"]
    completion_cost = (token_counts.get("completion_tokens", 0) / 1000) * rates["completion"]

    return prompt_cost + completion_cost


def add_token_info(event: Dict, model: str = "gpt-4") -> Dict:
    """
    Add token count and cost information to an event.

    Args:
        event: Event dictionary to augment
        model: Model name for token counting

    Returns:
        Event with added token information
    """
    token_info = count_tokens(event, model)
    cost = estimate_cost(token_info, model)

    # Add token information to event
    event.update({"tokens": token_info, "estimated_cost_usd": round(cost, 6)})

    return event
