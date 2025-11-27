"""S2-05: Ejecutar T-A-S (k=1) en 50 problemas con DeepSeek.

Este script ejecuta el flow T-A-S en exactamente los mismos 50 problemas
del baseline S1 (seed=42) para permitir comparaciones emparejadas 1-a-1.

Features:
- Carga de IDs versionados desde S2-04
- Budget monitoring con S2-09 (≤8k tokens/ítem, alertas al 90%)
- Retry logic con S2-01 (exponential backoff)
- Cálculo de coherencia con S2-07/S2-08
- Logging sanitizado (CoT solo en logs_local/)
- Generación de Parquet para analytics
"""

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
sys.path.append(str(Path(__file__).parent / "src"))

from utils.budget_monitor import (  # noqa: E402
    calculate_budget_status,
    format_budget_alert,
    format_budget_summary,
    load_baseline_stats_from_parquet,
    should_alert_budget,
)
from utils.evaluation import coherence_ts, evaluate_exact_match  # noqa: E402
from utils.parquet_utils import create_tas_parquet  # noqa: E402

# Configuración
IDS_FILE = "data/processed/gsm8k_s1_200_seed42_ids.json"
BASELINE_PARQUET = "analytics/parquet/s1_baseline_200.parquet"  # Si existe
MAX_COST_USD = 1.0  # Budget para 50 problemas con DeepSeek
N_PROBLEMS = 50  # Reducido a 50 problemas
MODEL = "deepseek-chat"  # Usar DeepSeek
RUN_ID = f"s2_tas_deepseek_k1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def load_problem_ids() -> List[str]:
    """Carga los IDs de problemas versionados desde S2-04."""
    print(f"\n📋 Loading problem IDs from {IDS_FILE}...")

    with open(IDS_FILE, "r") as f:
        data = json.load(f)

    ids = data["ids"]
    print(f"✅ Loaded {len(ids)} problem IDs")
    print(f"   Seed: {data['seed']}")
    print(f"   Content hash: {data['content_hash']}")

    return ids


def load_problems_by_questions(questions: List[str]) -> List[Dict]:
    """
    Carga los problemas completos desde GSM8K usando las preguntas.

    Args:
        questions: Lista de preguntas (usadas como IDs en S2-04)

    Returns:
        Lista de diccionarios con question, answer, problem_id
    """
    print("\n📚 Loading full problems from GSM8K dataset...")

    # Cargar todo el dataset GSM8K
    from datasets import load_dataset

    dataset = load_dataset("gsm8k", "main", split="train")

    # Crear diccionario de búsqueda
    question_to_problem = {}
    for idx, item in enumerate(dataset):
        question = item["question"]
        answer = item["answer"]
        question_to_problem[question] = {
            "question": question,
            "answer": answer,
            "problem_id": f"gsm8k-{idx:04d}",
        }

    # Recuperar problemas en el orden correcto
    problems = []
    for question in questions:
        if question in question_to_problem:
            problems.append(question_to_problem[question])
        else:
            print("⚠️  Warning: Question not found in dataset")

    print(f"✅ Loaded {len(problems)} complete problems")
    return problems


