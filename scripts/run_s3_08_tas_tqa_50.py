"""S3-08: Ejecutar T-A-S (k=1) en TruthfulQA 50 problemas.

Este script ejecuta el flow T-A-S (Tesis-Antítesis-Síntesis) en 50 problemas
de TruthfulQA para comparar contra el baseline.

Features:
- Usa los mismos 50 problemas que S3-07 (seed=42)
- T-A-S con DeepSeek-chat (3 etapas por problema)
- Budget monitoring (≤8k tokens/ítem por etapa, ~24k total)
- Retry logic con exponential backoff
- Logging sanitizado (sin CoT en outputs públicos)
- Generación de Parquet para analytics
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Verificar API key
if not os.getenv("DEEPSEEK_API_KEY") and not os.getenv("OPENAI_API_KEY"):
    print("❌ Error: DEEPSEEK_API_KEY or OPENAI_API_KEY not found")
    sys.exit(1)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dialectic_llm.data import load_truthfulqa_problems, normalize_truthfulqa_answer
from flows.tas import TASFlowConfig, run_tas_k1

# Configuración
N_PROBLEMS = 50
SEED = 42  # Mismo seed que S3-07
MODEL = "deepseek-chat"
MAX_COST_USD = 15.0  # Budget para T-A-S (3× baseline)
RUN_ID = f"s3_tas_tqa_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def evaluate_truthfulqa_answer(predicted: str, problem: Dict) -> bool:
    """
    Evalúa si la respuesta predicha es correcta para TruthfulQA.

    Args:
        predicted: Respuesta predicha normalizada
        problem: Diccionario del problema con correct_answers

    Returns:
        True si la respuesta es correcta
    """
    # TruthfulQA acepta múltiples respuestas correctas
    correct_answers = problem.get("correct_answers", [])

    # Normalizar predicción
    pred_normalized = normalize_truthfulqa_answer(predicted)

    # Comparación exacta con cualquier respuesta correcta
    return pred_normalized in correct_answers


def run_tas_on_tqa_problem(problem: Dict, run_id: str) -> Dict:
    """
    Ejecuta T-A-S en un problema individual de TruthfulQA.

    Args:
        problem: Diccionario con question, correct_answers, etc.
        run_id: ID único del run

    Returns:
        Resultado con todas las etapas y métricas
    """
    # Configurar flow T-A-S
    config = TASFlowConfig(
        run_id=run_id,
        seed=SEED,
        dataset_name="truthfulqa",
        model_name=MODEL,
    )

    # Adaptar problema a formato esperado por run_tas_k1
    # El flow espera 'answer' pero TQA tiene 'best_answer'
    adapted_problem = {
        "problem_id": problem["problem_id"],
        "question": problem["question"],
        "answer": problem["best_answer"],  # Para logging interno
    }

    # Ejecutar T-A-S (esto hace 3 llamadas al LLM)
    try:
        tas_result = run_tas_k1(adapted_problem, config)
    except Exception as e:
        print(f"  ❌ Error en T-A-S: {e}")
        return {
            "run_id": run_id,
            "problem_id": problem["problem_id"],
            "dataset": "truthfulqa",
            "phase": "tas_k1",
            "model": MODEL,
            "question": problem["question"],
            "true_answer": problem["best_answer"],
            "predicted_answer_raw": "",
            "is_correct": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }

    # Extraer resultados de cada etapa
    thesis = tas_result.get("thesis", {})
    antithesis = tas_result.get("antithesis", {})
    synthesis = tas_result.get("synthesis", {})

    # La respuesta final viene de la síntesis
    final_answer = synthesis.get("answer", "")

    # Evaluar corrección usando la evaluación de TQA
    is_correct = evaluate_truthfulqa_answer(final_answer, problem)

    # Calcular usage total (suma de las 3 etapas)
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    for stage in [thesis, antithesis, synthesis]:
        if "meta" in stage and "usage" in stage["meta"]:
            usage = stage["meta"]["usage"]
            total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
            total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
            total_usage["total_tokens"] += usage.get("total_tokens", 0)

    # Calcular costo
    # DeepSeek: $0.00028/1k prompt, $0.00042/1k completion
    cost = (total_usage["prompt_tokens"] / 1000) * 0.00028 + (
        total_usage["completion_tokens"] / 1000
    ) * 0.00042

    # Construir resultado
    result = {
        "run_id": run_id,
        "problem_id": problem["problem_id"],
        "dataset": "truthfulqa",
        "phase": "tas_k1",
        "model": MODEL,
        "question": problem["question"],
        "true_answer": problem["best_answer"],
        "predicted_answer_raw": final_answer,
        "is_correct": is_correct,
        "correct_answers": problem.get("correct_answers", []),
        "incorrect_answers": problem.get("incorrect_answers", []),
        # Etapas T-A-S
        "thesis_text": thesis.get("answer", ""),
        "antithesis_text": antithesis.get("critique", ""),
        "synthesis_text": synthesis.get("answer", ""),
        # Metadata
        "tas_usage": total_usage,
        "estimated_cost_usd": cost,
        "timestamp": datetime.now().isoformat(),
    }

    return result


def main():
    """Ejecuta S3-08: T-A-S en TruthfulQA 50."""
    print("=" * 70)
    print(" S3-08: Ejecutar T-A-S (k=1) en TruthfulQA 50")
    print("=" * 70)
    print(f"\nRun ID: {RUN_ID}")
    print(f"Model: {MODEL}")
    print(f"Budget: ${MAX_COST_USD:.2f}")
    print(f"Target: {N_PROBLEMS} problems from TruthfulQA (seed={SEED})")
    print("\n⚠️  NOTE: T-A-S hace 3 llamadas por problema (Tesis, Antítesis, Síntesis)")
    print("   Estimated time: ~3-4 hours")

    # 1. Cargar problemas
    print(f"\n📚 Loading {N_PROBLEMS} TruthfulQA problems...")
    try:
        problems = load_truthfulqa_problems(n=N_PROBLEMS, seed=SEED)
        print(f"✅ Loaded {len(problems)} problems")

        # Verificar que son los mismos que S3-07
        print("\n🔍 Verification:")
        print(f"   First problem ID: {problems[0]['problem_id']}")
        print(f"   First question: {problems[0]['question'][:60]}...")
        print("   (Should match S3-07 baseline)")

    except Exception as e:
        print(f"❌ Error loading problems: {e}")
        sys.exit(1)

    # 2. Ejecutar T-A-S en cada problema
    results = []
    print(f"\n🚀 Starting T-A-S execution on {len(problems)} problems...")
    print("   (This will take ~3-4 hours due to 3× LLM calls per problem)\n")

    for i, problem in enumerate(problems, 1):
        print(f"\n[{i}/{len(problems)}] Processing {problem['problem_id']}...")
        print(f"  Question: {problem['question'][:60]}...")

        try:
            result = run_tas_on_tqa_problem(problem, RUN_ID)
            results.append(result)

            # Mostrar progreso
            if "error" in result:
                print(f"  ❌ Error: {result['error']}")
            else:
                status = "✅" if result["is_correct"] else "❌"
                tokens = result["tas_usage"]["total_tokens"]
                cost = result["estimated_cost_usd"]

                print(f"  {status} Final answer: {result['predicted_answer_raw'][:50]}...")
                print(f"  📊 Total tokens (3 stages): {tokens:,} | Cost: ${cost:.4f}")

                # Verificar cap de ~24k tokens (3× 8k)
                if tokens > 24000:
                    print("  ⚠️  WARNING: Exceeded ~24k token cap!")

        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            results.append(
                {
                    "run_id": RUN_ID,
                    "problem_id": problem["problem_id"],
                    "question": problem["question"],
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # 3. Budget check cada 10 problemas
        if i % 10 == 0 and results:
            valid_results = [r for r in results if "error" not in r]
            total_cost = sum(r.get("estimated_cost_usd", 0) for r in valid_results)
            correct_count = sum(1 for r in valid_results if r.get("is_correct"))
            accuracy = (correct_count / len(valid_results)) * 100 if valid_results else 0

            print(f"\n{'─' * 70}")
            print(f"💰 Budget Check ({i}/{len(problems)} problems)")
            print(f"{'─' * 70}")
            print(f"Current cost: ${total_cost:.2f}")
            print(f"Budget used: {(total_cost/MAX_COST_USD)*100:.1f}%")
            print(f"Projected total: ${(total_cost/i)*len(problems):.2f}")
            print(f"Current accuracy: {accuracy:.1f}%")

            # Alertar si excedemos presupuesto
            if total_cost > MAX_COST_USD:
                print("\n⚠️  WARNING: Budget exceeded!")
                print("   Consider stopping if projected cost is too high.")

    # 4. Resumen final
    print(f"\n{'=' * 70}")
    print(" EXECUTION COMPLETE")
    print(f"{'=' * 70}")

    # Calcular métricas finales
    valid_results = [r for r in results if "error" not in r]
    error_results = [r for r in results if "error" in r]
    correct_count = sum(1 for r in valid_results if r.get("is_correct"))
    accuracy = (correct_count / len(valid_results)) * 100 if valid_results else 0

    total_tokens = sum(r["tas_usage"]["total_tokens"] for r in valid_results)
    total_cost = sum(r["estimated_cost_usd"] for r in valid_results)
    avg_tokens = total_tokens / len(valid_results) if valid_results else 0

    print("\n📊 Results:")
    print(f"   Total problems: {len(results)}")
    print(f"   Valid results: {len(valid_results)}")
    print(f"   Errors: {len(error_results)}")
    print(f"   Correct: {correct_count}")
    print(f"   Accuracy: {accuracy:.2f}%")
    print(f"   Total tokens: {total_tokens:,}")
    print(f"   Avg tokens/problem: {avg_tokens:.0f}")
    print(f"   Total cost: ${total_cost:.2f}")
    status = "✅ Within budget" if total_cost <= MAX_COST_USD else "⚠️  Over budget"
    print(f"   Budget status: {status}")

    # Comparación con baseline S3-07
    baseline_tokens_avg = 199  # Del análisis S3-07
    if avg_tokens > 0:
        multiplier = avg_tokens / baseline_tokens_avg
        print("\n📈 vs Baseline (S3-07):")
        print(f"   Baseline avg: ~{baseline_tokens_avg} tokens/problem")
        print(f"   T-A-S avg: {avg_tokens:.0f} tokens/problem")
        print(f"   Multiplier: {multiplier:.1f}×")

    # 5. Guardar Parquet
    print("\n💾 Saving results to Parquet...")
    output_dir = Path("analytics/parquet")
    output_dir.mkdir(parents=True, exist_ok=True)

    parquet_filename = f"tas_tqa_50_{RUN_ID}.parquet"
    parquet_path = output_dir / parquet_filename

    # Guardar con pandas
    import pandas as pd

    df = pd.DataFrame(valid_results)
    df.to_parquet(str(parquet_path), index=False)

    print(f"✅ Results saved to: {parquet_path}")

    # 6. Guardar resumen JSON
    summary = {
        "run_id": RUN_ID,
        "timestamp": datetime.now().isoformat(),
        "sprint": "S3-08",
        "dataset": "truthfulqa",
        "method": "tas_k1",
        "n_problems": N_PROBLEMS,
        "seed": SEED,
        "model": MODEL,
        "total_problems": len(results),
        "valid_results": len(valid_results),
        "errors": len(error_results),
        "correct": correct_count,
        "accuracy": accuracy,
        "total_tokens": total_tokens,
        "avg_tokens_per_problem": avg_tokens,
        "total_cost_usd": total_cost,
        "budget_limit_usd": MAX_COST_USD,
        "budget_used_pct": (total_cost / MAX_COST_USD) * 100,
        "vs_baseline_multiplier": multiplier if avg_tokens > 0 else None,
    }

    summary_path = output_dir / f"summary_{RUN_ID}.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"✅ Summary saved to: {summary_path}")

    print(f"\n{'=' * 70}")
    print("✅ S3-08 COMPLETE")
    print(f"{'=' * 70}\n")

    # 7. Siguiente paso
    print("📋 Next steps:")
    print("   1. Review results vs baseline (S3-07)")
    print("   2. Check if accuracy improved")
    print("   3. Proceed to S3-09: T-A-S+MAMV on TruthfulQA 50")


if __name__ == "__main__":
    main()
