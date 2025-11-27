"""LLM client wrapper for OpenAI and DeepSeek API calls."""

import os
from typing import Any, Dict, Optional

from openai import OpenAI


class LLMClient:
    """Client for making LLM calls with consistent interface."""

    def __init__(
        self, api_key: Optional[str] = None, model: str = "gpt-4", base_url: Optional[str] = None
    ):
        """
        Initialize the LLM client.

        Args:
            api_key: API key (if None, reads from DEEPSEEK_API_KEY or OPENAI_API_KEY env var)
            model: Default model to use
            base_url: Base URL for API (use "https://api.deepseek.com" for DeepSeek)
        """
        # Auto-detect provider based on model or use explicit base_url
        if base_url is None:
            if model and "deepseek" in model.lower():
                base_url = "https://api.deepseek.com"
                self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
                if not self.api_key:
                    raise ValueError(
                        "DeepSeek API key is required. Set DEEPSEEK_API_KEY environment variable."
                    )
            else:
                self.api_key = api_key or os.getenv("OPENAI_API_KEY")
                if not self.api_key:
                    raise ValueError(
                        "OpenAI API key is required. Set OPENAI_API_KEY environment variable."
                    )
        else:
            # Explicit base_url provided
            if "deepseek" in base_url.lower():
                self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
                if not self.api_key:
                    raise ValueError(
                        "DeepSeek API key is required. Set DEEPSEEK_API_KEY environment variable."
                    )
            else:
                self.api_key = api_key or os.getenv("OPENAI_API_KEY")
                if not self.api_key:
                    raise ValueError(
                        "OpenAI API key is required. Set OPENAI_API_KEY environment variable."
                    )

        # Initialize client with optional base_url
        if base_url:
            self.client = OpenAI(api_key=self.api_key, base_url=base_url)
        else:
            self.client = OpenAI(api_key=self.api_key)

        self.default_model = model
        self.base_url = base_url

    def call(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Make a single LLM call.

        Args:
            prompt: The prompt text
            model: Model to use (if None, uses default)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for the API call

        Returns:
            Dictionary with response data including usage information
        """
        model = model or self.default_model

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            # Extract relevant information
            choice = response.choices[0]
            usage = response.usage

            return {
                "completion": choice.message.content,
                "model": model,
                "prompt": prompt,
                "temperature": temperature,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                },
                "finish_reason": choice.finish_reason,
                "response_id": response.id,
                "created": response.created,
            }

        except Exception as e:
            return {
                "completion": "",
                "model": model,
                "prompt": prompt,
                "temperature": temperature,
                "error": str(e),
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }


def create_baseline_prompt(question: str) -> str:
    """
    Create a baseline prompt for GSM8K problems.

    Args:
        question: The math problem question

    Returns:
        Formatted prompt for baseline solving
    """
    prompt = f"""Solve this math problem step by step. Show your work and give the final numerical answer.

Problem: {question}

Please solve this step by step and end your response with "#### [final_answer]" where [final_answer] is just the number."""  # noqa: E501
    return prompt


def extract_gsm8k_answer(completion: str) -> str:
    """
    Extract the final answer from a GSM8K completion.

    Args:
        completion: The LLM's completion text

    Returns:
        The extracted final answer
    """
    # Look for the #### pattern
    if "####" in completion:
        parts = completion.split("####")
        if len(parts) > 1:
            # Take the last part after ####
            answer_part = parts[-1].strip()
            # Extract just the number
            import re

            match = re.search(r"[\d,.\s]+", answer_part)
            if match:
                return match.group(0).strip()

    # Fallback: look for numbers at the end
    import re

    numbers = re.findall(r"[\d,.\s]+", completion)
    if numbers:
        return numbers[-1].strip()

    return ""
