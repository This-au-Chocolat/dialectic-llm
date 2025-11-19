import math

import pytest

from src.utils.evaluation import coherence_ts


def test_coherence_ts_identical_sentences():
    """
    Test that identical sentences have a cosine similarity of 1.0.
    """
    text1 = "This is a test sentence."
    text2 = "This is a test sentence."
    similarity = coherence_ts(text1, text2)
    assert similarity == pytest.approx(1.0, abs=1e-6)


def test_coherence_ts_highly_related_sentences():
    """
    Test that highly related sentences have a high cosine similarity.
    """
    text1 = "The cat sat on the mat."
    text2 = "A feline rested on the rug."
    similarity = coherence_ts(text1, text2)
    # The exact value might vary slightly, but it should be high
    assert similarity > 0.65


def test_coherence_ts_unrelated_sentences():
    """
    Test that unrelated sentences have a low cosine similarity.
    """
    text1 = "The cat sat on the mat."
    text2 = "Quantum physics explains the universe."
    similarity = coherence_ts(text1, text2)
    # The exact value might vary, but it should be low
    assert similarity < 0.3


def test_coherence_ts_empty_strings():
    """
    Test that empty strings return a specific behavior (e.g., 0.0 or handle error).
    SentenceTransformer might return NaN or raise an error for empty strings,
    or assign a default vector. We'll check for a numeric result for now.
    """
    text1 = ""
    text2 = "A short sentence."
    similarity = coherence_ts(text1, text2)
    # Check if the result is a finite number, not NaN or inf
    assert (
        isinstance(similarity, float) and not math.isnan(similarity) and not math.isinf(similarity)
    )
    # It's likely to be a low similarity given one empty string
    assert similarity < 0.2  # Expect very low similarity


def test_coherence_ts_different_languages():
    """
    Test that sentences in different languages have a low cosine similarity.
    all-mpnet-base-v2 is primarily English.
    """
    text1 = "Hello world."
    text2 = "Hola mundo."
    similarity = coherence_ts(text1, text2)
    assert similarity < 0.5  # Expect low similarity for different languages
