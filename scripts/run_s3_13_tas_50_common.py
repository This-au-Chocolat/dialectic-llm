'S3-13: Ejecutar T-A-S (k=1) en 50 problemas comunes con DeepSeek.'

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Verificar que la API key está configurada (DeepSeek o OpenAI)
if not os.getenv("DEEPSEEK_API_KEY") and not os.getenv("OPENAI_API_KEY"):
    print("❌ Error: DEEPSEEK_API_KEY or OPENAI_API_KEY not found in environment variables")
    print("   Please set it in your .env file")
    sys.exit(1)

# Add src to path
# This is a temporary solution for the directory structure.
# In a real-world scenario, this would be handled by a proper package installation.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.utils.budget_monitor import (
    calculate_budget_status,
    format_budget_alert,
    format_budget_summary,
    load_baseline_stats_from_parquet,
    should_alert_budget,
)
from src.utils.evaluation import coherence_ts, evaluate_exact_match
from src.utils.parquet_utils import create_tas_parquet

# Configuración
IDS_FILE = "data/processed/common_problem_ids.txt"  # <-- MODIFIED: Use the common IDs file
BASELINE_PARQUET = "analytics/parquet/baseline_baseline_20251127_152753_b9f53dc0.parquet"
MAX_COST_USD = 3.0  # Budget para 50 problemas con DeepSeek
MODEL = "deepseek-chat"
RUN_ID = f"s3_tas_common_ids_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def load_problems_from_common_ids() -> List[Dict]:
    """
    Carga los problemas completos de GSM8K usando una lista de problem_id.
    """
    print(f"\n📚 Loading problems from GSM8K dataset based on IDs from {IDS_FILE}...")

    # 1. Cargar la lista de problem_id
    with open(IDS_FILE, "r") as f:
        content = f.read()
        target_ids = {id_str for id_str in content.split('\\n') if id_str.strip()}
    
    print(f"   - Found {len(target_ids)} target problem IDs.")

    # 2. Cargar todo el dataset GSM8K
    from datasets import load_dataset
    dataset = load_dataset("gsm8k", "main", split="train")

    # 3. Recuperar problemas que coinciden con los IDs
    problems = []
    for idx, item in enumerate(dataset):
        # El formato de ID en los archivos parquet compatibles es 'gsm8k_xxxx'
        # Tenemos que asegurarnos de que el ID que generamos aquí coincida.
        # Basado en la inspección de los archivos, el formato es `gsm8k_` + 4 digitos con padding.
        current_id = f"gsm8k_{idx:04d}"
        
        if current_id in target_ids:
            problems.append({
                "question": item["question"],
                "answer": item["answer"],
                "problem_id": current_id,
            })

    if len(problems) != len(target_ids):
        print(f"⚠️  Warning: Could not find all problems. Found {len(problems)} out of {len(target_ids)}.")

    print(f"✅ Loaded {len(problems)} complete problems.")
    return problems


def run_tas_on_problem(problem: Dict, run_id: str) -> Dict:
    """
    Ejecuta T-A-S en un problema individual.
    """
    from src.flows.tas import TASFlowConfig, run_tas_k1

    config = TASFlowConfig(
        run_id=run_id,
        seed=42,
        dataset_name="gsm8k",
        model_name=MODEL,
    )

    tas_result = run_tas_k1(problem, config)

    thesis = tas_result["thesis"]
    antithesis = tas_result["antithesis"]
    synthesis = tas_result["synthesis"]
    final_answer = synthesis["answer"]
    expected_answer = problem["answer"].split("#### ")[-1].strip()
    is_correct = evaluate_exact_match(final_answer, expected_answer)

    try:
        thesis_text = thesis["answer"]
        synthesis_text = synthesis["answer"]
        coherence_score = coherence_ts(thesis_text, synthesis_text)
    except Exception as e:
        print(f"  ⚠️  Could not calculate coherence: {e}")
        coherence_score = None

    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for stage in [thesis, antithesis, synthesis]:
        if "meta" in stage and "usage" in stage["meta"]:
            usage = stage["meta"]["usage"]
            total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
            total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
            total_usage["total_tokens"] += usage.get("total_tokens", 0)

    cost = (total_usage["prompt_tokens"] / 1000) * 0.00028 + (
        total_usage["completion_tokens"] / 1000
    ) * 0.00042

    return {
        "run_id": run_id,
        "problem_id": problem["problem_id"],
        "dataset": "gsm8k",
        "phase": "tas_k1",
        "model": MODEL,
        "question": problem["question"],
        "true_answer": expected_answer,
        "expected_answer": expected_answer,
        "predicted_answer_raw": final_answer,
        "final_answer": final_answer,
        "is_correct": is_correct,
        "thesis_text": thesis_text,
        "antithesis_text": antithesis["critique"],
        "synthesis_text": synthesis_text,
        "coherence_score": coherence_score,
        "tas_usage": total_usage,
        "usage": total_usage,
        "estimated_cost_usd": cost,
        "timestamp": datetime.now().isoformat(),
    }


