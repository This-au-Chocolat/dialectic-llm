"""Evaluation functions."""

import math

# Import for SentenceTransformer
from sentence_transformers import SentenceTransformer, util

from utils.data_utils import normalize_answer

# Model for semantic coherence, loaded once
_coherence_model = None


def get_coherence_model():
    global _coherence_model
    if _coherence_model is None:
        _coherence_model = SentenceTransformer("all-mpnet-base-v2")
    return _coherence_model


def coherence_ts(text1: str, text2: str) -> float:
    """
    Calculates the semantic coherence (cosine similarity) between two texts
    using the 'all-mpnet-base-v2' SentenceTransformer model.

    Args:
        text1: The first text (e.g., Thesis).
        text2: The second text (e.g., Synthesis).

    Returns:
        A float representing the cosine similarity between the embeddings of the two texts.
    """
    model = get_coherence_model()

    # Encode the texts
    embeddings1 = model.encode(text1, convert_to_tensor=True)
    embeddings2 = model.encode(text2, convert_to_tensor=True)

    # Calculate cosine similarity
    cosine_scores = util.cos_sim(embeddings1, embeddings2)

    # Return the similarity score as a float
    return cosine_scores.item()


def evaluate_exact_match(y_true: float, y_pred_raw: str) -> bool:
    """
    Evaluate exact match between a float ground truth and a raw predicted string.

    This function normalizes the predicted string to extract a numerical value and
    compares it to the ground truth float using math.isclose for robust float comparison.

    Args:
        y_true: The ground truth float value.
        y_pred_raw: The raw predicted string.

    Returns:
        True if the normalized prediction is close to the ground truth, False otherwise.
    """
    normalized_pred = normalize_answer(y_pred_raw)
    if not normalized_pred:
        return False
    try:
        pred_float = float(normalized_pred)
        return math.isclose(y_true, pred_float)
    except (ValueError, TypeError):
        return False
