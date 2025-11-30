"""S2-05: Ejecutar T-A-S (k=1) en 200 problemas con GPT-3.5-turbo.

Este script ejecuta el flow T-A-S en exactamente los mismos 200 problemas
del baseline S1 (seed=42) usando GPT-3.5-turbo para reducir costos.

Costo estimado: ~$2.42 USD para 200 problemas (vs $62 con GPT-4)
Ahorro: 96% más barato que GPT-4

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

# Verificar que la API key está configurada
if not os.getenv("OPENAI_API_KEY"):
    print("❌ Error: OPENAI_API_KEY not found in environment variables")
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
MAX_COST_USD = 5.0  # Budget para la ejecución
RUN_ID = f"s2_tas_gpt35_k1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Importar flow T-A-S
from flows.tas import TASFlowConfig, run_tas_k1  # noqa: E402


def load_problem_ids() -> List[str]:
    """Carga los IDs de problemas desde el archivo versionado de S2-04."""
    print(f"\n📋 Loading problem IDs from {IDS_FILE}...")

    with open(IDS_FILE, "r") as f:
        data = json.load(f)

    # El archivo usa "ids" no "problem_ids"
    problem_ids = data["ids"]
    seed = data["seed"]
    content_hash = data["content_hash"]

    print(f"✅ Loaded {len(problem_ids)} problem IDs")
    print(f"   Seed: {seed}")
    print(f"   Content hash: {content_hash}\n")

    return problem_ids


def load_problems_by_questions(questions: List[str]) -> List[Dict]:
    """
    Carga los problemas completos de GSM8K que coinciden con las preguntas dadas.

    Args:
        questions: Lista de textos de preguntas (no usadas, cargamos por seed)

    Returns:
        Lista de diccionarios con problem_id, question, answer
    """
    print("📚 Loading full problems from GSM8K dataset...")

    # Cargar todo GSM8K test split
    import random

    from datasets import load_dataset

    dataset = load_dataset("openai/gsm8k", "main", split="test")

    # Usar mismo seed que en S1 para obtener los mismos 200 problemas
    random.seed(42)
    indices = list(range(len(dataset)))
    random.shuffle(indices)
    selected_indices = sorted(indices[:200])  # Tomar primeros 200 después del shuffle

    # Cargar problemas seleccionados
    problems = []
    for idx in selected_indices:
        item = dataset[idx]
        problems.append(
            {
                "problem_id": f"gsm8k-{idx:04d}",
                "question": item["question"],
                "answer": item["answer"],
            }
        )

    print(f"✅ Loaded {len(problems)} complete problems\n")
    return problems


def run_tas_on_problem(problem: Dict, run_id: str) -> Dict:
    """
    Ejecuta T-A-S en un problema individual y retorna resultado estructurado.

    Args:
        problem: Dict con problem_id, question, answer
        run_id: Identificador único del run

    Returns:
        Dict con resultados, métricas y metadata
    """
    # Configurar T-A-S
    config = TASFlowConfig(
        run_id=run_id,
        dataset_name="gsm8k",
        seed=42,
    )

    # Ejecutar T-A-S
    result = run_tas_k1(problem, config)

    # Extraer resultados
    thesis = result["thesis"]
    antithesis = result["antithesis"]
    synthesis = result["synthesis"]

    # Extraer respuestas
    thesis_text = thesis.get("answer", "")
    synthesis_text = synthesis.get("answer", "")

    # Extraer answer numérica del synthesis
    final_answer = synthesis_text
    expected_answer = problem["answer"]

    # Evaluar corrección
    is_correct = evaluate_exact_match(final_answer, expected_answer)

    # Calcular coherencia thesis-synthesis
    coherence_score = None
    try:
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
    # GPT-3.5-turbo: $0.0015/1k prompt, $0.002/1k completion
    cost = (total_usage["prompt_tokens"] / 1000) * 0.0015 + (
        total_usage["completion_tokens"] / 1000
    ) * 0.002

    return {
        "run_id": run_id,
        "problem_id": problem["problem_id"],
        "dataset": "gsm8k",
        "phase": "tas_k1",  # Requerido por parquet_utils
        "model": "gpt-3.5-turbo",  # Requerido por parquet_utils
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
    """Ejecuta S2-05: T-A-S en 200 problemas con GPT-3.5-turbo."""
    print("=" * 70)
    print(" S2-05: Ejecutar T-A-S (k=1) en 200 con GPT-3.5-turbo")
    print("=" * 70)
    print(f"\nRun ID: {RUN_ID}")
    print(f"Budget: ${MAX_COST_USD:.2f}")
    print("Model: gpt-3.5-turbo (96% más barato que GPT-4)")
    print("Target: 200 problems from S2-04 (seed=42)")
    print("Estimated cost: ~$2.42 USD\n")

    # 1. Cargar IDs versionados
    problem_questions = load_problem_ids()

    # 2. Cargar problemas completos
    problems = load_problems_by_questions(problem_questions)

    if len(problems) != 200:
        print(f"\n❌ Error: Expected 200 problems, got {len(problems)}")
        sys.exit(1)

    # 3. Cargar baseline stats si existen
    baseline_stats = None
    if Path(BASELINE_PARQUET).exists():
        baseline_stats = load_baseline_stats_from_parquet(BASELINE_PARQUET)
        print("📊 Baseline stats loaded:")
        print(f"   Tokens: {baseline_stats.get('total_tokens', 0):,}")
        print(f"   Cost: ${baseline_stats.get('total_cost_usd', 0):.2f}\n")

    # 4. Ejecutar T-A-S en cada problema
    results = []
    print(f"🚀 Starting T-A-S execution on {len(problems)} problems...")
    print("   (Estimated time: 2-3 hours)\n")

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

    # 7. Budget status final
    final_status = calculate_budget_status(
        run_id=RUN_ID,
        processed_results=valid_results,
        total_items=len(problems),
        budget_limit_usd=MAX_COST_USD,
        baseline_stats=baseline_stats,
    )

    print(f"\n{format_budget_summary(final_status)}")

    # 8. Guardar a Parquet
    if valid_results:
        print("\n💾 Saving results to Parquet...")
        output_dir = Path("analytics/parquet")
        output_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = output_dir / "s2_05_tas_gpt35_200.parquet"

        try:
            create_tas_parquet(valid_results, str(parquet_path))
            print(f"✅ Parquet saved: {parquet_path}")
        except Exception as e:
            print(f"❌ Error saving Parquet: {e}")

    print(f"\n{'=' * 70}")
    print("✅ S2-05 COMPLETE")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
