"""
Ejemplo de uso del sistema de logging con sanitización.
Integrado con el sistema dialectic-llm.
"""

import json
import os

from src.utils.log_utils import log_event

# --- Datos de ejemplo ---

event_1 = {
    "event_id": "evt_12345",
    "user_id": "user-jane-doe-42",
    "action": "login_success",
    "details": {"ip_address": "192.168.1.100", "user_agent": "Mozilla/5.0"},
}

event_2 = {
    "event_id": "evt_67890",
    "user_id": "user-john-smith-88",
    "action": "submit_form",
    "form_data": {
        "email": "john.smith@example.com",
        "phone": "(555) 123-4567",
        "comment": "Mi número de tarjeta es 4444-5555-6666-7777 para el pago.",
    },
}

# Evento con el mismo user_id que el primero para verificar consistencia del hash
event_3 = {
    "event_id": "evt_abcde",
    "user_id": "user-jane-doe-42",
    "action": "view_page",
    "page": "/dashboard",
}


def run_example():
    """Ejecuta el ejemplo de logging."""
    log_dir = "logs/events"
    log_file = "demo_events.jsonl"

    # Crear directorio si no existe
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, log_file)

    # Limpiar archivo de log anterior si existe
    if os.path.exists(log_file_path):
        os.remove(log_file_path)

    print(f"Usando SANITIZE_SALT: '{os.getenv('SANITIZE_SALT', 'dialectic-llm-default-salt')}'")
    fields_env = os.getenv("LOG_FIELDS_TO_SANITIZE", "user_id,session_id,tenant_id")
    print(f"Hasheando campos: {fields_env.split(',')}\n")

    print("Registrando eventos...")
    log_event(event_1, log_file_name=log_file)
    log_event(event_2, log_file_name=log_file)
    log_event(event_3, log_file_name=log_file)
    print("Eventos registrados.")

    # Buscar el archivo actual (con timestamp)
    from datetime import datetime

    date_str = datetime.utcnow().strftime("%Y%m%d")
    actual_file = f"{log_dir}/events_{date_str}.jsonl"

    if os.path.exists(actual_file):
        print(f"\n--- Contenido de '{actual_file}' ---")
        with open(actual_file, "r", encoding="utf-8") as f:
            for line in f:
                parsed_json = json.loads(line.strip())
                print(json.dumps(parsed_json, indent=2, ensure_ascii=False))
                print("---")
    else:
        print(f"No se encontró el archivo de log: {actual_file}")


if __name__ == "__main__":
    # Set environment variables for testing
    os.environ.setdefault("SANITIZE_SALT", "test-salt-for-demo")
    os.environ.setdefault("LOG_FIELDS_TO_SANITIZE", "user_id,session_id,tenant_id")

    run_example()
