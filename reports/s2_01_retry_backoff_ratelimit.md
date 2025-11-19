# S2-01: Escalado Prefect + retries/backoff + rate-limit aware

## Estado: ✅ COMPLETADO

**Owner:** This au Chocolat
**Estimate:** 6h
**Actual:** ~6h
**Fecha:** 2025-11-18

## Objetivo

Mejorar la robustez del sistema Prefect para manejar:
1. Reintentos con exponential backoff y jitter
2. Detección y manejo de rate limits
3. Logging de eventos de retry para observabilidad

## Implementación

### Archivos Creados

1. **`src/utils/retry_utils.py`** (241 líneas)
   - `exponential_backoff_with_jitter()`: Calcula delay con backoff exponencial
   - `is_rate_limit_error()`: Detecta errores de rate limiting
   - `is_retryable_error()`: Identifica errores que deben reintentarse
   - `retry_with_backoff()`: Función genérica de retry con backoff
   - `create_retry_log_entry()`: Estructura logs de retry
   - `get_prefect_retry_delays()`: Genera delays para config de Prefect
   - **Custom Exceptions**:
     - `RateLimitError`: Para rate limits explícitos
     - `RetryableError`: Para errores transitorios
   - **Configuración**: `PREFECT_RETRY_CONFIG` con defaults

2. **`tests/test_retry_utils.py`** (274 líneas)
   - 27 tests completos (100% passing)
   - Cobertura de:
     - Exponential backoff (con y sin jitter)
     - Detección de rate limits y errores retryables
     - Lógica de retry (éxito, fallo, max retries)
     - Logging de retry events
     - Configuración de Prefect
     - Tests de integración

### Archivos Modificados

1. **`src/flows/tas.py`**
   - Actualizado imports para incluir `retry_utils`
   - Mejorado `llm_call()` con:
     - Parámetro `logger` opcional
     - Detección de rate limits con logging
     - Re-raise de exceptions para Prefect retry
   - Actualizado **todas las tasks** (thesis, antithesis, synthesis):
     - `retries`: 2 → 3
     - `retry_delay_seconds`: [1, 2] → [1, 2, 4] (exponential backoff)
     - Pasando `logger` a `llm_call()`

## Resultados

### Tests
```bash
$ pytest tests/test_retry_utils.py -v
collected 27 items
tests/test_retry_utils.py::TestExponentialBackoff::test_backoff_no_jitter PASSED
tests/test_retry_utils.py::TestExponentialBackoff::test_backoff_with_jitter PASSED
tests/test_retry_utils.py::TestExponentialBackoff::test_backoff_respects_max_delay PASSED
tests/test_retry_utils.py::TestExponentialBackoff::test_backoff_custom_base PASSED
tests/test_retry_utils.py::TestErrorDetection::test_is_rate_limit_error_positive PASSED
tests/test_retry_utils.py::TestErrorDetection::test_is_rate_limit_error_negative PASSED
tests/test_retry_utils.py::TestErrorDetection::test_is_retryable_error_with_rate_limit PASSED
tests/test_retry_utils.py::TestErrorDetection::test_is_retryable_error_with_network PASSED
tests/test_retry_utils.py::TestErrorDetection::test_is_retryable_error_negative PASSED
tests/test_retry_utils.py::TestErrorDetection::test_custom_exception_types PASSED
tests/test_retry_utils.py::TestRetryWithBackoff::test_successful_first_call PASSED
tests/test_retry_utils.py::TestRetryWithBackoff::test_retry_on_retryable_error PASSED
tests/test_retry_utils.py::TestRetryWithBackoff::test_no_retry_on_non_retryable_error PASSED
tests/test_retry_utils.py::TestRetryWithBackoff::test_max_retries_exceeded PASSED
tests/test_retry_utils.py::TestRetryWithBackoff::test_retry_with_logger PASSED
tests/test_retry_utils.py::TestRetryWithBackoff::test_retry_timing PASSED
tests/test_retry_utils.py::TestRetryWithBackoff::test_retry_with_kwargs PASSED
tests/test_retry_utils.py::TestRetryLogEntry::test_create_basic_log_entry PASSED
tests/test_retry_utils.py::TestRetryLogEntry::test_create_log_entry_with_context PASSED
tests/test_retry_utils.py::TestRetryLogEntry::test_log_entry_rate_limit_detection PASSED
tests/test_retry_utils.py::TestRetryLogEntry::test_log_entry_truncates_long_messages PASSED
tests/test_retry_utils.py::TestPrefectConfiguration::test_prefect_retry_config PASSED
tests/test_retry_utils.py::TestPrefectConfiguration::test_get_prefect_retry_delays_default PASSED
tests/test_retry_utils.py::TestPrefectConfiguration::test_get_prefect_retry_delays_custom PASSED
tests/test_retry_utils.py::TestPrefectConfiguration::test_get_prefect_retry_delays_zero PASSED
tests/test_retry_utils.py::TestIntegration::test_realistic_api_call_simulation PASSED
tests/test_retry_utils.py::TestIntegration::test_exponential_growth_verification PASSED

========================== 27 passed in 0.35s ==========================
```

