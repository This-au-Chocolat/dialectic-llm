"""Baseline flow for GSM8K evaluation using Prefect."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from prefect import flow, task

from dialectic_llm.data import load_batch
from llm.client import LLMClient, create_baseline_prompt, extract_gsm8k_answer
from utils.evaluation import evaluate_exact_match
from utils.log_utils import create_run_summary, log_event_jsonl


@task(name="load_gsm8k_batch")
def load_gsm8k_batch(n: int, seed: int = 42) -> List[Dict[str, Any]]:
    """
    Load a batch of GSM8K problems.

    Args:
        n: Number of problems to load
        seed: Random seed for reproducibility

    Returns:
        List of problem dictionaries
    """
    dataset = load_batch(n=n, seed=seed)

    problems = []
    for i, item in enumerate(dataset):
        problems.append(
            {
                "problem_id": f"gsm8k_{i:04d}",
                "question": item["question"],
                "answer": float(item["answer"]),  # GSM8K answers are numeric
                "answer_raw": item["answer"],
            }
        )

    return problems


@task(name="solve_baseline_problem")
def solve_baseline_problem(
    problem: Dict[str, Any], run_id: str, llm_client: LLMClient, model: str = "gpt-4"
) -> Dict[str, Any]:
    """
    Solve a single GSM8K problem using baseline approach.

    Args:
        problem: Problem dictionary with question and answer
        run_id: Unique identifier for this run
        llm_client: LLM client instance
        model: Model to use

    Returns:
        Result dictionary with prediction and evaluation
    """
    # Create baseline prompt
    prompt = create_baseline_prompt(problem["question"])

    # Make LLM call
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
        "predicted_answer_raw": predicted_answer_raw,
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
def create_results_parquet(results: List[Dict[str, Any]], run_id: str) -> str:
    """
    Create a Parquet file with baseline results.

    Args:
        results: List of result dictionaries
        run_id: Run identifier

    Returns:
        Path to created Parquet file
    """
    # Create analytics directory
    analytics_dir = Path("analytics/parquet")
    analytics_dir.mkdir(parents=True, exist_ok=True)

    # Create DataFrame
    df_data = []
    for result in results:
        row = {
            "run_id": result["run_id"],
            "problem_id": result["problem_id"],
            "dataset": result["dataset"],
            "phase": result["phase"],
            "model": result["model"],
            "is_correct": result["is_correct"],
            "true_answer": result["true_answer"],
            "predicted_answer_raw": result["predicted_answer_raw"],
            "has_error": bool(result.get("error")),
            "prompt_tokens": result.get("llm_usage", {}).get("prompt_tokens", 0),
            "completion_tokens": result.get("llm_usage", {}).get("completion_tokens", 0),
            "total_tokens": result.get("llm_usage", {}).get("total_tokens", 0),
        }
        df_data.append(row)

    df = pd.DataFrame(df_data)

    # Save to Parquet
    filename = f"baseline_{run_id}.parquet"
    filepath = analytics_dir / filename
    df.to_parquet(filepath, index=False)

    return str(filepath)


@flow(name="baseline_gsm8k_flow", log_prints=True)
def run_baseline_gsm8k(
    n_problems: int = 200, seed: int = 42, model: str = "gpt-4", run_id: str = None
) -> Dict[str, Any]:
    """
    Run baseline evaluation on GSM8K problems.

    Args:
        n_problems: Number of problems to evaluate (≥200 for S1-06)
        seed: Random seed for reproducibility
        model: LLM model to use
        run_id: Unique run identifier (auto-generated if None)

    Returns:
        Summary of the run results
    """
    # Generate run ID if not provided
    if run_id is None:
        run_id = f"baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

    print(f"Starting baseline run: {run_id}")
    print(f"Problems: {n_problems}, Model: {model}, Seed: {seed}")

    # Initialize LLM client
    llm_client = LLMClient(model=model)

    # Load problems
    print("Loading GSM8K problems...")
    problems = load_gsm8k_batch(n=n_problems, seed=seed)
    print(f"Loaded {len(problems)} problems")

    # Solve problems
    print("Solving problems...")
    results = []
    total_cost = 0.0

    for i, problem in enumerate(problems):
        print(f"Solving problem {i+1}/{len(problems)}: {problem['problem_id']}")

        # Solve the problem
        result = solve_baseline_problem(
            problem=problem, run_id=run_id, llm_client=llm_client, model=model
        )

        # Log the result
        log_baseline_result(result)

        results.append(result)

        # Track cost (rough estimate)
        tokens = result.get("llm_usage", {}).get("total_tokens", 0)
        if tokens > 0:
            # Rough cost estimate for gpt-4: $0.03 per 1K prompt tokens,
            # $0.06 per 1K completion tokens. Simplified: use $0.045 per 1K tokens average
            cost = (tokens / 1000) * 0.045
            total_cost += cost

        # Safety check: don't spend too much
        if total_cost > 50.0:  # Stop if cost exceeds $50
            print(f"WARNING: Cost limit reached (${total_cost:.2f}). Stopping at {i+1} problems.")
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
    parquet_path = create_results_parquet(results, run_id)
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
    result = run_baseline_gsm8k(n_problems=5, model="gpt-4")  # Small test run
    print(f"Test run completed: {result}")
