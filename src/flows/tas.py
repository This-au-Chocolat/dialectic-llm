"""T-A-S (Thesis-Antithesis-Synthesis) dialectic flow implementation."""

from __future__ import annotations
from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from datetime import timedelta
from dataclasses import dataclass
from typing import Any, Dict
import hashlib, json, os, time, uuid, re
from pathlib import Path

# Import existing infrastructure
from src.utils.config import get_tas_config
from src.utils.tokens import count_tokens
from src.utils.log_utils import log_event_jsonl, log_local_cot
from src.utils.sanitize import sanitize_advanced
from src.llm.client import LLMClient

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
        sanitized_event = {k: (sanitize_for_public(str(v)) if isinstance(v, str) else v) 
                          for k, v in event.items()}
        log_event_jsonl(event.get("stage", "tas"), sanitized_event)

def llm_call(prompt: str, *, temperature: float, model: str = "gpt-4", max_tokens: int = 2000) -> Dict[str, Any]:
    """
    Make LLM call using existing infrastructure.
    Returns {'text': str, 'raw': dict, 'usage': dict}
    """
    start = time.time()
    
    try:
        # Use existing LLM client
        client = LLMClient(model=model)
        response = client.call(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        latency = time.time() - start
        
        return {
            "text": response.get("completion", ""),
            "raw": {
                "latency_s": latency,
                "finish_reason": response.get("finish_reason"),
                "response_id": response.get("response_id"),
                "created": response.get("created")
            },
            "usage": response.get("usage", {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            })
        }
    except Exception as e:
        latency = time.time() - start
        # Fallback with error info
        return {
            "text": f"Error: {str(e)}",
            "raw": {"latency_s": latency, "error": str(e)},
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }

def load_prompt_template(template_name: str) -> str:
    """Load prompt template from file."""
    template_path = Path(f"prompts/tas/{template_name}.txt")
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        # Fallback to inline templates if files don't exist
        fallback_templates = {
            "thesis": """You are solving a math word problem. Provide a concise solution and final numeric answer.
Question: {problem}
Answer with brief reasoning then 'Final:' line.""",
            "antithesis": """Critique the following solution. Identify defects (assumptions, arithmetic, logic, format), propose a corrected perspective.
Solution:
{thesis_response}
Output a short critique and the key opposing point.""",
            "synthesis": """Unify the original solution and the critique into a single improved answer.
- Keep correct steps, fix mistakes flagged in the critique.
- Return a concise reasoning and a line 'Final:' with the numeric answer only.
Original:
{thesis_response}

Critique:
{antithesis_response}"""
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
        max_tokens=config.get_max_tokens_per_phase()
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
        max_tokens=config.get_max_tokens_per_phase()
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
def synthesis(t: Dict[str, Any], a: Dict[str, Any], flow_config: TASFlowConfig = flow_cfg) -> Dict[str, Any]:
    logger = get_run_logger()
    thesis_answer = t["answer"]
    critique = a["critique"]
    prompt = make_prompt_synthesis(thesis_answer, critique)
    prompt_h = hash_text(prompt)

    resp = llm_call(
        prompt, 
        temperature=config.get_synthesis_temperature(),
        model=config.get_primary_model(),
        max_tokens=config.get_max_tokens_per_phase()
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
# Flow (k=1)
# -------------------------------
from prefect import flow

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

if __name__ == "__main__":
    out = run_tas_k1({"id": "demo-1", "question": "If Ana has 3 apples and buys 2 more, how many apples does she have?"})
    print(json.dumps(out, indent=2, ensure_ascii=False))

