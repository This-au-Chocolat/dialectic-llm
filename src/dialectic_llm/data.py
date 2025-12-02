import re
from typing import Any, Dict, List

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
        final_answer = parts[1].strip()
        # Extract the number from the beginning of the string
        match = re.match(r"[\d,.]+", final_answer)
        if match:
            number_str = match.group(0)
            # Remove commas
            cleaned_answer = number_str.replace(",", "")
            # Remove trailing dot if it is the last character
            if cleaned_answer.endswith("."):
                cleaned_answer = cleaned_answer[:-1]
            return cleaned_answer
        else:
            return ""  # No number found
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


def load_truthfulqa_batch(n: int, seed: int, split: str = "validation"):
    """
    Loads a batch of n items from the TruthfulQA dataset with a given seed.
    """
    dataset = load_dataset("truthful_qa", "generation", split=split)
    return dataset.shuffle(seed=seed).select(range(n))


def normalize_truthfulqa_answer(answer: str) -> str:
    """
    Normalizes a TruthfulQA answer by lowercasing, stripping whitespace,
    and handling common variations of 'yes' and 'no'.
    """
    cleaned_answer = answer.strip().lower()
    if cleaned_answer in ["yes", "y", "correct", "right"]:
        return "yes"
    if cleaned_answer in ["no", "n", "incorrect", "wrong"]:
        return "no"
    # Remove trailing punctuation
    return re.sub(r"[.!,?]$", "", cleaned_answer)


def load_truthfulqa_problems(n: int, seed: int = 42) -> List[Dict[str, Any]]:
    """
    Load a batch of TruthfulQA problems with standardized processing.
    """
    dataset = load_truthfulqa_batch(n=n, seed=seed)
    problems = []
    for i, item in enumerate(dataset):
        correct_answers: List[str] = item.get("correct_answers", [])
        normalized_correct = [normalize_truthfulqa_answer(ans) for ans in correct_answers]

        problems.append(
            {
                "problem_id": f"truthfulqa_{i:04d}",
                "question": item["question"],
                "best_answer": normalize_truthfulqa_answer(item["best_answer"]),
                "correct_answers": normalized_correct,
                "incorrect_answers": [
                    normalize_truthfulqa_answer(ans) for ans in item["incorrect_answers"]
                ],
            }
        )
    return problems
