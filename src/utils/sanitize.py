import hashlib
import os

ALLOW = {
    "run_id",
    "dataset",
    "problem_id",
    "phase",
    "params",
    "metrics",
    "prompt_hash",
    "response_hash",
    "tokens",  # Token counts
    "estimated_cost_usd",  # Cost estimation
    "model",  # Model used
    "timestamp",  # Timing info
}


def sanitize(record: dict) -> dict:
    salted = os.getenv("SANITIZE_SALT", "salt")
    clean = {k: v for k, v in record.items() if k in ALLOW}
    for k in list(clean.keys()):
        if isinstance(clean[k], str) and len(clean[k]) > 5000:
            clean[k] = clean[k][:5000]
    # ejemplo de hashing de metadatos sensibles si existieran
    if "host" in record:
        clean["host_hash"] = hashlib.sha256((record["host"] + salted).encode()).hexdigest()
    return clean
