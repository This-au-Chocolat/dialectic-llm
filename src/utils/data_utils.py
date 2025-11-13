"""Utilities for loading and processing GSM8K dataset."""

from typing import Any, Dict, List

from dialectic_llm.data import load_batch


def load_gsm8k_problems(n: int, seed: int = 42) -> List[Dict[str, Any]]:
    """
    Load a batch of GSM8K problems with standardized processing.

    This consolidates the duplicated load_gsm8k_batch and load_tas_batch functions
    that had 97% identical code.

    Args:
        n: Number of problems to load
        seed: Random seed for reproducibility

    Returns:
        List of problem dictionaries with standardized structure:
        - problem_id: Unique identifier (gsm8k_0000, gsm8k_0001, etc.)
        - question: The math problem text
        - answer: Extracted numeric answer as float
        - answer_raw: Original GSM8K answer with full solution steps
    """
    dataset = load_batch(n=n, seed=seed)

    problems = []
    for i, item in enumerate(dataset):
        # Extract numeric answer from GSM8K format (after ####)
        numeric_answer = extract_answer_from_gsm8k(item["answer"], normalize=False)

        try:
            answer_float = float(numeric_answer.replace(",", ""))
        except (ValueError, AttributeError):
            # Fallback: try to find last number in answer
            import re

            numbers = re.findall(r"[\d,]+", item["answer"])
            answer_float = float(numbers[-1].replace(",", "")) if numbers else 0.0

        problems.append(
            {
                "problem_id": f"gsm8k_{i:04d}",
                "question": item["question"],
                "answer": answer_float,  # Extracted numeric answer
                "answer_raw": item["answer"],  # Full GSM8K answer with steps
            }
        )

    return problems


# Legacy wrappers for backward compatibility
def load_gsm8k_batch(n: int, seed: int = 42) -> List[Dict[str, Any]]:
    """
    Load a batch of GSM8K problems (legacy wrapper for baseline flow).

    Args:
        n: Number of problems to load
        seed: Random seed for reproducibility

    Returns:
        List of problem dictionaries
    """
    return load_gsm8k_problems(n=n, seed=seed)


def load_tas_batch(n: int, seed: int = 42) -> List[Dict[str, Any]]:
    """
    Load a batch of GSM8K problems for T-A-S evaluation (legacy wrapper).

    Args:
        n: Number of problems to load
        seed: Random seed for reproducibility

    Returns:
        List of problem dictionaries
    """
    return load_gsm8k_problems(n=n, seed=seed)


def extract_answer_from_gsm8k(completion: str, normalize: bool = False) -> str:
    """
    Extract and optionally normalize the final answer from a GSM8K completion.

    This function consolidates the logic from extract_gsm8k_answer() and normalize_answer()
    to provide a unified interface for answer extraction.

    Args:
        completion: The LLM's completion text or GSM8K answer string
        normalize: If True, clean the answer by removing commas, spaces, and handling dots
                  If False, return raw extracted answer with formatting preserved

    Returns:
        The extracted final answer, optionally normalized
    """
    import re

    # Look for the #### pattern (GSM8K standard format)
    if "####" in completion:
        parts = completion.split("####")
        if len(parts) > 1:
            # Take the last part after ####
            answer_part = parts[-1].strip()
            # Extract the number
            match = re.search(r"[\d,.\s]+", answer_part)
            if match:
                raw_answer = match.group(0).strip()
                if normalize:
                    return _normalize_numeric_answer(raw_answer)
                return raw_answer
            elif not normalize:
                return ""  # No number found

    # Fallback: look for numbers at the end
    numbers = re.findall(r"[\d,.\s]+", completion)
    if numbers:
        raw_answer = numbers[-1].strip()
        if normalize:
            return _normalize_numeric_answer(raw_answer)
        return raw_answer

    return ""  # No numbers found


def _normalize_numeric_answer(answer: str) -> str:
    """
    Normalize a numeric answer string by cleaning formatting.

    Args:
        answer: Raw numeric answer string

    Returns:
        Cleaned numeric string
    """
    # Remove commas and spaces
    cleaned = answer.replace(",", "").replace(" ", "").strip()

    # Remove trailing dot if it is the last character
    if cleaned.endswith("."):
        cleaned = cleaned[:-1]

    # If there are multiple dots, assume they are thousand separators
    if cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")

    return cleaned


# Legacy wrapper functions for backward compatibility
def extract_gsm8k_answer(completion: str) -> str:
    """
    Extract the final answer from a GSM8K completion (legacy wrapper).

    Args:
        completion: The LLM's completion text

    Returns:
        The extracted final answer
    """
    return extract_answer_from_gsm8k(completion, normalize=False)


def normalize_answer(answer: str) -> str:
    """
    Normalize a numerical answer string (legacy wrapper).

    Args:
        answer: Answer string to normalize

    Returns:
        Normalized answer string
    """
    return extract_answer_from_gsm8k(answer, normalize=True)
