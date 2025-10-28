"""Logging utilities with automatic token counting and sanitization."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from utils.sanitize import sanitize
from utils.tokens import add_token_info


def log_event_jsonl(
    record: Dict[str, Any], model: str = "gpt-4", log_dir: str = "logs/events"
) -> None:
    """
    Log an event to JSONL with automatic token counting and sanitization.

    This function:
    1. Adds token counts and cost estimation to the record
    2. Sanitizes the record for safe sharing
    3. Writes to JSONL file with timestamp

    Args:
        record: Event dictionary containing at minimum 'prompt' and 'completion'
        model: Model name for token counting
        log_dir: Directory to write log files
    """
    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Add timestamp
    record["timestamp"] = datetime.utcnow().isoformat()
    record["model"] = model

    # Add token information
    record_with_tokens = add_token_info(record.copy(), model)

    # Sanitize for safe sharing (removes sensitive content)
    clean_record = sanitize(record_with_tokens)

    # Generate filename with date
    date_str = datetime.utcnow().strftime("%Y%m%d")
    filename = f"events_{date_str}.jsonl"
    filepath = log_path / filename

    # Write to JSONL
    with open(filepath, "a", encoding="utf-8") as f:
        json_line = json.dumps(clean_record, ensure_ascii=False)
        f.write(json_line + "\n")


def log_local_cot(record: Dict[str, Any], log_dir: str = "logs_local") -> None:
    """
    Log Chain-of-Thought data locally (not sanitized, never shared).

    This is for detailed debugging and analysis - stays local only.

    Args:
        record: Complete event dictionary including CoT
        log_dir: Local directory for unsanitized logs
    """
    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Add timestamp
    record["timestamp"] = datetime.utcnow().isoformat()

    # Generate filename with date
    date_str = datetime.utcnow().strftime("%Y%m%d")
    filename = f"cot_{date_str}.jsonl"
    filepath = log_path / filename

    # Write complete record (with CoT) to local file
    with open(filepath, "a", encoding="utf-8") as f:
        json_line = json.dumps(record, ensure_ascii=False, indent=None)
        f.write(json_line + "\n")


def create_run_summary(
    run_id: str, total_items: int, total_cost: float, log_dir: str = "logs/events"
) -> None:
    """
    Create a summary file for a completed run.

    Args:
        run_id: Unique identifier for the run
        total_items: Number of items processed
        total_cost: Total estimated cost in USD
        log_dir: Directory to write summary
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    summary = {
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat(),
        "total_items": total_items,
        "total_estimated_cost_usd": round(total_cost, 4),
        "status": "completed",
    }

    filename = f"summary_{run_id}.json"
    filepath = log_path / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
