"""
Ejemplo de uso del sistema de logging con sanitización.
"""
import os
import json
from src.dialectic_llm.utils.logging import log_event, LOGS_DIRECTORY

# --- Datos de ejemplo ---

event_1 = {
    "event_id": "evt_12345",
    "user_id": "user-jane-doe-42",
    "action": "login_success",
    "details": {
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0"
    }
}

event_2 = {
    "event_id": "evt_67890",
    "user_id": "user-john-smith-88",
    "action": "submit_form",
    "form_data": {
        "email": "john.smith@example.com",
        "phone": "(555) 123-4567",
        "comment": "Mi número de tarjeta es 4444-5555-6666-7777 para el pago."
    }
}


# Evento con el mismo user_id que el primero para verificar consistencia del hash
event_3 = {
    "event_id": "evt_abcde",
    "user_id": "user-jane-doe-42",
    "action": "view_page",
    "page": "/dashboard"
}


def run_example():
    """Ejecuta el ejemplo de logging."""
    log_file = "demo_events.jsonl"
    log_file_path = os.path.join(LOGS_DIRECTORY, log_file)

    # Limpiar archivo de log anterior si existe
    if os.path.exists(log_file_path):
        os.remove(log_file_path)

    print(f"Usando LOG_SALT: '{os.getenv('LOG_SALT', 'default-salt-please-change-me')}'")
    print(f"Hasheando campos: {os.getenv('LOG_FIELDS_TO_SANITIZE', 'user_id,session_id,tenant_id').split(',')}\n")

    print("Registrando eventos...")
    log_event(event_1, log_file_name=log_file)
    log_event(event_2, log_file_name=log_file)
    log_event(event_3, log_file_name=log_file)
    print("Eventos registrados.")

    print(f"\n--- Contenido de '{log_file_path}' ---")
    with open(log_file_path, 'r', encoding='utf-8') as f:
        for line in f:

            parsed_json = json.loads(line.strip())
            print(json.dumps(parsed_json, indent=2, ensure_ascii=False))
            print("---")

if __name__ == "__main__":

    from dotenv import load_dotenv
    load_dotenv()



    run_example()