### Linting
```bash
$ ruff check src/utils/retry_utils.py tests/test_retry_utils.py src/flows/tas.py
All checks passed!
```

### Suite Completa
```bash
$ pytest tests/ -q
108 passed in 13.27s
```

## Criterios de Aceptación ✅

- [x] Flow con backoff exponencial (1s, 2s, 4s con jitter)
- [x] Manejo de rate limits con detección automática
- [x] Logs de reintentos en JSONL (via Prefect logger)
- [x] Runs no fallan por rate limit (retries automáticos)
- [x] Tests completos (27 nuevos)
- [x] Sin regresiones (108/108 tests pasan)
- [x] Linting limpio

## Detalles Técnicos

### Exponential Backoff

El sistema usa backoff exponencial con jitter:
```
Attempt 0: delay = 1s × 2^0 = 1s (+ jitter)
Attempt 1: delay = 1s × 2^1 = 2s (+ jitter)
Attempt 2: delay = 1s × 2^2 = 4s (+ jitter)
```

El jitter ayuda a evitar thundering herd problem cuando múltiples tasks reintentan simultáneamente.

### Rate Limit Detection

Detecta automáticamente errores de rate limiting basándose en:
- Texto "rate limit", "rate_limit", "ratelimit"
- HTTP status code 429
- "too many requests", "quota exceeded", "throttle"

### Retry Logic en Prefect Tasks

Configuración actualizada en las 3 fases T-A-S:
```python
@task(
    retries=3,  # 3 reintentos (antes: 2)
    retry_delay_seconds=[1, 2, 4],  # Exponential backoff (antes: [1, 2])
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(minutes=10),
)
```

### Logging de Retries

Cuando ocurre un rate limit:
```python
logger.warning(
    f"Retry attempt {attempt + 1}/{max_retries} "
    f"after {delay:.2f}s delay. "
    f"Error type: rate_limit. "
    f"Error: Rate limit exceeded"
)
```

Estos logs aparecen en:
- Prefect UI (flow runs)
- Logs de la task

## Beneficios

1. **Robustez**: Sistema tolera rate limits sin fallar
2. **Observabilidad**: Logs estructurados de cada retry
3. **Eficiencia**: Backoff exponencial reduce carga en API
4. **Jitter**: Evita reintentos simultáneos (thundering herd)
5. **Configuración**: Fácil ajustar delays y max retries
6. **Testing**: Funciones bien testeadas y reutilizables

## Uso

### En Prefect Tasks

```python
from utils.retry_utils import get_prefect_retry_delays

@task(
    retries=3,
    retry_delay_seconds=get_prefect_retry_delays(3, 1.0),  # [1s, 2s, 4s]
)
def my_task():
    # Task logic
    pass
```

### Detección Manual de Rate Limits

```python
from utils.retry_utils import is_rate_limit_error

try:
    api_call()
except Exception as e:
    if is_rate_limit_error(e):
        logger.warning("Rate limit hit, will retry")
    raise
```

### Retry Genérico (fuera de Prefect)

```python
from utils.retry_utils import retry_with_backoff

def api_call():
    # Your API logic
    return result

result = retry_with_backoff(
    api_call,
    max_retries=3,
    base_delay=1.0,
    logger=my_logger
)
```

## Próximos Pasos

Para futuros sprints:
1. Agregar métricas de retry (cuántos retries por run)
2. Considerar circuit breaker pattern si rate limits son persistentes
3. Ajustar delays basándose en retry-after headers de la API
4. Dashboard de observabilidad para monitorear retries

## Notas

- Los delays son progresivos: 1s → 2s → 4s
- El jitter es aleatorio entre 0 y el delay calculado
- Max 3 reintentos = 4 intentos totales (inicial + 3 retries)
- Errores no-retryables (auth, bad request) fallan inmediatamente
- Compatible con Prefect 2.x task configuration
