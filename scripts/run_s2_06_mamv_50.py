"""
S2-06: Execute T-A-S+MAMV on 50 GSM8K problems with DeepSeek.
...
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from flows.tas import TASFlowConfig, run_tas_mamv
from utils.data_utils import load_gsm8k_batch
from utils.evaluation import coherence_ts, evaluate_exact_match

# Add src to path (must be before local imports)
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Cargar variables de entorno desde .env (after sys.path, before local imports)
load_dotenv()

# Configuration
SEED = 42
N_PROBLEMS = 50
MODEL = "deepseek-chat"
MAX_COST_USD = 5.0  # Budget for MAMV with DeepSeek
DATASET_FILE = "data/processed/gsm8k_s1_200_seed42_ids.json"

# Budget monitoring (DeepSeek pricing)
COST_PER_1K_TOKENS_PROMPT = 0.00028  # $0.28 per 1M tokens
COST_PER_1K_TOKENS_COMPLETION = 0.00042  # $0.42 per 1M tokens
ALERT_THRESHOLD_PCT = 0.90


def estimate_cost(total_tokens: int) -> float:
    """Estimate cost based on tokens (rough approximation)."""
    # Assume 40% prompt, 60% completion
    prompt_tokens = total_tokens * 0.4
    completion_tokens = total_tokens * 0.6
    return (prompt_tokens * COST_PER_1K_TOKENS_PROMPT / 1000) + (
        completion_tokens * COST_PER_1K_TOKENS_COMPLETION / 1000
    )


def load_problems_by_questions(n: int, seed: int) -> list:
    """
    Load problems using seed-based selection (same as S2-05 resume script).

    This ensures we get the exact same 200 problems as S2-05 for comparison.
    """
    problems = load_gsm8k_batch(n=n, seed=seed)
    return problems


def main():
    """Execute T-A-S+MAMV on 50 GSM8K problems."""
    print("=" * 80)
    print("S2-06: T-A-S+MAMV Execution on 50 GSM8K Problems (DeepSeek)")
    print("=" * 80)
    print(f"Model: {MODEL}")
    print(f"Dataset: {N_PROBLEMS} problems (seed={SEED})")
    print(f"Max budget: ${MAX_COST_USD:.2f} USD")
    print("MAMV: 3 instances with temperatures [0.65, 0.70, 0.75]")
    print("=" * 80)

    # Check if DeepSeek API key is set
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("❌ ERROR: DEEPSEEK_API_KEY not set in environment")
        print("Please set your DeepSeek API key before running this script")
        return

    # Load problems
    print("\n📥 Loading GSM8K problems...")
    problems = load_problems_by_questions(n=N_PROBLEMS, seed=SEED)
    print(f"✅ Loaded {len(problems)} problems")

    # Create run ID
    run_id = f"s2_06_mamv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"🆔 Run ID: {run_id}")

    # Create flow config
    flow_config = TASFlowConfig(seed=SEED, dataset_name="gsm8k", model_name=MODEL, run_id=run_id)

    # Results storage
    results = []
    total_cost = 0.0
    start_time = time.time()

    # Process each problem
    print(f"\n🧠 Executing T-A-S+MAMV on {len(problems)} problems...")
    print("━" * 80)

    for i, problem in enumerate(problems):
        problem_start = time.time()
        problem_id = problem.get("problem_id", f"problem_{i}")

        print(f"\n[{i + 1}/{len(problems)}] Processing: {problem_id}")

        try:
            # Execute MAMV flow
            mamv_result = run_tas_mamv(problem, flow_config)

            # Extract final answer
            final_answer = mamv_result["final_answer"]

            # Evaluate correctness
            try:
                y_true_float = float(problem["answer"])
                is_correct = evaluate_exact_match(y_true=y_true_float, y_pred_raw=final_answer)
            except (ValueError, TypeError):
                is_correct = False

            # Calculate coherence between thesis and synthesis for each instance
            coherences = []
            for inst in mamv_result["instances"]:
                thesis_text = inst["thesis"]["answer"]
                synthesis_text = inst["synthesis"]["answer"]
                coh = coherence_ts(thesis_text, synthesis_text)
                coherences.append(coh)

            avg_coherence = sum(coherences) / len(coherences) if coherences else 0.0

            # Aggregate token usage from all instances
            total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            for inst in mamv_result["instances"]:
                for stage in ["thesis", "antithesis", "synthesis"]:
                    usage = inst[stage]["meta"]["usage"]
                    total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                    total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
                    total_usage["total_tokens"] += usage.get("total_tokens", 0)

            # Calculate cost
            problem_cost = estimate_cost(total_usage["total_tokens"])
            total_cost += problem_cost

            # Create result record
            result = {
                "run_id": run_id,
                "problem_id": problem_id,
                "dataset": "gsm8k",
                "phase": "tas_mamv",
                "model": MODEL,
                "question": problem["question"],
                "true_answer": problem["answer"],
                "predicted_answer_raw": final_answer,
                "is_correct": is_correct,
                "decision_method": mamv_result["decision_method"],
                "vote_counts": mamv_result["mamv_result"]["vote_counts"],
                "individual_votes": [
                    v["extracted_answer"] for v in mamv_result["mamv_result"]["votes"]
                ],
                "coherence_avg": avg_coherence,
                "coherences": coherences,
                "mamv_usage": total_usage,
                "cost_usd": problem_cost,
                "elapsed_seconds": time.time() - problem_start,
            }
            results.append(result)

            # Status
            status = "✓" if is_correct else "✗"
            print(
                f"  {status} Answer: {final_answer} | "
                f"Method: {mamv_result['decision_method']} | "
                f"Coherence: {avg_coherence:.3f}"
            )
            print(f"  Tokens: {total_usage['total_tokens']:,} | Cost: ${problem_cost:.4f}")
            print(f"  Cumulative: ${total_cost:.2f} / ${MAX_COST_USD:.2f}")

        except Exception as e:
            print(f"  ❌ ERROR: {str(e)[:100]}")
            result = {
                "run_id": run_id,
                "problem_id": problem_id,
                "dataset": "gsm8k",
                "phase": "tas_mamv",
                "model": MODEL,
                "question": problem["question"],
                "true_answer": problem["answer"],
                "error": str(e),
                "is_correct": False,
            }
            results.append(result)

        # Budget check
        if total_cost >= MAX_COST_USD:
            print(f"\n⚠️  Budget limit reached (${total_cost:.2f}). Stopping at {i + 1} problems.")
            break

        # Alert at 90%
        if total_cost >= MAX_COST_USD * ALERT_THRESHOLD_PCT and i < len(problems) - 1:
            print(f"\n⚠️  Alert: {ALERT_THRESHOLD_PCT * 100:.0f}% of budget used")

    # Summary
    elapsed_time = time.time() - start_time
    print("\n" + "=" * 80)
    print("📊 EXECUTION SUMMARY")
    print("=" * 80)

    completed = len([r for r in results if "error" not in r])
    correct = len([r for r in results if r.get("is_correct", False)])
    accuracy = correct / completed if completed > 0 else 0.0

    print(f"Total problems processed: {len(results)}")
    print(f"Successfully completed:   {completed}")
    print(f"Errors:                   {len(results) - completed}")
    print(f"Correct:                  {correct}/{completed}")
    print(f"Accuracy:                 {accuracy:.3f} ({accuracy * 100:.1f}%)")
    print(f"Total cost:               ${total_cost:.2f} USD")
    print(f"Cost per problem:         ${total_cost / len(results):.4f} USD")
    print(f"Elapsed time:             {elapsed_time / 60:.1f} minutes")

    # Decision method breakdown
    decision_methods = {}
    for r in results:
        method = r.get("decision_method", "unknown")
        decision_methods[method] = decision_methods.get(method, 0) + 1

    print("\nDecision method breakdown:")
    for method, count in sorted(decision_methods.items(), key=lambda x: -x[1]):
        pct = count / len(results) * 100
        print(f"  {method:30s}: {count:3d} ({pct:5.1f}%)")

    # Save results to JSON (optional, but keep for now)
    output_dir_json = Path("analytics/mamv")  # Keep JSON in its original folder
    output_dir_json.mkdir(parents=True, exist_ok=True)

    output_file = output_dir_json / f"mamv_results_{run_id}.json"
    with open(output_file, "w") as f:
        json.dump(
            {
                "run_id": run_id,
                "config": {
                    "model": MODEL,
                    "n_problems": N_PROBLEMS,
                    "seed": SEED,
                    "max_cost_usd": MAX_COST_USD,
                },
                "summary": {
                    "total_problems": len(results),
                    "completed": completed,
                    "correct": correct,
                    "accuracy": accuracy,
                    "total_cost_usd": total_cost,
                    "elapsed_seconds": elapsed_time,
                },
                "results": results,
            },
            f,
            indent=2,
        )

    print(f"\n💾 JSON results saved to: {output_file}")

    # Convert to Parquet for analytics
    print("\n📊 Creating Parquet file...")
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq

        # Flatten results for Parquet
        flat_results = []
        for r in results:
            flat_r = {
                "run_id": r["run_id"],
                "problem_id": r["problem_id"],
                "dataset": r["dataset"],
                "phase": r["phase"],
                "model": r["model"],
                "question": r["question"],
                "true_answer": r["true_answer"],
                "predicted_answer_raw": r.get("predicted_answer_raw", ""),
                "is_correct": r["is_correct"],
                "decision_method": r.get("decision_method", ""),
                "coherence_avg": r.get("coherence_avg", 0.0),
                "total_tokens": r.get("mamv_usage", {}).get("total_tokens", 0),
                "cost_usd": r.get("cost_usd", 0.0),
                "elapsed_seconds": r.get("elapsed_seconds", 0.0),
                "error": r.get("error", ""),
            }
            flat_results.append(flat_r)

        table = pa.Table.from_pylist(flat_results)
        # Change output_dir to analytics/parquet for Parquet files
        parquet_output_dir = Path("analytics/parquet")
        parquet_output_dir.mkdir(parents=True, exist_ok=True)
        parquet_file = parquet_output_dir / f"mamv_results_{run_id}.parquet"
        pq.write_table(table, parquet_file)
        print(f"✅ Parquet saved to: {parquet_file}")
    except Exception as e:
        print(f"⚠️  Could not create Parquet: {e}")

    print("\n" + "=" * 80)
    print("✅ S2-06 execution completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
