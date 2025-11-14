"""Baseline flow for GSM8K evaluation using Prefect."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from prefect import flow, task

from llm.client import LLMClient, create_baseline_prompt, extract_gsm8k_answer
from utils.evaluation import evaluate_exact_match
from utils.log_utils import create_run_summary, log_event_jsonl
from utils.parquet_utils import create_results_parquet


@task(name="load_gsm8k_batch")
def load_gsm8k_batch_task(n: int, seed: int = 42) -> List[Dict[str, Any]]:
    """
    Prefect task wrapper for loading GSM8K problems.

    Args:
        n: Number of problems to load
        seed: Random seed for reproducibility

    Returns:
        List of problem dictionaries
    """
    from utils.data_utils import load_gsm8k_batch

    return load_gsm8k_batch(n=n, seed=seed)


def _create_mock_response(question: str, expected_answer: float) -> Dict[str, Any]:
    """Create a mock LLM response for dry-run mode."""
    # Simple heuristic: if it's an addition problem, get it right most of the time
    import random

    # Extract numbers from question (for potential mock logic)
    # numbers = re.findall(r'\d+', question)  # Not currently used

    if random.random() < 0.8:  # 80% accuracy for mock
        mock_answer = int(expected_answer)
        completion = (
            f"Let me solve this step by step.\nThe answer is {mock_answer}.\n#### {mock_answer}"
        )
    else:
        # Wrong answer 20% of the time
        wrong_answer = int(expected_answer) + random.randint(1, 5)
        completion = (
            f"Let me solve this step by step.\nThe answer is {wrong_answer}.\n#### {wrong_answer}"
        )

    return {
        "completion": completion,
        "model": "mock-gpt-4",
        "usage": {
            "prompt_tokens": 50 + len(question) // 4,
            "completion_tokens": 25,
            "total_tokens": 75 + len(question) // 4,
        },
        "finish_reason": "stop",
        "response_id": f"mock-{random.randint(1000, 9999)}",
        "created": int(datetime.now().timestamp()),
    }


@task(name="solve_baseline_problem")
def solve_baseline_problem(
    problem: Dict[str, Any],
    run_id: str,
    llm_client: Optional[LLMClient] = None,
    model: str = "gpt-4",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Solve a single GSM8K problem using baseline approach.

    Args:
        problem: Problem dictionary with question and answer
        run_id: Unique identifier for this run
        llm_client: LLM client instance (None for dry run)
        model: Model to use
        dry_run: If True, use mock response

    Returns:
        Result dictionary with prediction and evaluation
    """
    # Create baseline prompt
    prompt = create_baseline_prompt(problem["question"])

    # Make LLM call (real or mock)
    if dry_run or llm_client is None:
        response = _create_mock_response(problem["question"], problem["answer"])
    else:
        response = llm_client.call(
            prompt=prompt,
            model=model,
            temperature=0.7,  # Standard baseline temperature
            max_tokens=1000,
        )

    # Extract answer
    predicted_answer_raw = extract_gsm8k_answer(response["completion"])

    # Evaluate
    is_correct = evaluate_exact_match(y_true=problem["answer"], y_pred_raw=predicted_answer_raw)

    # Create result
    result = {
        "run_id": run_id,
        "problem_id": problem["problem_id"],
        "dataset": "gsm8k",
        "phase": "baseline",
        "model": model,
        "question": problem["question"],
        "true_answer": problem["answer"],
        "predicted_answer": predicted_answer_raw,
        "is_correct": is_correct,
        "prompt": prompt,
        "completion": response["completion"],
        "llm_usage": response.get("usage", {}),
        "error": response.get("error"),
    }

    return result


@task(name="log_baseline_result")
def log_baseline_result(result: Dict[str, Any]) -> None:
    """
    Log a baseline result to JSONL with automatic token counting.

    Args:
        result: Result dictionary from solve_baseline_problem
    """
    # Log to shared events (sanitized)
    log_event_jsonl(result, model=result["model"])


@task(name="create_results_parquet")
def create_results_parquet_task(results: List[Dict[str, Any]], run_id: str) -> str:
    """
    Create a Parquet file with baseline results (Prefect task wrapper).

    Args:
        results: List of result dictionaries
        run_id: Run identifier

    Returns:
        Path to created Parquet file
    """
    return create_results_parquet(results, run_id)