def main():
    """Ejecuta T-A-S en 50 problemas comunes con DeepSeek."""
    print("=" * 70)
    print(" S3-13: Ejecutar T-A-S (k=1) en 50 problemas comunes")
    print("=" * 70)
    print(f"\nRun ID: {RUN_ID}")
    print(f"Model: {MODEL}")
    print(f"Budget: ${MAX_COST_USD:.2f}")
    print(f"Target: 50 problems from {IDS_FILE}")

    problems = load_problems_from_common_ids()

    if not problems:
        print("\n❌ Error: No problems loaded. Aborting.")
        sys.exit(1)

    baseline_stats = None
    if Path(BASELINE_PARQUET).exists():
        baseline_stats = load_baseline_stats_from_parquet(BASELINE_PARQUET)
        print("\n📊 Baseline stats loaded:")
        print(f"   Tokens: {baseline_stats.get('total_tokens', 0):,}")
        print(f"   Cost: ${baseline_stats.get('total_cost_usd', 0):.2f}")

    results = []
    print(f"\n🚀 Starting T-A-S execution on {len(problems)} problems...")
    print("   (This will take approximately 2-3 hours)\n")

    for i, problem in enumerate(problems, 1):
        print(f"\n[{i}/{len(problems)}] Processing {problem['problem_id']}...")
        try:
            result = run_tas_on_problem(problem, RUN_ID)
            results.append(result)

            status_icon = "✅" if result["is_correct"] else "❌"
            print(f"  {status_icon} Answer: {result['final_answer'][:50]}...")
            print(f"  📊 Tokens: {result['usage']['total_tokens']:,} | Cost: ${result['estimated_cost_usd']:.4f}")
            if result['coherence_score'] is not None:
                print(f"  🔗 Coherence: {result['coherence_score']:.3f}")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                "run_id": RUN_ID, "problem_id": problem["problem_id"],
                "question": problem["question"], "error": str(e),
                "timestamp": datetime.now().isoformat(),
            })

        if i % 10 == 0 and results:
            status = calculate_budget_status(
                run_id=RUN_ID, processed_results=results, total_items=len(problems),
                budget_limit_usd=MAX_COST_USD, baseline_stats=baseline_stats,
            )
            print(f"\n{'─' * 70}\n💰 Budget Check ({i}/{len(problems)} problems)\n{'─' * 70}")
            print(f"Current cost: ${status.total_cost_usd:.2f} | Budget used: {status.budget_used_pct:.1f}%")
            print(f"Projected total: ${status.projected_total_cost:.2f}")
            if status.cost_vs_baseline_ratio:
                print(f"vs Baseline: {status.cost_vs_baseline_ratio:.2f}×")
            if status.items_over_cap:
                print(f"⚠️  Items over 8k cap: {len(status.items_over_cap)}")
            if should_alert_budget(status):
                print(f"\n{format_budget_alert(status)}")
                if status.projected_total_cost > MAX_COST_USD * 1.5:
                    print("\n❌ Projected cost exceeds 150% of budget! Stopping.")
                    break
    
    print(f"\n{'=' * 70}\n EXECUTION COMPLETE\n{'=' * 70}")

    valid_results = [r for r in results if "error" not in r]
    correct_count = sum(1 for r in valid_results if r["is_correct"])
    accuracy = (correct_count / len(valid_results)) * 100 if valid_results else 0
    total_tokens = sum(r["usage"]["total_tokens"] for r in valid_results)
    total_cost = sum(r["estimated_cost_usd"] for r in valid_results)
    coherence_scores = [r["coherence_score"] for r in valid_results if r["coherence_score"] is not None]
    avg_coherence = sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0

    print("\n📊 Results:")
    print(f"   Accuracy: {accuracy:.2f}% ({correct_count}/{len(valid_results)})")
    print(f"   Total tokens: {total_tokens:,} | Total cost: ${total_cost:.2f}")
    print(f"   Avg coherence: {avg_coherence:.3f}")

    final_status = calculate_budget_status(
        run_id=RUN_ID, processed_results=valid_results, total_items=len(problems),
        budget_limit_usd=MAX_COST_USD, baseline_stats=baseline_stats,
    )
    print(f"\n{format_budget_summary(final_status)}")

    print("\n💾 Saving results to Parquet...")
    output_dir = Path("analytics/parquet")
    output_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = create_tas_parquet(valid_results, RUN_ID)
    print(f"✅ Results saved to: {parquet_path}")

    summary = {
        "run_id": RUN_ID, "accuracy": accuracy, "total_tokens": total_tokens,
        "total_cost_usd": total_cost, "avg_coherence": avg_coherence,
    }
    summary_path = output_dir / f"summary_{RUN_ID}.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Summary saved to: {summary_path}")

    print(f"\n{'=' * 70}\n✅ S3-13 (TAS Common) COMPLETE\n{'=' * 70}\n")


if __name__ == "__main__":
    main()
