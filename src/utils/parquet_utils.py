"""Utilities for creating Parquet files from evaluation results."""

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def create_parquet_from_results(
    results: List[Dict[str, Any]],
    run_id: str,
    flow_type: str,
    usage_key: str = "llm_usage",
    answer_key: str = "predicted_answer",
) -> str:
    """
    Create a Parquet file from evaluation results.

    This is a consolidated function that replaces the duplicated
    create_results_parquet and create_tas_parquet functions.

    Args:
        results: List of result dictionaries
        run_id: Run identifier
        flow_type: Type of flow ("baseline", "tas", etc.) for filename
        usage_key: Key for token usage data ("llm_usage" or "tas_usage")
        answer_key: Key for predicted answer ("predicted_answer" or "predicted_answer_raw")

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
            answer_key: result.get(answer_key, result.get("predicted_answer_raw", "")),
            "has_error": bool(result.get("error")),
            "prompt_tokens": result.get(usage_key, {}).get("prompt_tokens", 0),
            "completion_tokens": result.get(usage_key, {}).get("completion_tokens", 0),
            "total_tokens": result.get(usage_key, {}).get("total_tokens", 0),
        }
        df_data.append(row)

    df = pd.DataFrame(df_data)

    # Save to Parquet
    filename = f"{flow_type}_{run_id}.parquet"
    filepath = analytics_dir / filename
    df.to_parquet(filepath, index=False)

    return str(filepath)


# Legacy wrappers for backward compatibility
def create_results_parquet(results: List[Dict[str, Any]], run_id: str) -> str:
    """
    Create a Parquet file with baseline results (legacy wrapper).

    Args:
        results: List of result dictionaries
        run_id: Run identifier

    Returns:
        Path to created Parquet file
    """
    return create_parquet_from_results(
        results=results,
        run_id=run_id,
        flow_type="baseline",
        usage_key="llm_usage",
        answer_key="predicted_answer",
    )


def create_tas_parquet(results: List[Dict[str, Any]], run_id: str) -> str:
    """
    Create Parquet file from T-A-S results for analytics (legacy wrapper).

    Args:
        results: List of result dictionaries
        run_id: Run identifier

    Returns:
        Path to created Parquet file
    """
    return create_parquet_from_results(
        results=results,
        run_id=run_id,
        flow_type="tas",
        usage_key="tas_usage",
        answer_key="predicted_answer_raw",
    )