@flow(name="baseline_gsm8k_flow", log_prints=True)
def run_baseline_gsm8k(
    n_problems: int = 200,
    seed: int = 42,
    model: str = "gpt-4",
    run_id: Optional[str] = None,
    dry_run: bool = False,
    max_cost_usd: float = 5.0,
) -> Dict[str, Any]:
    """
    Run baseline evaluation on GSM8K problems.

    Args:
        n_problems: Number of problems to evaluate (≥200 for S1-06)
        seed: Random seed for reproducibility
        model: LLM model to use
        run_id: Unique run identifier (auto-generated if None)
        dry_run: If True, use mock responses instead of real API calls
        max_cost_usd: Maximum cost limit in USD

    Returns:
        Summary of the run results
    """
    # Generate run ID if not provided
    if run_id is None:
        run_id = f"baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

    print(f"Starting baseline run: {run_id}")
    print(f"Problems: {n_problems}, Model: {model}, Seed: {seed}")

    if dry_run:
        print("🔄 DRY RUN MODE: Using mock responses")

    # Initialize LLM client
    try:
        llm_client = LLMClient(model=model)
        if dry_run:
            print("✅ LLM client initialized (dry run mode)")
    except ValueError as e:
        if "API key" in str(e):
            print("⚠️  No valid API key found - enabling dry run mode")
            dry_run = True
            llm_client = None
        else:
            raise

    # Load problems
    print("Loading GSM8K problems...")
    problems = load_gsm8k_batch_task(n=n_problems, seed=seed)
    print(f"Loaded {len(problems)} problems")

    # Solve problems
    print("Solving problems...")
    results = []
    total_cost = 0.0

    for i, problem in enumerate(problems):
        print(f"Solving problem {i + 1}/{len(problems)}: {problem['problem_id']}")

        # Solve the problem
        result = solve_baseline_problem(
            problem=problem, run_id=run_id, llm_client=llm_client, model=model, dry_run=dry_run
        )

        # Log the result
        log_baseline_result(result)

        results.append(result)

        # Track cost (rough estimate)
        tokens = result.get("llm_usage", {}).get("total_tokens", 0)
        if tokens > 0:
            if dry_run:
                # Mock cost for dry run (much lower)
                cost = (tokens / 1000) * 0.001  # $0.001 per 1K tokens for testing
            else:
                # Real cost estimate for gpt-4: $0.03 per 1K prompt tokens,
                # $0.06 per 1K completion tokens. Simplified: use $0.045 per 1K tokens average
                cost = (tokens / 1000) * 0.045
            total_cost += cost

        # Safety check: don't spend too much (skip in dry run)
        if not dry_run and total_cost > max_cost_usd:
            print(f"WARNING: Cost limit reached (${total_cost:.2f}). Stopping at {i + 1} problems.")
            break

    # Calculate metrics
    correct_count = sum(1 for r in results if r["is_correct"])
    accuracy = correct_count / len(results) if results else 0.0
    error_count = sum(1 for r in results if r.get("error"))

    print(f"Completed {len(results)} problems")
    print(f"Accuracy: {accuracy:.3f} ({correct_count}/{len(results)})")
    print(f"Errors: {error_count}")
    print(f"Estimated cost: ${total_cost:.2f}")

    # Create Parquet file
    print("Creating Parquet file...")
    parquet_path = create_results_parquet_task(results, run_id)
    print(f"Results saved to: {parquet_path}")

    # Create run summary
    create_run_summary(run_id=run_id, total_items=len(results), total_cost=total_cost)

    summary = {
        "run_id": run_id,
        "total_problems": len(results),
        "correct": correct_count,
        "accuracy": accuracy,
        "errors": error_count,
        "estimated_cost_usd": total_cost,
        "parquet_path": parquet_path,
        "model": model,
    }

    return summary


if __name__ == "__main__":
    # Run with default parameters for testing
    import os

    # Check if we have a real API key
    api_key = os.getenv("OPENAI_API_KEY", "")
    has_real_key = api_key and not api_key.startswith("sk-demo")

    if has_real_key:
        print("🔑 Real API key detected - running small test with real calls")
        result = run_baseline_gsm8k(n_problems=3, model="gpt-4", dry_run=False)
    else:
        print("🔄 Demo/no API key - running dry run test")
        result = run_baseline_gsm8k(n_problems=10, model="gpt-4", dry_run=True)

    print(f"Test run completed: {result}")
