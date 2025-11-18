"""
Módulo de Sanitización de Datos.

Este módulo proporciona funciones para limpiar y anonimizar datos sensibles
en estructuras de datos de Python (diccionarios, listas).
Integrado con el sistema de logging del proyecto dialectic-llm.
"""

import copy
import hashlib
import os
import re
from typing import Any, Dict, List, Tuple

# Patrones de expresiones regulares para detectar información sensible
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[- ]?)?\(?\d{2,3}\)?[- ]?\d{3,4}[- ]?\d{4}")
CREDIT_CARD_REGEX = re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b")
IP_ADDRESS_REGEX = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")

# Order matters! More specific patterns (like CREDIT_CARD) should come before
# more general ones (like PHONE) to avoid partial matches
REDACTION_PATTERNS = [
    ("CREDIT_CARD", CREDIT_CARD_REGEX),
    ("EMAIL", EMAIL_REGEX),
    ("PHONE", PHONE_REGEX),
    ("IP_ADDRESS", IP_ADDRESS_REGEX),
]

# Campos permitidos para compartir (whitelist approach para mayor seguridad)
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
    "sanitization_info",  # Sanitization metadata
    "llm_usage",  # Usage information
    "is_correct",  # Evaluation results
    "accuracy",  # Metrics
    "event_type",  # Event classification
}


def _hash_value(value: str, salt: str) -> str:
    """Genera un hash SHA-256 para un valor usando un salt."""
    return hashlib.sha256((salt + value).encode("utf-8")).hexdigest()


def _sanitize_recursive(
    data: Any, salt: str, fields_to_hash: List[str]
) -> Tuple[Any, List[Dict[str, str]]]:
    """
    Función recursiva para sanitizar datos en diccionarios y listas.
    Devuelve los datos sanitizados y una lista de las acciones realizadas.
    """
    sanitized_actions = []

    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            if key in fields_to_hash:
                new_dict[key] = _hash_value(str(value), salt)
                sanitized_actions.append({"field": key, "action": "hashed"})
            else:
                sanitized_value, actions = _sanitize_recursive(value, salt, fields_to_hash)
                new_dict[key] = sanitized_value
                sanitized_actions.extend(actions)
        return new_dict, sanitized_actions

    if isinstance(data, list):
        new_list = []
        for item in data:
            sanitized_item, actions = _sanitize_recursive(item, salt, fields_to_hash)
            new_list.append(sanitized_item)
            sanitized_actions.extend(actions)
        return new_list, sanitized_actions

    if isinstance(data, str):
        sanitized_string = data
        for name, regex in REDACTION_PATTERNS:
            if regex.search(sanitized_string):
                sanitized_string = regex.sub(f"[REDACTED_{name}]", sanitized_string)
                sanitized_actions.append(
                    {"field": "string_pattern", "action": f"redacted_{name.lower()}"}
                )
        return sanitized_string, sanitized_actions

    return data, sanitized_actions


def sanitize_advanced(data: Dict[str, Any], salt: str, fields_to_hash: List[str]) -> Dict[str, Any]:
    """
    Sanitiza un diccionario usando el enfoque avanzado de Lorena con patrones de detección.

    Args:
        data: El diccionario de datos a sanitizar
        salt: Salt para el hashing
        fields_to_hash: Lista de campos que deben ser hasheados

    Returns:
        Diccionario sanitizado con metadata de sanitización
    """
    if not isinstance(data, dict):
        raise TypeError("La entrada principal de datos debe ser un diccionario.")

    data_copy = copy.deepcopy(data)
    sanitized_data, actions = _sanitize_recursive(data_copy, salt, fields_to_hash)

    if actions:
        unique_actions = [dict(t) for t in {tuple(d.items()) for d in actions}]
        sanitized_data["sanitization_info"] = unique_actions

    return sanitized_data


def sanitize(record: dict) -> dict:
    """
    Sanitiza un registro usando el enfoque de whitelist (compatible con sistema existente).

    Esta función mantiene compatibilidad con el sistema existente mientras
    proporciona sanitización robusta.

    Args:
        record: Diccionario de datos del evento

    Returns:
        Diccionario sanitizado con solo campos permitidos
    """
    salt = os.getenv("SANITIZE_SALT", "dialectic-llm-default-salt")

    # Whitelist approach: solo campos permitidos
    clean = {k: v for k, v in record.items() if k in ALLOW}

    # Truncar strings muy largos para evitar problemas de memoria
    for k in list(clean.keys()):
        if isinstance(clean[k], str) and len(clean[k]) > 5000:
            clean[k] = clean[k][:5000]

    # Hash de metadatos sensibles si existen
    if "host" in record:
        clean["host_hash"] = _hash_value(record["host"], salt)

    # Aplicar sanitización avanzada si hay contenido que puede contener PII
    sensitive_fields = ["prompt", "completion", "response", "user_input"]
    fields_to_hash = os.getenv("LOG_FIELDS_TO_SANITIZE", "user_id,session_id,tenant_id").split(",")
    fields_to_hash = [f.strip() for f in fields_to_hash if f.strip()]

    if any(field in record for field in sensitive_fields) and fields_to_hash:
        # Aplicar sanitización avanzada solo a los campos sensibles
        temp_record = {
            k: v for k, v in record.items() if k in sensitive_fields or k in fields_to_hash
        }
        if temp_record:
            try:
                sanitized_advanced = sanitize_advanced(temp_record, salt, fields_to_hash)
                # Mantener solo metadata de sanitización, no el contenido completo
                if "sanitization_info" in sanitized_advanced:
                    clean["sanitization_info"] = sanitized_advanced["sanitization_info"]
            except Exception:
                # Si falla la sanitización avanzada, continuar sin ella
                pass

    return clean
