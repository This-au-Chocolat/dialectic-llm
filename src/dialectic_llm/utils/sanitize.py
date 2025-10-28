"""
Módulo de Sanitización de Datos.

Este módulo proporciona funciones para limpiar y anonimizar datos sensibles
en estructuras de datos de Python (diccionarios, listas).
"""

import re
import hashlib
import copy
from typing import Any, Dict, List, Union, Tuple


EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_REGEX = re.compile(r'(?:\+?\d{1,3}[- ]?)?\(?\d{2,3}\)?[- ]?\d{3,4}[- ]?\d{4}')
CREDIT_CARD_REGEX = re.compile(r'\b(?:\d{4}[- ]?){3}\d{4}\b')
IP_ADDRESS_REGEX = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')

REDACTION_PATTERNS = {
    "EMAIL": EMAIL_REGEX,
    "PHONE": PHONE_REGEX,
    "CREDIT_CARD": CREDIT_CARD_REGEX,
    "IP_ADDRESS": IP_ADDRESS_REGEX,
}

def _hash_value(value: str, salt: str) -> str:
    """Genera un hash SHA-256 para un valor usando un salt."""
    return hashlib.sha256((salt + value).encode('utf-8')).hexdigest()

def _sanitize_recursive(data: Any, salt: str, fields_to_hash: List[str]) -> Tuple[Any, List[Dict[str, str]]]:
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
        for name, regex in REDACTION_PATTERNS.items():
            if regex.search(sanitized_string):
                sanitized_string = regex.sub(f"[REDACTED_{name}]", sanitized_string)
                sanitized_actions.append({"field": "string_pattern", "action": f"redacted_{name.lower()}"})
        return sanitized_string, sanitized_actions

    return data, sanitized_actions


def sanitize(
    data: Dict[str, Any],
    salt: str,
    fields_to_hash: List[str]
) -> Dict[str, Any]:
    """
    Sanitiza un diccionario de datos, anonimizando campos específicos y
    eliminando información sensible detectada por patrones.

    Args:
        data (Dict[str, Any]): El diccionario de datos a sanitizar.
        salt (str): Un salt para el hashing, asegurando consistencia.
        fields_to_hash (List[str]): Una lista de claves de diccionario cuyos
                                     valores serán hasheados.

    Returns:
        Dict[str, Any]: Un nuevo diccionario con los datos sanitizados y
                        un campo `sanitization_info` que detalla las
                        acciones realizadas.
    """
    if not isinstance(data, dict):
        raise TypeError("La entrada principal de datos debe ser un diccionario.")


    data_copy = copy.deepcopy(data)

    sanitized_data, actions = _sanitize_recursive(data_copy, salt, fields_to_hash)


    if actions:

        unique_actions = [dict(t) for t in {tuple(d.items()) for d in actions}]
        sanitized_data['sanitization_info'] = unique_actions

    return sanitized_data
