# tas_k1.py
from __future__ import annotations
from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from datetime import timedelta
from dataclasses import dataclass
from typing import Any, Dict
import hashlib, json, os, time, uuid, re
from pathlib import Path

# -------------------------------
# Configuración
# -------------------------------
@dataclass
class TASConfig:
    t_thesis: float = 0.7
    t_antithesis: float = 0.5   # ajustable
    t_synthesis: float = 0.2
    seed: int = 42
    save_cot_local_only: bool = os.getenv("SAVE_COT_LOCAL_ONLY", "true").lower() == "true"
    logs_dir_public: Path = Path("logs/events")
    logs_dir_local: Path = Path("logs_local")
    dataset_name: str = "gsm8k"
    model_name: str = "your-llm"
    run_id: str = uuid.uuid4().hex

CFG = TASConfig()
CFG.logs_dir_public.mkdir(parents=True, exist_ok=True)
CFG.logs_dir_local.mkdir(parents=True, exist_ok=True)

# -------------------------------
# Utilidades
# -------------------------------
def hash_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def sanitize(text: str) -> str:
    # Remueve posibles PII triviales y CoT si aplica
    text = re.sub(r"\b\d{3}[- ]?\d{2}[- ]?\d{4}\b", "[REDACTED-SSN]", text)  # ejemplo
    if CFG.save_cot_local_only:
        # borra trazas típicas de CoT (marcadores) para compartidos
        text = re.sub(r"(?is)(chain[- ]?of[- ]?thought|reasoning:|step\s*\d+:).*", "[REDACTED-COT]", text)
    return text

