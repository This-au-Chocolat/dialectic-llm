"""
Integration script for S1-10: Automatic JSONL to Parquet conversion after runs.

This script demonstrates how to use the analytics aggregation functionality
as part of the baseline runner workflow.
"""

import argparse

from flows.baseline import run_baseline_gsm8k
from utils.jsonl_to_parquet import aggregate_analytics_run


def run_baseline_with_analytics(
    n_problems: int = 200, model: str = "gpt-4", run_id: str = None, auto_convert: bool = True
) -> str:
    """
    Run baseline evaluation and automatically convert results to Parquet.

    This function implements the complete S1-10 workflow:
    1. Run baseline evaluation (generates JSONL logs)
    2. Convert JSONL logs to Parquet for analytics

    Args:
        n_problems: Number of problems to evaluate
        model: LLM model to use
        run_id: Custom run ID (auto-generated if None)
        auto_convert: Whether to automatically convert to Parquet

    Returns:
        Path to the created Parquet file (if auto_convert=True)
    """
    print("🚀 Starting baseline evaluation with analytics conversion")
    print(f"   Problems: {n_problems}, Model: {model}")

    # Run baseline evaluation
    summary = run_baseline_gsm8k(n_problems=n_problems, model=model, run_id=run_id)

    actual_run_id = summary.get("run_id")
    print(f"✅ Baseline evaluation completed: {actual_run_id}")

    if auto_convert and actual_run_id:
        print("📊 Converting logs to Parquet for analytics...")

        try:
            parquet_file = aggregate_analytics_run(
                run_id=actual_run_id, events_dir="logs/events", output_dir="analytics/parquet"
            )

            print(f"✅ Analytics conversion completed: {parquet_file}")

            # Show basic analytics
            import pandas as pd

            df = pd.read_parquet(parquet_file)
            print("📈 Analytics summary:")
            print(f"   Total events: {len(df)}")
            print(
                f"   Unique problems: {df['problem_id'].nunique() if 'problem_id' in df.columns else 'N/A'}"  # noqa: E501
            )

            if "tokens" in df.columns:
                total_tokens = (
                    df["tokens"]
                    .apply(lambda x: x.get("total_tokens", 0) if isinstance(x, dict) else 0)
                    .sum()
                )
                print(f"   Total tokens: {total_tokens:,}")

            if "estimated_cost_usd" in df.columns:
                total_cost = df["estimated_cost_usd"].sum()
                print(f"   Estimated cost: ${total_cost:.4f}")

            return parquet_file

        except Exception as e:
            print(f"❌ Analytics conversion failed: {e}")
            return None

    return None


def analyze_parquet_file(parquet_file: str) -> None:
    """
    Analyze a Parquet file and show basic statistics.

    Args:
        parquet_file: Path to the Parquet file
    """
    import pandas as pd

    try:
        df = pd.read_parquet(parquet_file)

        print(f"\n📊 Analysis of {parquet_file}")
        print(f"   Shape: {df.shape}")
        print(f"   Columns: {list(df.columns)}")

        # Show data types
        print("\n📋 Data types:")
        for col, dtype in df.dtypes.items():
            print(f"   {col}: {dtype}")

        # Show sample data
        print("\n🔍 Sample data:")
        print(df.head(3).to_string())

    except Exception as e:
        print(f"❌ Error analyzing Parquet file: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run baseline with automatic analytics conversion (S1-10 demo)"
    )

    parser.add_argument(
        "--problems",
        "-n",
        type=int,
        default=5,
        help="Number of problems to evaluate (default: 5 for demo)",
    )
    parser.add_argument(
        "--model", "-m", type=str, default="gpt-4", help="LLM model to use (default: gpt-4)"
    )
    parser.add_argument(
        "--run-id", type=str, default=None, help="Custom run ID (auto-generated if not provided)"
    )
    parser.add_argument(
        "--no-convert", action="store_true", help="Skip automatic Parquet conversion"
    )
    parser.add_argument(
        "--analyze", type=str, metavar="PARQUET_FILE", help="Analyze an existing Parquet file"
    )

    args = parser.parse_args()

    if args.analyze:
        analyze_parquet_file(args.analyze)
    else:
        # Check if we have an OpenAI API key
        import os

        if not os.getenv("OPENAI_API_KEY"):
            print(
                "⚠️  Warning: OPENAI_API_KEY not found. This is a demo that will use mocked responses."  # noqa: E501
            )
            print("   To run with real API calls, set your OpenAI API key in the environment.")

        parquet_file = run_baseline_with_analytics(
            n_problems=args.problems,
            model=args.model,
            run_id=args.run_id,
            auto_convert=not args.no_convert,
        )

        if parquet_file:
            print(f"\n🎯 S1-10 Complete! Analytics Parquet file created: {parquet_file}")
            print(f"   You can analyze it with: python {__file__} --analyze {parquet_file}")
        else:
            print("\n✅ Baseline evaluation completed (no analytics conversion)")
