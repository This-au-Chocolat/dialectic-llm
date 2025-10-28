"""
Módulo de Logging de Eventos en formato JSONL.

Este módulo proporciona una función para registrar eventos en un archivo
con formato JSON Lines (.jsonl), aplicando sanitización a cada registro.
"""

import json
import os
from typing import Dict, Any, List


from .sanitize import sanitize

# --- Configuración ---

FIELDS_TO_SANITIZE_STR = os.getenv("LOG_FIELDS_TO_SANITIZE", "user_id,session_id,tenant_id")
FIELDS_TO_HASH = [field.strip() for field in FIELDS_TO_SANITIZE_STR.split(',') if field.strip()]

LOGS_DIRECTORY = "C:\\Users\\Usuario\\Proyecto\\dialectic-llm\\logs\\events"


def log_event(record: Dict[str, Any], log_file_name: str = "events.jsonl") -> None:
    """
    Sanitiza un registro y lo escribe como una línea en un archivo JSONL.

    El registro se enriquece con un campo `sanitization_info` si se realizan
    cambios durante el proceso de sanitización.

    Args:
        record (Dict[str, Any]): El diccionario de datos del evento a registrar.
        log_file_name (str): El nombre del archivo de log. Se guardará en el
                             directorio de logs configurado.

    Raises:
        IOError: Si ocurre un problema al escribir en el archivo de log.
        TypeError: Si el registro no es un diccionario.
    """
    if not isinstance(record, dict):
        raise TypeError(f"El registro debe ser un diccionario, pero se recibió {type(record)}")

    # 1. Aplica la sanitización al registro
    sanitized_record = sanitize(
        data=record,
        salt=LOG_SALT,
        fields_to_hash=FIELDS_TO_HASH
    )

    # 2. Define la ruta completa del archivo de log
    log_file_path = os.path.join(LOGS_DIRECTORY, log_file_name)

    try:
        # 3. Escribe el evento como una línea JSON en el archivo
        # Se abre en modo apend (agregar) y se asegura el encoding UTF-8
        with open(log_file_path, 'a', encoding='utf-8') as f:
            # `ensure_ascii=False` para correcta serialización de caracteres no latinos
            json_string = json.dumps(sanitized_record, ensure_ascii=False)
            f.write(json_string + '\n')
    except IOError as e:
        # Manejo básico de errores: imprimir en stderr
        print(f"Error: No se pudo escribir en el archivo de log {log_file_path}. Detalles: {e}")

    except Exception as e:
        print(f"Un error inesperado ocurrió durante el logging: {e}")