def count_tokens_stub(text: str) -> int:
    # Reemplazar luego por tu contador real (tiktoken o API)
    # Aproximación grosera: ~1 token por 4 caracteres
    return max(1, len(text) // 4)

def log_event_jsonl(event: Dict[str, Any], *, local: bool = False) -> None:
    # Guarda evento en JSONL; si local=True va a logs_local (incluye COT)
    path = (CFG.logs_dir_local if local else CFG.logs_dir_public) / f"{CFG.run_id}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def llm_call_stub(prompt: str, *, temperature: float, seed: int) -> Dict[str, Any]:
    """
    Sustituye por tu provider (OpenAI, etc.). Devuelve {'text':..., 'raw':..., 'usage':...}
    """
    # Simulación barata con eco + metadatos
    start = time.time()
    text = f"[T={temperature:.2f} seed={seed}] {prompt[:180]} ... (stub)"
    usage = {
        "prompt_tokens": count_tokens_stub(prompt),
        "completion_tokens": count_tokens_stub(text),
        "total_tokens": 0
    }
    usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
    latency = time.time() - start
    return {"text": text, "raw": {"latency_s": latency}, "usage": usage}

def make_prompt_thesis(item: Any) -> str:
    # item puede ser str o dict {'id','question',...}
    q = item if isinstance(item, str) else item.get("question", str(item))
    return f"""You are solving a math word problem. Provide a concise solution and final numeric answer.
Question: {q}
Answer with brief reasoning then 'Final:' line.
"""

def make_prompt_antithesis(thesis_answer: str) -> str:
    return f"""Critique the following solution. Identify defects (assumptions, arithmetic, logic, format), propose a corrected perspective.
Solution:
{thesis_answer}
Output a short critique and the key opposing point.
"""

def make_prompt_synthesis(thesis_answer: str, critique: str) -> str:
    return f"""Unify the original solution and the critique into a single improved answer.
- Keep correct steps, fix mistakes flagged in the critique.
- Return a concise reasoning and a line 'Final:' with the numeric answer only.
Original:
{thesis_answer}

Critique:
{critique}
"""

# -------------------------------
# Tareas Prefect (con retries/backoff)
# -------------------------------
@task(
    retries=2,
    retry_delay_seconds=[1, 2],  # backoff simple
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(minutes=10),
)
def thesis(item: Any, cfg: TASConfig = CFG) -> Dict[str, Any]:
    logger = get_run_logger()
    prompt = make_prompt_thesis(item)
    prompt_h = hash_text(prompt)

    resp = llm_call_stub(prompt, temperature=cfg.t_thesis, seed=cfg.seed)
    answer = resp["text"]

    event_public = {
        "run_id": cfg.run_id,
        "stage": "thesis",
        "dataset": cfg.dataset_name,
        "model": cfg.model_name,
        "temperature": cfg.t_thesis,
        "seed": cfg.seed,
        "prompt_hash": prompt_h,
        "answer_hash": hash_text(answer),
        "usage": resp["usage"],
        "ts": time.time(),
    }
    event_local = {**event_public, "prompt": prompt, "answer": answer, "raw": resp["raw"]}

    log_event_jsonl(event_local, local=True)
    # Versión pública sanitizada (sin COT explícito)
    public_copy = {**event_public, "answer_preview": sanitize(answer)[:280]}
    log_event_jsonl(public_copy, local=False)

    logger.info("Thesis done.")
    return {"answer": answer, "meta": event_public}

@task(
    retries=2,
    retry_delay_seconds=[1, 2],
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(minutes=10),
)
def antithesis(t: Dict[str, Any], cfg: TASConfig = CFG) -> Dict[str, Any]:
    logger = get_run_logger()
    thesis_answer = t["answer"]
    prompt = make_prompt_antithesis(thesis_answer)
    prompt_h = hash_text(prompt)

    resp = llm_call_stub(prompt, temperature=cfg.t_antithesis, seed=cfg.seed + 1)
    critique = resp["text"]

    event_public = {
        "run_id": cfg.run_id,
        "stage": "antithesis",
        "dataset": cfg.dataset_name,
        "model": cfg.model_name,
        "temperature": cfg.t_antithesis,
        "seed": cfg.seed + 1,
        "prompt_hash": prompt_h,
        "critique_hash": hash_text(critique),
        "usage": resp["usage"],
        "ts": time.time(),
    }
    event_local = {**event_public, "prompt": prompt, "critique": critique, "raw": resp["raw"]}

    log_event_jsonl(event_local, local=True)
    public_copy = {**event_public, "critique_preview": sanitize(critique)[:280]}
    log_event_jsonl(public_copy, local=False)

    logger.info("Antithesis done.")
    return {"critique": critique, "meta": event_public}

@task(
    retries=2,
    retry_delay_seconds=[1, 2],
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(minutes=10),
)
def synthesis(t: Dict[str, Any], a: Dict[str, Any], cfg: TASConfig = CFG) -> Dict[str, Any]:
    logger = get_run_logger()
    thesis_answer = t["answer"]
    critique = a["critique"]
    prompt = make_prompt_synthesis(thesis_answer, critique)
    prompt_h = hash_text(prompt)

    resp = llm_call_stub(prompt, temperature=cfg.t_synthesis, seed=cfg.seed + 2)
    final_answer = resp["text"]

    event_public = {
        "run_id": cfg.run_id,
        "stage": "synthesis",
        "dataset": cfg.dataset_name,
        "model": cfg.model_name,
        "temperature": cfg.t_synthesis,
        "seed": cfg.seed + 2,
        "prompt_hash": prompt_h,
        "final_hash": hash_text(final_answer),
        "usage": resp["usage"],
        "ts": time.time(),
    }
    event_local = {**event_public, "prompt": prompt, "final": final_answer, "raw": resp["raw"]}

    log_event_jsonl(event_local, local=True)
    public_copy = {**event_public, "final_preview": sanitize(final_answer)[:280]}
    log_event_jsonl(public_copy, local=False)

    logger.info("Synthesis done.")
    return {"answer": final_answer, "meta": event_public}

# -------------------------------
# Flow (k=1)
# -------------------------------
from prefect import flow

@flow(name="tas_k1")
def run_tas_k1(item: Any, cfg: TASConfig = CFG) -> Dict[str, Any]:
    """
    item: str | dict{'id','question',...}
    Devuelve dict con 'answer' (texto) y 'meta' (metadatos + hashes/usages).
    """
    t = thesis.submit(item, cfg)
    a = antithesis.submit(t, cfg)
    s = synthesis.submit(t, a, cfg)
    return s.result()

if __name__ == "__main__":
    out = run_tas_k1({"id": "demo-1", "question": "If Ana has 3 apples and buys 2 more, how many apples does she have?"})
    print(json.dumps(out, indent=2, ensure_ascii=False))