def run_tas_on_problem(problem: Dict, run_id: str) -> Dict:
    """
    Ejecuta T-A-S en un problema individual.

    Args:
        problem: Diccionario con question, answer, problem_id
        run_id: ID único del run

    Returns:
        Resultado con todas las etapas y métricas
    """
    from flows.tas import TASFlowConfig, run_tas_k1

    # Configurar flow
    config = TASFlowConfig(
        run_id=run_id,
        seed=42,
        dataset_name="gsm8k",
        model_name="gpt-4",
    )

    # Ejecutar T-A-S
    tas_result = run_tas_k1(problem, config)

    # Extraer respuestas
    thesis = tas_result["thesis"]
    antithesis = tas_result["antithesis"]
    synthesis = tas_result["synthesis"]

    # Obtener respuesta final
    final_answer = synthesis["answer"]

    # Evaluar corrección
    expected_answer = problem["answer"].split("#### ")[-1].strip()
    is_correct = evaluate_exact_match(final_answer, expected_answer)

    # Calcular coherencia thesis→synthesis
    try:
        thesis_text = thesis["answer"]
        synthesis_text = synthesis["answer"]
        coherence_score = coherence_ts(thesis_text, synthesis_text)
    except Exception as e:
        print(f"  ⚠️  Could not calculate coherence: {e}")
        coherence_score = None

    # Agregar usage stats
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    for stage in [thesis, antithesis, synthesis]:
        if "meta" in stage and "usage" in stage["meta"]:
            usage = stage["meta"]["usage"]
            total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
            total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
            total_usage["total_tokens"] += usage.get("total_tokens", 0)

    # Estimar costo
    # DeepSeek: $0.00028/1k prompt, $0.00042/1k completion
    cost = (total_usage["prompt_tokens"] / 1000) * 0.00028 + (
        total_usage["completion_tokens"] / 1000
    ) * 0.00042

    return {
        "run_id": run_id,
        "problem_id": problem["problem_id"],
        "dataset": "gsm8k",
        "phase": "tas_k1",  # Requerido por parquet_utils
        "model": MODEL,  # deepseek-chat
        "question": problem["question"],
        "true_answer": expected_answer,  # Nombre esperado por parquet_utils
        "expected_answer": expected_answer,  # Mantener para compatibilidad
        "predicted_answer_raw": final_answer,  # Nombre esperado por parquet_utils
        "final_answer": final_answer,  # Mantener para compatibilidad
        "is_correct": is_correct,
        "thesis_text": thesis_text,
        "antithesis_text": antithesis["critique"],
        "synthesis_text": synthesis_text,
        "coherence_score": coherence_score,
        "tas_usage": total_usage,  # Nombre esperado por parquet_utils
        "usage": total_usage,  # Mantener para compatibilidad
        "estimated_cost_usd": cost,
        "timestamp": datetime.now().isoformat(),
    }


