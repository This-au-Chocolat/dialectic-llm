"""S2-05 RESUME: Reanudar ejecución T-A-S desde problema 28.

Este script reanuda la ejecución desde donde se detuvo por límite de presupuesto.
- Problemas ya completados: 27 (gsm8k-0002 hasta problemas varios)
- Problemas pendientes: 173 (desde problema 28 hasta 200)
- Presupuesto restante: ~$1.50 USD (de $5 total, ya gastados $3.50)

IMPORTANTE: Aumentar límite en OpenAI Dashboard a $5 USD antes de ejecutar.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set

from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("❌ Error: OPENAI_API_KEY not found")
    sys.exit(1)

sys.path.append(str(Path(__file__).parent / "src"))

from flows.tas import TASFlowConfig, run_tas_k1  # noqa: E402
from llm.client import extract_gsm8k_answer  # noqa: E402
from utils.evaluation import coherence_ts, evaluate_exact_match  # noqa: E402
from utils.parquet_utils import create_tas_parquet  # noqa: E402
from utils.tokens import estimate_cost  # noqa: E402

# Configuración
IDS_FILE = "data/processed/gsm8k_s1_200_seed42_ids.json"
LOGS_FILE = "logs_local/cot_20251123.jsonl"
MAX_COST_USD = 5.0
RUN_ID = "s2_tas_gpt35_k1_resume_20251123"
MODEL = "gpt-3.5-turbo"


def get_completed_problem_ids() -> Set[str]:
    """Obtener IDs de problemas ya completados del log."""
    completed = set()
    if Path(LOGS_FILE).exists():
        with open(LOGS_FILE, "r") as f:
            for line in f:
                try:
                    event = json.loads(line)
                    if event.get("stage") == "synthesis":
                        completed.add(event.get("problem_id"))
                except Exception:
                    continue
    return completed


def load_problem_ids(filepath: str = IDS_FILE) -> List[str]:
    """Cargar IDs de problemas desde archivo JSON."""
    with open(filepath, "r") as f:
        data = json.load(f)
    return data["ids"]  # Las preguntas completas


def load_problems_by_questions(questions: List[str]) -> List[Dict]:
    """Cargar problemas usando seed-based selection como S1."""
    import random

    from datasets import load_dataset

    dataset = load_dataset("openai/gsm8k", "main", split="test")

    # Usar mismo seed que S1 para obtener mismos 200 problemas
    random.seed(42)
    indices = list(range(len(dataset)))
    random.shuffle(indices)
    selected_indices = sorted(indices[:200])

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

    return problems


def run_tas_on_problem(problem: Dict, config: TASFlowConfig) -> Dict:
    """Ejecutar T-A-S en un problema y retornar resultado."""
    # Ejecutar T-A-S flow
    tas_result = run_tas_k1(problem, config)

    # Extraer respuesta final (synthesis)
    synthesis_text = tas_result["synthesis"]["answer"]
    predicted_answer_raw = extract_gsm8k_answer(synthesis_text)

    # Evaluar corrección
    is_correct = evaluate_exact_match(y_true=problem["answer"], y_pred_raw=predicted_answer_raw)

    # Calcular coherencia entre thesis y synthesis
    thesis_text = tas_result["thesis"]["answer"]
    coherence = coherence_ts(thesis_text, synthesis_text)

    # Agregar usage de las 3 fases
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for stage in ["thesis", "antithesis", "synthesis"]:
        usage = tas_result[stage]["meta"]["usage"]
        total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
        total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
        total_usage["total_tokens"] += usage.get("total_tokens", 0)

    # Estimar costo
    cost_estimate = estimate_cost(total_usage, MODEL)

    return {
        "run_id": config.run_id,
        "problem_id": problem["problem_id"],
        "dataset": config.dataset_name,
        "phase": "tas_k1",
        "model": MODEL,
        "question": problem["question"],
        "true_answer": problem["answer"],
        "predicted_answer_raw": predicted_answer_raw,
        "is_correct": is_correct,
        "coherence_t_s": coherence,
        "thesis_text": thesis_text,
        "synthesis_text": synthesis_text,
        "tas_usage": total_usage,
        "cost_estimate": cost_estimate,
    }


def main():
    """Ejecutar reanudación de S2-05."""
    print("=" * 70)
    print("S2-05 RESUME: Reanudar T-A-S (k=1) con GPT-3.5-turbo")
    print("=" * 70)
    print(f"Run ID: {RUN_ID}")
    print(f"Budget: ${MAX_COST_USD:.2f}")
    print(f"Model: {MODEL}")
    print()

    # 1. Obtener problemas ya completados
    print("📋 Verificando progreso anterior...")
    completed_ids = get_completed_problem_ids()
    print(f"✅ Problemas ya completados: {len(completed_ids)}")

    # 2. Cargar todos los 200 problemas
    print("\n📚 Cargando problemas desde dataset...")
    problem_ids = load_problem_ids()
    all_problems = load_problems_by_questions(problem_ids)
    print(f"✅ Cargados {len(all_problems)} problemas totales")

    # 3. Filtrar pendientes
    pending_problems = [p for p in all_problems if p["problem_id"] not in completed_ids]
    print(f"📝 Problemas pendientes: {len(pending_problems)}")
    print(f"   Desde: {pending_problems[0]['problem_id']}")
    print(f"   Hasta: {pending_problems[-1]['problem_id']}")

    if not pending_problems:
        print("\n✅ ¡Todos los problemas ya están completados!")
        return

    # 4. Ejecutar T-A-S en problemas pendientes
    print(f"\n🚀 Reanudando ejecución en {len(pending_problems)} problemas...")
    print(f"   (Costo estimado: ~${len(pending_problems) * 0.012:.2f} USD)\n")

    config = TASFlowConfig(run_id=RUN_ID, dataset_name="gsm8k", model_name=MODEL, seed=42)

    results = []
    total_cost = 0.0
    correct_count = 0

    for i, problem in enumerate(pending_problems, start=len(completed_ids) + 1):
        print(f"[{i}/{len(all_problems)}] Processing {problem['problem_id']}...")

        try:
            result = run_tas_on_problem(problem, config)
            results.append(result)

            # Actualizar contadores
            total_cost += result.get("cost_estimate", 0.0)
            if result["is_correct"]:
                correct_count += 1

            # Mostrar resultado
            status = "✅" if result["is_correct"] else "❌"
            print(f"  {status} Answer: {result['predicted_answer_raw']}")
            tokens = result["tas_usage"]["total_tokens"]
            cost = result["cost_estimate"]
            print(f"  📊 Tokens: {tokens:,} | Cost: ${cost:.4f}")
            print(f"  🔗 Coherence: {result['coherence_t_s']:.3f}")
            print()

            # Budget check cada 10 problemas
            if i % 10 == 0:
                print("-" * 70)
                print(f"💰 Budget Check ({i}/{len(all_problems)} problems)")
                print("-" * 70)
                print(f"Current cost: ${total_cost:.2f}")
                print(f"Budget used: {(total_cost/MAX_COST_USD)*100:.1f}%")
                projected = (total_cost / (i - len(completed_ids))) * len(pending_problems)
                print(f"Projected total: ${total_cost + projected:.2f}")
                print()

            # Detener si excede presupuesto
            if total_cost >= MAX_COST_USD * 1.5:  # 150% del máximo
                print(f"⚠️  Budget limit exceeded (${total_cost:.2f}). Stopping.")
                break

        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            results.append(
                {
                    "run_id": RUN_ID,
                    "problem_id": problem["problem_id"],
                    "dataset": "gsm8k",
                    "phase": "tas_k1",
                    "model": MODEL,
                    "question": problem["question"],
                    "true_answer": problem["answer"],
                    "predicted_answer_raw": None,
                    "is_correct": False,
                    "coherence_t_s": None,
                    "thesis_text": None,
                    "synthesis_text": None,
                    "tas_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "cost_estimate": 0.0,
                    "error": str(e),
                }
            )

    # 6. Resumen final
    print("\n" + "=" * 70)
    print("📊 RESUMEN FINAL")
    print("=" * 70)
    total_completed = len(completed_ids) + len(results)
    total_accuracy = correct_count / len(results) if results else 0
    print(f"Total completado: {total_completed}/200 problemas")
    print(f"Nuevos: {len(results)} problemas")
    print(f"Accuracy (nuevos): {total_accuracy:.3f} ({correct_count}/{len(results)})")
    print(f"💰 Costo sesión: ${total_cost:.2f}")
    print()

    # 7. Guardar Parquet (solo problemas nuevos)
    if results:
        print("💾 Guardando resultados a Parquet...")
        parquet_path = create_tas_parquet(results, RUN_ID)
        print(f"✅ Guardado en: {parquet_path}")

    print("\n✅ Reanudación completada!")


if __name__ == "__main__":
    main()
