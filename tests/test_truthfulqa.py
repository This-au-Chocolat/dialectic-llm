import importlib.util
import subprocess

import pytest

from src.dialectic_llm.data import load_truthfulqa_problems, normalize_truthfulqa_answer


# Fixture to ensure datasets library is installed
@pytest.fixture(scope="module", autouse=True)
def check_and_install_datasets():
    if importlib.util.find_spec("datasets") is None:
        print("datasets library not found. Attempting to install with uv...")
        # Assuming uv is in PATH and the project is using a uv-managed venv
        result = subprocess.run(
            ["uv", "pip", "install", "datasets"],
            capture_output=True,
            text=True,
            check=False,  # Don't raise an exception for non-zero exit codes yet
        )
        if result.returncode != 0:
            print(f"Error installing datasets: {result.stderr}")
            pytest.fail(f"Failed to install datasets library: {result.stderr}")
        print("datasets library installed successfully.")
    # No need to import datasets here, as functions using it are imported directly
    # and will only run if the import succeeds (which means it's installed).


@pytest.mark.parametrize(
    "answer, expected",
    [
        ("Yes.", "yes"),
        ("no", "no"),
        ("Y", "yes"),
        ("N", "no"),
        ("correct", "yes"),
        ("   Free form answer. ", "free form answer"),
        ("Another example?", "another example"),
        ("123.", "123"),
        ("True", "true"),
        ("False", "false"),
    ],
)
def test_normalize_truthfulqa_answer(answer, expected):
    assert normalize_truthfulqa_answer(answer) == expected


def test_load_truthfulqa_problems_50_items():
    """
    Test loading 50 items from TruthfulQA dataset.
    This test will download the dataset if not cached.
    """
    n_items = 50
    seed = 42
    problems = load_truthfulqa_problems(n=n_items, seed=seed)

    assert len(problems) == n_items
    for problem in problems:
        assert "problem_id" in problem
        assert problem["problem_id"].startswith("truthfulqa_")
        assert "question" in problem
        assert "best_answer" in problem
        assert "correct_answers" in problem
        assert isinstance(problem["correct_answers"], list)
        assert len(problem["correct_answers"]) > 0  # Should have at least one correct answer
        assert "incorrect_answers" in problem
        assert isinstance(problem["incorrect_answers"], list)
        # Check that answers are normalized
        assert all(isinstance(ans, str) for ans in problem["correct_answers"])
        assert all(isinstance(ans, str) for ans in problem["incorrect_answers"])
        assert isinstance(problem["best_answer"], str)
