"""T-A-S (Thesis-Antithesis-Synthesis) dialectic flow implementation."""

from __future__ import annotations

import hashlib
import json
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from prefect import flow, get_run_logger, task
from prefect.tasks import task_input_hash

from src.llm.client import LLMClient

# Import existing infrastructure
from src.utils.config import get_tas_config
from src.utils.log_utils import log_event_jsonl, log_local_cot
from src.utils.sanitize import sanitize_advanced
from src.utils.tokens import count_tokens


# -------------------------------
# Configuration
# -------------------------------
@dataclass
class TASFlowConfig:
    """Extended configuration for T-A-S flow execution."""

    seed: int = 42
    dataset_name: str = "gsm8k"
    model_name: str = "gpt-4"
    run_id: str = uuid.uuid4().hex


# Initialize configurations
config = get_tas_config()
flow_cfg = TASFlowConfig()

# Ensure directories exist
Path("logs/events").mkdir(parents=True, exist_ok=True)
Path("logs_local").mkdir(parents=True, exist_ok=True)


# -------------------------------
# Utilities (using existing infrastructure)
# -------------------------------
def hash_text(s: str) -> str:
    """Hash text for consistent identification."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sanitize_for_public(text: str) -> str:
    """Sanitize text for public logs using existing sanitization."""
    return sanitize_advanced(text)


def count_tokens_from_text(text: str, model: str = "gpt-4") -> int:
    """Count tokens using existing token counter."""
    # Use existing count_tokens function
    event = {"prompt": text, "completion": ""}
    token_info = count_tokens(event, model)
    return token_info.get("prompt_tokens", 0)


def log_tas_event(event: Dict[str, Any], *, local: bool = False) -> None:
    """Log T-A-S event using existing infrastructure."""
    if local:
        # Save full event with CoT to local logs
        log_local_cot(event.get("stage", "tas"), event)
    else:
        # Save sanitized event to shared logs
        sanitized_event = {
            k: (sanitize_for_public(str(v)) if isinstance(v, str) else v) for k, v in event.items()
        }
        log_event_jsonl(event.get("stage", "tas"), sanitized_event)


def llm_call(
    prompt: str, *, temperature: float, model: str = "gpt-4", max_tokens: int = 2000
) -> Dict[str, Any]:
    """
    Make LLM call using existing infrastructure.
    Returns {'text': str, 'raw': dict, 'usage': dict}
    """
    start = time.time()

    try:
        # Use existing LLM client
        client = LLMClient(model=model)
        response = client.call(prompt=prompt, temperature=temperature, max_tokens=max_tokens)

        latency = time.time() - start

        return {
            "text": response.get("completion", ""),
            "raw": {
                "latency_s": latency,
                "finish_reason": response.get("finish_reason"),
                "response_id": response.get("response_id"),
                "created": response.get("created"),
            },
            "usage": response.get(
                "usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            ),
        }
    except Exception as e:
        latency = time.time() - start
        # Fallback with error info
        return {
            "text": f"Error: {str(e)}",
            "raw": {"latency_s": latency, "error": str(e)},
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }


def load_prompt_template(template_name: str) -> str:
    """Load prompt template from file."""
    template_path = Path(f"prompts/tas/{template_name}.txt")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        # Fallback to inline templates if files don't exist
        fallback_templates = {
            "thesis": (
                "You are solving a math word problem. "
                "Provide a concise solution and final numeric answer.\n"
                "Question: {problem}\n"
                "Answer with brief reasoning then 'Final:' line."
            ),
            "antithesis": (
                "Critique the following solution. "
                "Identify defects (assumptions, arithmetic, logic, format), "
                "propose a corrected perspective.\n"
                "Solution:\n"
                "{thesis_response}\n"
                "Output a short critique and the key opposing point."
            ),
            "synthesis": (
                "Unify the original solution and the critique "
                "into a single improved answer.\n"
                "- Keep correct steps, fix mistakes flagged in the critique.\n"
                "- Return a concise reasoning and a line 'Final:' "
                "with the numeric answer only.\n"
                "Original:\n"
                "{thesis_response}\n\n"
                "Critique:\n"
                "{antithesis_response}"
            ),
        }
        return fallback_templates.get(template_name, "Template not found: {problem}")


def make_prompt_thesis(item: Any) -> str:
    """Create thesis prompt using template."""
    problem = item if isinstance(item, str) else item.get("question", str(item))
    template = load_prompt_template("thesis")
    return template.format(problem=problem)


def make_prompt_antithesis(thesis_answer: str) -> str:
    """Create antithesis prompt using template."""
    template = load_prompt_template("antithesis")
    return template.format(thesis_response=thesis_answer)


def make_prompt_synthesis(thesis_answer: str, critique: str) -> str:
    """Create synthesis prompt using template."""
    template = load_prompt_template("synthesis")
    return template.format(thesis_response=thesis_answer, antithesis_response=critique)


# -------------------------------
# Tareas Prefect (con retries/backoff)
# -------------------------------
@task(
    retries=2,
    retry_delay_seconds=[1, 2],  # backoff simple
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(minutes=10),
)
def thesis(item: Any, flow_config: TASFlowConfig = flow_cfg) -> Dict[str, Any]:
    logger = get_run_logger()
    prompt = make_prompt_thesis(item)
    prompt_h = hash_text(prompt)

    # Use configured temperature and model
    resp = llm_call(
        prompt,
        temperature=config.get_thesis_temperature(),
        model=config.get_primary_model(),
        max_tokens=config.get_max_tokens_per_phase(),
    )
    answer = resp["text"]

    event_public = {
        "run_id": flow_config.run_id,
        "stage": "thesis",
        "dataset": flow_config.dataset_name,
        "model": flow_config.model_name,
        "temperature": config.get_thesis_temperature(),
        "seed": flow_config.seed,
        "prompt_hash": prompt_h,
        "answer_hash": hash_text(answer),
        "usage": resp["usage"],
        "ts": time.time(),
    }
    event_local = {**event_public, "prompt": prompt, "answer": answer, "raw": resp["raw"]}

    log_tas_event(event_local, local=True)
    # Versión pública sanitizada
    public_copy = {**event_public, "answer_preview": sanitize_for_public(answer)[:280]}
    log_tas_event(public_copy, local=False)

    logger.info("Thesis done.")
    return {"answer": answer, "meta": event_public}


@task(
    retries=2,
    retry_delay_seconds=[1, 2],
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(minutes=10),
)
def antithesis(t: Dict[str, Any], flow_config: TASFlowConfig = flow_cfg) -> Dict[str, Any]:
    logger = get_run_logger()
    thesis_answer = t["answer"]
    prompt = make_prompt_antithesis(thesis_answer)
    prompt_h = hash_text(prompt)

    resp = llm_call(
        prompt,
        temperature=config.get_antithesis_temperature(),
        model=config.get_primary_model(),
        max_tokens=config.get_max_tokens_per_phase(),
    )
    critique = resp["text"]

    event_public = {
        "run_id": flow_config.run_id,
        "stage": "antithesis",
        "dataset": flow_config.dataset_name,
        "model": flow_config.model_name,
        "temperature": config.get_antithesis_temperature(),
        "seed": flow_config.seed + 1,
        "prompt_hash": prompt_h,
        "critique_hash": hash_text(critique),
        "usage": resp["usage"],
        "ts": time.time(),
    }
    event_local = {**event_public, "prompt": prompt, "critique": critique, "raw": resp["raw"]}

    log_tas_event(event_local, local=True)
    public_copy = {**event_public, "critique_preview": sanitize_for_public(critique)[:280]}
    log_tas_event(public_copy, local=False)

    logger.info("Antithesis done.")
    return {"critique": critique, "meta": event_public}


@task(
    retries=2,
    retry_delay_seconds=[1, 2],
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(minutes=10),
)
def synthesis(
    t: Dict[str, Any], a: Dict[str, Any], flow_config: TASFlowConfig = flow_cfg
) -> Dict[str, Any]:
    logger = get_run_logger()
    thesis_answer = t["answer"]
    critique = a["critique"]
    prompt = make_prompt_synthesis(thesis_answer, critique)
    prompt_h = hash_text(prompt)

    resp = llm_call(
        prompt,
        temperature=config.get_synthesis_temperature(),
        model=config.get_primary_model(),
        max_tokens=config.get_max_tokens_per_phase(),
    )
    final_answer = resp["text"]

    event_public = {
        "run_id": flow_config.run_id,
        "stage": "synthesis",
        "dataset": flow_config.dataset_name,
        "model": flow_config.model_name,
        "temperature": config.get_synthesis_temperature(),
        "seed": flow_config.seed + 2,
        "prompt_hash": prompt_h,
        "final_hash": hash_text(final_answer),
        "usage": resp["usage"],
        "ts": time.time(),
    }
    event_local = {**event_public, "prompt": prompt, "final": final_answer, "raw": resp["raw"]}

    log_tas_event(event_local, local=True)
    public_copy = {**event_public, "final_preview": sanitize_for_public(final_answer)[:280]}
    log_tas_event(public_copy, local=False)

    logger.info("Synthesis done.")
    return {"answer": final_answer, "meta": event_public}


# -------------------------------
# T-A-S Flow for single items (k=1)
# -------------------------------


@flow(name="tas_k1")
def run_tas_k1(item: Any, flow_config: TASFlowConfig = flow_cfg) -> Dict[str, Any]:
    """
    Execute full T-A-S pipeline for a single item.

    Args:
        item: str | dict{'id','question',...} - the problem to solve
        flow_config: TASFlowConfig - flow execution configuration

    Returns:
        dict with 'answer' (final synthesis) and 'meta' (metadata)
    """
    t = thesis.submit(item, flow_config)
    a = antithesis.submit(t, flow_config)
    s = synthesis.submit(t, a, flow_config)
    return s.result()


# -------------------------------
# T-A-S Batch Evaluation Tasks
# -------------------------------


@task(name="load_tas_batch")
def load_tas_batch(n: int, seed: int = 42) -> List[Dict[str, Any]]:
    """
    Load a batch of GSM8K problems for T-A-S evaluation.

    Args:
        n: Number of problems to load
        seed: Random seed for reproducibility

    Returns:
        List of problem dictionaries
    """
    # Import here to avoid circular imports
    from dialectic_llm.data import load_batch

    dataset = load_batch(n=n, seed=seed)

    problems = []
    for i, item in enumerate(dataset):
        # Extract numeric answer from GSM8K format (after ####)
        from llm.client import extract_gsm8k_answer

        numeric_answer = extract_gsm8k_answer(item["answer"])

        try:
            answer_float = float(numeric_answer.replace(",", ""))
        except (ValueError, AttributeError):
            # Fallback: try to find last number in answer
            import re

            numbers = re.findall(r"[\d,]+", item["answer"])
            answer_float = float(numbers[-1].replace(",", "")) if numbers else 0.0

        problems.append(
            {
                "problem_id": f"gsm8k_{i:04d}",
                "question": item["question"],
                "answer": answer_float,  # Extracted numeric answer
                "answer_raw": item["answer"],  # Full GSM8K answer with steps
            }
        )

    return problems


@task(name="solve_tas_problem")
def solve_tas_problem(
    problem: Dict[str, Any], run_id: str, flow_config: TASFlowConfig
) -> Dict[str, Any]:
    """
    Solve a single GSM8K problem using T-A-S approach.

    Args:
        problem: Problem dictionary with question and answer
        run_id: Unique identifier for this run
        flow_config: Flow configuration

    Returns:
        Result dictionary with T-A-S prediction and evaluation
    """
    logger = get_run_logger()

    # Execute T-A-S flow for this problem
    tas_result = run_tas_k1(problem, flow_config)
    final_answer_text = tas_result["answer"]

    # Extract numeric answer from T-A-S result
    from llm.client import extract_gsm8k_answer

    predicted_answer_raw = extract_gsm8k_answer(final_answer_text)

    # Evaluate correctness
    from utils.evaluation import evaluate_exact_match

    is_correct = evaluate_exact_match(y_true=problem["answer"], y_pred_raw=predicted_answer_raw)

    # Aggregate usage stats from T-A-S meta
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    # Calculate total tokens across all phases
    if "meta" in tas_result and "usage" in tas_result["meta"]:
        usage = tas_result["meta"]["usage"]
        total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
        total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
        total_usage["total_tokens"] += usage.get("total_tokens", 0)

    # Create result
    result = {
        "run_id": run_id,
        "problem_id": problem["problem_id"],
        "dataset": flow_config.dataset_name,
        "phase": "tas_k1",
        "model": flow_config.model_name,
        "question": problem["question"],
        "true_answer": problem["answer"],
        "predicted_answer_raw": predicted_answer_raw,
        "tas_final_text": final_answer_text,
        "is_correct": is_correct,
        "tas_usage": total_usage,
        "error": None,  # T-A-S has internal error handling
    }

    logger.info(f"T-A-S problem {problem['problem_id']}: {'✓' if is_correct else '✗'}")

    return result


@task(name="log_tas_result")
def log_tas_result(result: Dict[str, Any]) -> None:
    """
    Log T-A-S evaluation result to events.

    Args:
        result: Result dictionary from solve_tas_problem
    """
    # Create sanitized log event (no CoT)
    log_event = {
        "event_type": "tas_evaluation",
        "timestamp": datetime.now().isoformat(),
        "run_id": result["run_id"],
        "problem_id": result["problem_id"],
        "dataset": result["dataset"],
        "phase": result["phase"],
        "model": result["model"],
        "is_correct": result["is_correct"],
        "usage": result["tas_usage"],
        "prompt": "",  # Required for token counting, empty for TAS
        "completion": "",  # Required for token counting, empty for TAS
    }

    log_event_jsonl(log_event, model=result["model"])


@task(name="create_tas_parquet")
def create_tas_parquet(results: List[Dict[str, Any]], run_id: str) -> str:
    """
    Create Parquet file from T-A-S results for analytics.

    Args:
        results: List of result dictionaries
        run_id: Run identifier

    Returns:
        Path to created Parquet file
    """
    # Prepare data for Parquet
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
            "has_error": result.get("error") is not None,
            "prompt_tokens": result.get("tas_usage", {}).get("prompt_tokens", 0),
            "completion_tokens": result.get("tas_usage", {}).get("completion_tokens", 0),
            "total_tokens": result.get("tas_usage", {}).get("total_tokens", 0),
        }
        df_data.append(row)

    # Create DataFrame and save as Parquet
    df = pd.DataFrame(df_data)

    # Ensure analytics directory exists
    Path("analytics/parquet").mkdir(parents=True, exist_ok=True)

    parquet_path = f"analytics/parquet/tas_{run_id}.parquet"
    df.to_parquet(parquet_path, index=False)

    return parquet_path


# -------------------------------
# Main T-A-S Orchestration Flow
# -------------------------------


@flow(name="tas_gsm8k_flow", log_prints=True)
def run_tas_gsm8k(
    n_problems: int = 50,
    seed: int = 42,
    model: str = "gpt-4",
    run_id: Optional[str] = None,
    dry_run: bool = False,
    max_cost_usd: float = 25.0,
) -> Dict[str, Any]:
    """
    Run T-A-S evaluation on GSM8K problems using Prefect orchestration.

    This is the main flow for S1-08 that orchestrates the complete T-A-S pipeline:
    1. Load GSM8K problems
    2. Execute T-A-S (k=1) on each problem
    3. Evaluate correctness
    4. Log results and create analytics

    Args:
        n_problems: Number of problems to evaluate (~50 for S1-12 pilot)
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
        run_id = f"tas_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

    print(f"🚀 Starting T-A-S evaluation: {run_id}")
    print(f"📊 Problems: {n_problems}, Model: {model}, Seed: {seed}")

    if dry_run:
        print("🔄 DRY RUN MODE: Using mock responses")

    # Create flow configuration
    flow_config = TASFlowConfig(seed=seed, dataset_name="gsm8k", model_name=model, run_id=run_id)

    # Load problems
    print("📥 Loading GSM8K problems...")
    problems = load_tas_batch(n=n_problems, seed=seed)
    print(f"✅ Loaded {len(problems)} problems")

    # Solve problems using T-A-S
    print("🧠 Executing T-A-S pipeline...")
    results = []
    total_cost = 0.0

    for i, problem in enumerate(problems):
        print(f"🔄 Processing problem {i + 1}/{len(problems)}: {problem['problem_id']}")

        if dry_run:
            # Mock T-A-S result for dry run
            import random

            random.seed(seed + i)  # Deterministic for testing
            is_correct = random.random() < 0.75  # 75% mock accuracy for T-A-S

            mock_result = {
                "run_id": run_id,
                "problem_id": problem["problem_id"],
                "dataset": flow_config.dataset_name,
                "phase": "tas_k1",
                "model": flow_config.model_name,
                "question": problem["question"],
                "true_answer": problem["answer"],
                "predicted_answer_raw": str(problem["answer"])
                if is_correct
                else str(problem["answer"] + 1),
                "tas_final_text": f"Mock T-A-S solution: {problem['answer']}",
                "is_correct": is_correct,
                "tas_usage": {"prompt_tokens": 150, "completion_tokens": 200, "total_tokens": 350},
                "error": None,
            }
            result = mock_result
        else:
            # Real T-A-S execution
            result = solve_tas_problem(problem=problem, run_id=run_id, flow_config=flow_config)

        # Log the result
        log_tas_result(result)
        results.append(result)

        # Track cost (rough estimate)
        tokens = result.get("tas_usage", {}).get("total_tokens", 0)
        if tokens > 0:
            # T-A-S uses multiple calls, so higher cost than baseline
            # Rough estimate: $0.045 per 1K tokens average
            cost = (tokens / 1000) * 0.045
            total_cost += cost

        # Safety check: don't exceed cost limit
        if total_cost > max_cost_usd:
            print(f"⚠️  Cost limit reached (${total_cost:.2f}). Stopping at {i + 1} problems.")
            break

    # Calculate metrics
    correct_count = sum(1 for r in results if r["is_correct"])
    accuracy = correct_count / len(results) if results else 0.0
    error_count = sum(1 for r in results if r.get("error"))

    print(f"✅ Completed {len(results)} problems")
    print(f"📈 Accuracy: {accuracy:.3f} ({correct_count}/{len(results)})")
    print(f"❌ Errors: {error_count}")
    print(f"💰 Estimated cost: ${total_cost:.2f}")

    # Create Parquet file for analytics
    print("📊 Creating analytics Parquet...")
    parquet_path = create_tas_parquet(results, run_id)
    print(f"💾 Results saved to: {parquet_path}")

    # Create run summary
    from utils.log_utils import create_run_summary

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
        "approach": "tas_k1",
    }

    return summary


# -------------------------------
# Command Line Interface
# -------------------------------


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run T-A-S evaluation on GSM8K")
    parser.add_argument("--problems", "-n", type=int, default=5, help="Number of problems")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--model", type=str, default="gpt-4", help="LLM model")
    parser.add_argument("--dry-run", action="store_true", help="Use mock responses")
    parser.add_argument("--max-cost", type=float, default=25.0, help="Max cost in USD")

    args = parser.parse_args()

    # Test single item first
    if len(sys.argv) == 1:  # No arguments, run demo
        print("🧪 Demo: Single T-A-S execution")
        out = run_tas_k1(
            {
                "id": "demo-1",
                "question": "If Ana has 3 apples and buys 2 more, how many apples does she have?",
            }
        )
        print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    else:
        # Run batch evaluation
        result = run_tas_gsm8k(
            n_problems=args.problems,
            seed=args.seed,
            model=args.model,
            dry_run=args.dry_run,
            max_cost_usd=args.max_cost,
        )
        print(f"\n🎉 T-A-S evaluation completed: {result}")