def main():
    """Ejecuta S2-05: T-A-S en 50 problemas con DeepSeek."""
    print("=" * 70)
    print(" S2-05: Ejecutar T-A-S (k=1) en 50 con DeepSeek")
    print("=" * 70)
    print(f"\nRun ID: {RUN_ID}")
    print(f"Model: {MODEL}")
    print(f"Budget: ${MAX_COST_USD:.2f}")
    print(f"Target: {N_PROBLEMS} problems from S2-04 (seed=42)")

    # 1. Cargar IDs versionados
    problem_questions = load_problem_ids()

    # 2. Cargar problemas completos (tomar solo los primeros N_PROBLEMS)
    problems = load_problems_by_questions(problem_questions[:N_PROBLEMS])

    if len(problems) != N_PROBLEMS:
        print(f"\n❌ Error: Expected {N_PROBLEMS} problems, got {len(problems)}")
        sys.exit(1)

    # 3. Cargar baseline stats si existen
    baseline_stats = None
    if Path(BASELINE_PARQUET).exists():
        baseline_stats = load_baseline_stats_from_parquet(BASELINE_PARQUET)
        print("\n📊 Baseline stats loaded:")
        print(f"   Tokens: {baseline_stats.get('total_tokens', 0):,}")
        print(f"   Cost: ${baseline_stats.get('total_cost_usd', 0):.2f}")

    # 4. Ejecutar T-A-S en cada problema
    results = []
    print(f"\n🚀 Starting T-A-S execution on {len(problems)} problems...")
    print("   (This will take approximately 2-3 hours)\n")

    for i, problem in enumerate(problems, 1):
        print(f"\n[{i}/{len(problems)}] Processing {problem['problem_id']}...")

        try:
            result = run_tas_on_problem(problem, RUN_ID)
            results.append(result)

            # Mostrar progreso
            status = "✅" if result["is_correct"] else "❌"
            tokens = result["usage"]["total_tokens"]
            cost = result["estimated_cost_usd"]
            coherence = result["coherence_score"]

            print(f"  {status} Answer: {result['final_answer'][:50]}...")
            print(f"  📊 Tokens: {tokens:,} | Cost: ${cost:.4f}")
            if coherence is not None:
                print(f"  🔗 Coherence: {coherence:.3f}")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            # Log error but continue
            results.append(
                {
                    "run_id": RUN_ID,
                    "problem_id": problem["problem_id"],
                    "question": problem["question"],
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # 5. Budget monitoring cada 10 problemas
        if i % 10 == 0 and results:
            status = calculate_budget_status(
                run_id=RUN_ID,
                processed_results=results,
                total_items=len(problems),
                budget_limit_usd=MAX_COST_USD,
                baseline_stats=baseline_stats,
            )

            print(f"\n{'─' * 70}")
            print(f"💰 Budget Check ({i}/{len(problems)} problems)")
            print(f"{'─' * 70}")
            print(f"Current cost: ${status.total_cost_usd:.2f}")
            print(f"Budget used: {status.budget_used_pct:.1f}%")
            print(f"Projected total: ${status.projected_total_cost:.2f}")

            if status.cost_vs_baseline_ratio:
                print(f"vs Baseline: {status.cost_vs_baseline_ratio:.2f}×")

            if status.items_over_cap:
                print(f"⚠️  Items over 8k cap: {len(status.items_over_cap)}")

            # Alertar si necesario
            if should_alert_budget(status):
                print(f"\n{format_budget_alert(status)}")

                # Opcionalmente detener si se excede mucho el presupuesto
                if status.projected_total_cost > MAX_COST_USD * 1.5:
                    print("\n❌ Projected cost exceeds 150% of budget!")
                    print("   Stopping execution to avoid excessive costs.")
                    break

    # 6. Resumen final
    print(f"\n{'=' * 70}")
    print(" EXECUTION COMPLETE")
    print(f"{'=' * 70}")

    # Calcular métricas finales
    valid_results = [r for r in results if "error" not in r]
    correct_count = sum(1 for r in valid_results if r["is_correct"])
    accuracy = (correct_count / len(valid_results)) * 100 if valid_results else 0

    total_tokens = sum(r["usage"]["total_tokens"] for r in valid_results)
    total_cost = sum(r["estimated_cost_usd"] for r in valid_results)

    coherence_scores = [
        r["coherence_score"] for r in valid_results if r["coherence_score"] is not None
    ]
    avg_coherence = sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0

    print("\n📊 Results:")
    print(f"   Total problems: {len(results)}")
    print(f"   Valid results: {len(valid_results)}")
    print(f"   Correct: {correct_count}")
    print(f"   Accuracy: {accuracy:.2f}%")
    print(f"   Total tokens: {total_tokens:,}")
    print(f"   Total cost: ${total_cost:.2f}")
    print(f"   Avg coherence: {avg_coherence:.3f}")

    # 7. Budget final
    final_status = calculate_budget_status(
        run_id=RUN_ID,
        processed_results=valid_results,
        total_items=len(problems),
        budget_limit_usd=MAX_COST_USD,
        baseline_stats=baseline_stats,
    )

    print(f"\n{format_budget_summary(final_status)}")

    # 8. Guardar Parquet
    print("\n💾 Saving results to Parquet...")
    output_dir = Path("analytics/parquet")
    output_dir.mkdir(parents=True, exist_ok=True)

    # create_tas_parquet construye el path internamente, solo necesita run_id
    parquet_path = create_tas_parquet(valid_results, RUN_ID)

    print(f"✅ Results saved to: {parquet_path}")

    # 9. Guardar resumen JSON
    summary = {
        "run_id": RUN_ID,
        "timestamp": datetime.now().isoformat(),
        "total_problems": len(results),
        "valid_results": len(valid_results),
        "correct": correct_count,
        "accuracy": accuracy,
        "total_tokens": total_tokens,
        "total_cost_usd": total_cost,
        "avg_coherence": avg_coherence,
        "budget_status": {
            "budget_limit": MAX_COST_USD,
            "budget_used_pct": final_status.budget_used_pct,
            "projected_total": final_status.projected_total_cost,
            "items_over_cap": len(final_status.items_over_cap),
        },
    }

    summary_path = output_dir / f"summary_{RUN_ID}.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"✅ Summary saved to: {summary_path}")

    print(f"\n{'=' * 70}")
    print("✅ S2-05 COMPLETE")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
