# S1-16: Templating de prompts + hashing de prompt/resp

## Estado: ✅ COMPLETADO

**Owner:** Julio de Aquino
**Estimate:** 3h
**Actual:** ~3h
**Fecha:** 2025-10-26

## Objetivo

Crear funciones utilitarias para:
1. Templating de prompts con variables
2. Hashing consistente de prompts y respuestas
3. Integración en el flujo T-A-S

## Implementación

### Archivos Creados

1. **`src/utils/prompt_utils.py`** (165 líneas)
   - `hash_prompt(prompt: str) -> str`: SHA-256 hash de prompts
   - `hash_response(response: str) -> str`: SHA-256 hash de respuestas
   - `hash_dict(data: Dict) -> str`: Hash de diccionarios (order-independent)
   - `create_prompt(template_name, variables, custom_template)`: Crear prompts desde templates
   - `register_template(name, template)`: Registrar nuevos templates
   - `get_template(name)`: Obtener template por nombre
   - `list_templates()`: Listar todos los templates disponibles
   - **Templates incluidos:**
     - `baseline_gsm8k`: Prompt para baseline
     - `tas_thesis`: Prompt para fase Thesis
     - `tas_antithesis`: Prompt para fase Antithesis
     - `tas_synthesis`: Prompt para fase Synthesis

2. **`tests/test_prompt_utils.py`** (249 líneas)
   - 26 tests completos (100% passing)
   - Cobertura de:
     - Hashing functions (consistency, unicode, empty strings)
     - Template creation (all phases)
     - Template registry (register, get, list)
     - Integration (full T-A-S workflow simulation)

### Archivos Modificados

1. **`src/flows/tas.py`**
   - Removida función local `hash_text()`
   - Importado `hash_prompt, hash_response` desde `utils.prompt_utils`
   - Cambiados todos los logs para usar:
     - `prompt_hash` (en lugar de `prompt_h`)
     - `response_hash` (en lugar de `answer_hash`, `critique_hash`, `final_hash`)
   - Afecta funciones: `thesis()`, `antithesis()`, `synthesis()`

## Resultados

### Tests
```bash
$ pytest tests/test_prompt_utils.py -v
collected 26 items
tests/test_prompt_utils.py::TestHashingFunctions::test_hash_prompt_basic PASSED
tests/test_prompt_utils.py::TestHashingFunctions::test_hash_prompt_consistency PASSED
tests/test_prompt_utils.py::TestHashingFunctions::test_hash_prompt_different_inputs PASSED
tests/test_prompt_utils.py::TestHashingFunctions::test_hash_response_basic PASSED
tests/test_prompt_utils.py::TestHashingFunctions::test_hash_response_consistency PASSED
tests/test_prompt_utils.py::TestHashingFunctions::test_hash_response_different_inputs PASSED
tests/test_prompt_utils.py::TestHashingFunctions::test_hash_dict_basic PASSED
tests/test_prompt_utils.py::TestHashingFunctions::test_hash_dict_order_independent PASSED
tests/test_prompt_utils.py::TestHashingFunctions::test_hash_dict_different_data PASSED
tests/test_prompt_utils.py::TestHashingFunctions::test_hash_empty_string PASSED
tests/test_prompt_utils.py::TestHashingFunctions::test_hash_unicode PASSED
tests/test_prompt_utils.py::TestPromptTemplating::test_create_prompt_baseline PASSED
tests/test_prompt_utils.py::TestPromptTemplating::test_create_prompt_tas_thesis PASSED
tests/test_prompt_utils.py::TestPromptTemplating::test_create_prompt_tas_antithesis PASSED
tests/test_prompt_utils.py::TestPromptTemplating::test_create_prompt_tas_synthesis PASSED
tests/test_prompt_utils.py::TestPromptTemplating::test_create_prompt_custom_template PASSED
tests/test_prompt_utils.py::TestPromptTemplating::test_create_prompt_missing_variable PASSED
tests/test_prompt_utils.py::TestPromptTemplating::test_create_prompt_invalid_template PASSED
tests/test_prompt_utils.py::TestPromptTemplating::test_register_template PASSED
tests/test_prompt_utils.py::TestPromptTemplating::test_get_template PASSED
tests/test_prompt_utils.py::TestPromptTemplating::test_get_template_not_found PASSED
tests/test_prompt_utils.py::TestPromptTemplating::test_list_templates PASSED
tests/test_prompt_utils.py::TestPromptTemplating::test_all_default_templates_exist PASSED
tests/test_prompt_utils.py::TestIntegration::test_hash_generated_prompt PASSED
tests/test_prompt_utils.py::TestIntegration::test_different_questions_different_hashes PASSED
tests/test_prompt_utils.py::TestIntegration::test_workflow_simulation PASSED

========================== 26 passed in 0.14s ==========================
```

### Linting
```bash
$ ruff check src/utils/prompt_utils.py tests/test_prompt_utils.py src/flows/tas.py
All checks passed!
```

### Suite Completa
```bash
$ pytest tests/ -v
collected 81 items
========================== 81 passed in 14.48s ==========================
```

## Criterios de Aceptación ✅

- [x] `prompt_hash` presente en logs (thesis, antithesis, synthesis)
- [x] `response_hash` presente en logs (thesis, antithesis, synthesis)
- [x] Funciones utilitarias completas y documentadas
- [x] Pruebas unitarias completas (26 tests)
- [x] Integración en flujo T-A-S existente
- [x] Linting limpio (ruff)
- [x] No se rompieron tests existentes (81 tests pasan)

## Beneficios

1. **Deduplicación**: Los hashes permiten identificar prompts/respuestas duplicadas
2. **Trazabilidad**: Cada prompt y respuesta tiene un identificador único
3. **Templating**: Sistema extensible para agregar nuevos tipos de prompts
4. **Consistencia**: Todos los prompts siguen el mismo patrón
5. **Testing**: Templates se pueden probar de forma aislada
6. **Reutilización**: Otros flujos pueden usar las mismas funciones

## Uso

```python
from src.utils.prompt_utils import (
    hash_prompt,
    hash_response,
    create_prompt,
    register_template
)

# Crear prompt desde template
prompt = create_prompt("tas_thesis", {"question": "What is 2 + 2?"})

# Generar hashes
prompt_hash = hash_prompt(prompt)
response_hash = hash_response("The answer is 4")

# Registrar template custom
register_template("custom", "Hello {name}!")
custom_prompt = create_prompt("custom", {"name": "World"})
```

## Próximos Pasos

Para futuros sprints, se puede:
1. Migrar `make_prompt_thesis/antithesis/synthesis` a usar `create_prompt()`
2. Agregar templates para otros tipos de problemas (TriviaQA, etc.)
3. Implementar caché basado en `prompt_hash` para evitar llamadas duplicadas al LLM
4. Usar `response_hash` para detectar respuestas idénticas y analizar convergencia

## Notas

- Los templates usan formato de strings multilínea para cumplir con E501 (líneas ≤100 chars)
- SHA-256 es el estándar para todos los hashes (64 chars hex)
- Los hashes son determinísticos: mismo input = mismo hash
- `hash_dict()` ordena las keys para consistencia independiente del orden de inserción
