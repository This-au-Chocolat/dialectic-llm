"""
Logging utilities with automatic token counting and sanitization.
Integra el trabajo de Lorena con el sistema existente para cumplir S1-09.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from utils.sanitize import sanitize, sanitize_advanced
from utils.tokens import add_token_info

# Configuración global
FIELDS_TO_SANITIZE_STR = os.getenv("LOG_FIELDS_TO_SANITIZE", "user_id,session_id,tenant_id")
FIELDS_TO_HASH = [field.strip() for field in FIELDS_TO_SANITIZE_STR.split(",") if field.strip()]


def log_event_jsonl(
    record: Dict[str, Any], model: str = "gpt-4", log_dir: str = "logs/events"
) -> None:
    """
    Log an event to JSONL with automatic token counting and sanitization.

    This function implements S1-09 requirements:
    1. Adds token counts and cost estimation to the record
    2. Sanitizes the record for safe sharing using Lorena's advanced sanitization
    3. Writes to JSONL file with timestamp
    4. Ensures CoT never leaves logs_local directory

    Args:
        record: Event dictionary containing at minimum 'prompt' and 'completion'
        model: Model name for token counting
        log_dir: Directory to write log files (shared logs only)
    """
    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Add timestamp and model info
    enriched_record = record.copy()
    enriched_record["timestamp"] = datetime.utcnow().isoformat()
    enriched_record["model"] = model

    # Add token information
    record_with_tokens = add_token_info(enriched_record, model)

    # Enhanced sanitization using Lorena's approach
    salt = os.getenv("SANITIZE_SALT", "dialectic-llm-default-salt")

    # Si hay campos sensibles, usar sanitización avanzada de Lorena
    if FIELDS_TO_HASH and any(field in record_with_tokens for field in FIELDS_TO_HASH):
        try:
            sanitized_record = sanitize_advanced(record_with_tokens, salt, FIELDS_TO_HASH)
        except Exception:
            # Fallback a sanitización básica si falla la avanzada
            sanitized_record = sanitize(record_with_tokens)
    else:
        # Usar sanitización básica (whitelist)
        sanitized_record = sanitize(record_with_tokens)

    # Generate filename with date
    date_str = datetime.utcnow().strftime("%Y%m%d")
    filename = f"events_{date_str}.jsonl"
    filepath = log_path / filename

    # Write to JSONL
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            json_line = json.dumps(sanitized_record, ensure_ascii=False)
            f.write(json_line + "\n")
    except IOError as e:
        print(f"Error: No se pudo escribir en el archivo de log {filepath}. Detalles: {e}")
    except Exception as e:
        print(f"Un error inesperado ocurrió durante el logging: {e}")


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


def log_event(record: Dict[str, Any], log_file_name: str = "events.jsonl") -> None:
    """
    Wrapper compatible con el ejemplo de Lorena.

    Esta función mantiene compatibilidad con example_usage.py mientras
    usa nuestro sistema mejorado.

    Args:
        record: El diccionario de datos del evento a registrar
        log_file_name: El nombre del archivo de log
    """
    if not isinstance(record, dict):
        raise TypeError(f"El registro debe ser un diccionario, pero se recibió {type(record)}")

    # Crear registro con metadatos adicionales
    enhanced_record = record.copy()
    enhanced_record["event_type"] = "general"

    # Usar nuestro sistema principal de logging
    log_event_jsonl(enhanced_record, log_dir="logs/events")
