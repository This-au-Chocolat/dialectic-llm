# src/dialectic_llm/data.py
import re

from datasets import load_dataset


def load_batch(n: int, seed: int, split: str = "train"):
    """
    Loads a batch of n items from the GSM8K dataset with a given seed.
    """
    dataset = load_dataset("gsm8k", "main", split=split)
    return dataset.shuffle(seed=seed).select(range(n))


def normalize_answer(answer: str) -> str:
    """
    Normalizes a numerical answer string by extracting the last numerical
    value, removing commas and spaces. It specifically handles the GSM8K
    format where the final answer is preceded by "#### ".
    """
    parts = answer.split("####")
    if len(parts) > 1:
        # GSM8K format found, take the part after "####"
        final_answer = parts[1]
        # Remove commas and spaces
        cleaned_answer = final_answer.replace(",", "").strip()
        return cleaned_answer
    else:
        # Fallback for cases where "####" is not present
        # Find all sequences that look like numbers
        matches = re.findall(r"[\d,.\s]+", answer)
        if not matches:
            return ""

        potential_number = matches[-1]

        # Remove commas and spaces
        cleaned = potential_number.replace(",", "").replace(" ", "").strip()

        # If there are multiple dots, assume they are thousand separators
        if cleaned.count(".") > 1:
            cleaned = cleaned.replace(".", "")

        return cleaned
