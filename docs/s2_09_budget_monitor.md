# S2-09: Token Caps y Budget Monitor - COMPLETADO ✅

## 📋 Resumen

**Task ID:** S2-09
**Título:** Token caps por ítem y budget monitor por sprint
**Estimación:** 4h
**Owner:** This au Chocolat
**Dependencias:** S1 tokens (✅)
**Estado:** ✅ COMPLETADO

## 🎯 Objetivos

Implementar control de costos y monitoreo de presupuesto para Sprint 2:

1. **Token cap por ítem**: Límite ≤8k tokens/problema
2. **Budget monitor**: Alertas al 90% del presupuesto
3. **Comparación vs baseline**: Verificar ≤1.5× costo baseline (generación)

## ✅ Criterios de Aceptación

- [x] Límite de 8,000 tokens por ítem implementado
- [x] Sistema de alertas al acercarse al 90% del presupuesto
- [x] Tabla de consumo comparativa vs baseline
- [x] Proyecciones de costo total basadas en progreso actual
- [x] Detección de ítems que exceden el token cap
- [x] Carga de estadísticas baseline desde Parquet

## 🏗️ Implementación

### Módulo Principal: `src/utils/budget_monitor.py`

**Clases:**

```python
@dataclass
class TokenUsage:
    """Token usage for a single item."""
    problem_id: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    phase: str = "unknown"
    model: str = "gpt-4"

@dataclass
class BudgetStatus:
    """Current budget status for a sprint run."""
    run_id: str
    total_items: int
    processed_items: int
    total_tokens: int
    total_cost_usd: float
    budget_limit_usd: float
    baseline_tokens: Optional[int] = None
    baseline_cost_usd: Optional[float] = None
    items_over_cap: List[str] = field(default_factory=list)

    # Computed properties
    @property
    def budget_used_pct(self) -> float
    @property
    def avg_tokens_per_item(self) -> float
    @property
    def projected_total_cost(self) -> float
    @property
    def tokens_vs_baseline_ratio(self) -> Optional[float]
    @property
    def cost_vs_baseline_ratio(self) -> Optional[float]
```

**Constantes:**

- `MAX_TOKENS_PER_ITEM = 8000` - Cap de tokens por problema
- `BUDGET_ALERT_THRESHOLD_PCT = 90.0` - Umbral para alertas

**Funciones Principales:**

1. `check_item_token_cap()` - Verifica si un ítem excede el cap
2. `calculate_budget_status()` - Calcula estado actual del presupuesto
3. `should_alert_budget()` - Determina si disparar alerta
4. `format_budget_alert()` - Formatea mensaje de alerta
5. `format_budget_summary()` - Genera reporte de resumen
6. `create_budget_report_table()` - Tabla comparativa multi-run
7. `load_baseline_stats_from_parquet()` - Carga stats desde Parquet

## 🧪 Testing

**Archivo:** `tests/test_budget_monitor.py`
**Tests:** 16 pruebas (100% passing)

### Cobertura de Tests

- ✅ Creación de `TokenUsage`
- ✅ Verificación de token cap (dentro/fuera)
- ✅ Propiedades calculadas de `BudgetStatus`
- ✅ Cálculo de budget status básico
- ✅ Cálculo con comparación vs baseline
- ✅ Detección de ítems sobre el cap
- ✅ Alertas por umbral (90%)
- ✅ Alertas por proyección
- ✅ Formato de alertas
- ✅ Formato de resúmenes
- ✅ Tabla comparativa multi-run
- ✅ Casos edge (sin baseline, lista vacía)
- ✅ Constantes configuradas correctamente

```bash
$ pytest tests/test_budget_monitor.py -v
====================== 16 passed in 0.27s ======================
```

## 📊 Demo

**Script:** `demo_s2_09_budget.py`

El demo demuestra:

1. **Token Cap**: Verificación de ítems que exceden 8k tokens
2. **Monitoreo**: Progreso con alertas en tiempo real
3. **Alertas**: Formato de mensajes de alerta al 90%
4. **Resúmenes**: Reportes completos con comparación baseline
5. **Comparación**: Tabla multi-run (baseline vs TAS vs MAMV)
6. **Integración**: Carga de stats desde Parquet

### Ejemplo de Output

```
1. TOKEN CAP PER ITEM (≤8k tokens)
Configured cap: 8,000 tokens/item

problem-001: 5,000 tokens ($0.3500) - ✅ Within cap
problem-002: 7,500 tokens ($0.5500) - ✅ Within cap
problem-003: 9,000 tokens ($0.7000) - ❌ EXCEEDS CAP

2. BUDGET MONITORING & ALERTS
After 90 items:
  Tokens: 549,900
  Cost: $38.49
  Budget used: 64.2%
  Projected total: $85.54
  vs Baseline: 1.37×
  ⚠️  Items over cap: 4
  🚨 ALERT TRIGGERED!

3. BUDGET ALERT FORMAT
⚠️  BUDGET ALERT
Run ID: s2-tas-k1-20251119
Progress: 150/200 items

Current Usage:
  Tokens: 825,000
  Cost: $55.0000
  Budget: $60.00
  Used: 91.7%

Projections:
  Est. total cost: $73.3333
  Avg tokens/item: 5500

vs Baseline:
  Token ratio: 2.06×
  Cost ratio: 1.96×
  Target: ≤1.5×

Items over 8,000 token cap: 3
  gsm8k-042, gsm8k-089, gsm8k-127
```

## 🔧 Uso

### 1. Verificar Token Cap de un Ítem

```python
from src.utils.budget_monitor import TokenUsage, check_item_token_cap

usage = TokenUsage(
    problem_id="gsm8k-001",
    prompt_tokens=3000,
    completion_tokens=4500,
    total_tokens=7500,
    estimated_cost_usd=0.55
)

if not check_item_token_cap(usage):
    print(f"⚠️  Problem {usage.problem_id} exceeds token cap!")
```

### 2. Calcular Budget Status

```python
from src.utils.budget_monitor import calculate_budget_status

# Tus resultados procesados
results = [
    {
        "problem_id": "gsm8k-001",
        "tas_usage": {"total_tokens": 5000},
        "estimated_cost_usd": 0.35
    },
    # ... más resultados
]

# Stats del baseline (opcional)
baseline = {
    "total_tokens": 400000,
    "total_cost_usd": 28.0
}

status = calculate_budget_status(
    run_id="s2-tas-k1",
    processed_results=results,
    total_items=200,
    budget_limit_usd=60.0,
    baseline_stats=baseline
)

print(f"Budget used: {status.budget_used_pct:.1f}%")
print(f"Cost vs baseline: {status.cost_vs_baseline_ratio:.2f}×")
```

### 3. Monitorear y Alertar

```python
from src.utils.budget_monitor import should_alert_budget, format_budget_alert

if should_alert_budget(status):
    alert = format_budget_alert(status)
    print(alert)
    # Aquí podrías enviar notificación, log, etc.
```

### 4. Generar Reporte Final

```python
from src.utils.budget_monitor import format_budget_summary

summary = format_budget_summary(status)
print(summary)

# Verificar objetivo de costo
if status.is_within_budget_target(target_multiplier=1.5):
    print("✅ Within ≤1.5× baseline target")
else:
    print("❌ Exceeds 1.5× baseline target")
```

### 5. Comparar Múltiples Runs

```python
from src.utils.budget_monitor import create_budget_report_table

runs = [baseline_status, tas_status, mamv_status]
table = create_budget_report_table(runs)
print(table)
```

### 6. Cargar Baseline desde Parquet

```python
from src.utils.budget_monitor import load_baseline_stats_from_parquet

baseline = load_baseline_stats_from_parquet(
    "analytics/parquet/baseline_200.parquet"
)

print(f"Baseline: {baseline['total_tokens']:,} tokens, ${baseline['total_cost_usd']:.2f}")
```

## 📈 Integración con Flows

El budget monitor se integrará con los flows de ejecución (S2-05, S2-06):

```python
# En run_tas_gsm8k o run_mamv_gsm8k
from src.utils.budget_monitor import (
    calculate_budget_status,
    should_alert_budget,
    format_budget_alert,
    load_baseline_stats_from_parquet
)

# Cargar baseline al inicio
baseline = load_baseline_stats_from_parquet("analytics/parquet/s1_baseline_200.parquet")

# Durante ejecución, revisar periódicamente
for i, batch in enumerate(problem_batches):
    results.extend(process_batch(batch))

    # Check cada N items
    if i % 10 == 0:
        status = calculate_budget_status(
            run_id=run_id,
            processed_results=results,
            total_items=total_items,
            budget_limit_usd=max_cost_usd,
            baseline_stats=baseline
        )

        if should_alert_budget(status):
            print(format_budget_alert(status))

            # Decidir si continuar o detener
            if status.projected_total_cost > max_cost_usd * 1.2:
                raise RuntimeError("Projected cost exceeds 120% of budget!")
```

## 🎯 Métricas de Éxito

### Sprint 2 Goals

- ✅ **Token cap**: 8,000 tokens/problema (documentado y testeado)
- ✅ **Alertas**: Umbral de 90% implementado
- ✅ **Target**: Comparación vs baseline ≤1.5× (verificable)
- ✅ **Monitoreo**: Real-time con proyecciones
- ✅ **Reportes**: Tablas comparativas multi-run

### Validación Técnica

- ✅ 16/16 tests passing
- ✅ Demo funcional ejecutado exitosamente
- ✅ Integración con sistema de tokens existente (S1-05)
- ✅ Carga de Parquet para baseline stats
- ✅ Documentación completa

## 🔄 Próximos Pasos

Con S2-09 completado, ahora se puede:

1. **S2-05**: Ejecutar T-A-S (k=1) en ≥200 con logging
   - Usar `calculate_budget_status()` durante ejecución
   - Alertar si se acerca al límite

2. **S2-06**: Ejecutar T-A-S+MAMV en ≥200
   - Mismo monitoreo pero con 3× tokens (9 llamadas)
   - Verificar cumplimiento de ≤1.5× baseline

3. **S2-10**: McNemar y KPIs
   - Usar `create_budget_report_table()` para tabla final
   - Incluir en `reports/Sprint2.md`

## 📝 Archivos Modificados/Creados

### Nuevos
- ✅ `src/utils/budget_monitor.py` (370 líneas)
- ✅ `tests/test_budget_monitor.py` (16 tests)
- ✅ `demo_s2_09_budget.py` (demo completo)
- ✅ `docs/s2_09_budget_monitor.md` (este archivo)

### Sin Modificar
- `src/utils/tokens.py` - Se reutiliza tal cual (S1-05)
- `src/flows/tas.py` - Se integrará en S2-05/S2-06

## 🏆 Conclusión

**S2-09 está COMPLETO** y listo para producción. El sistema de budget monitoring:

- ✅ Previene runaway costs con token caps
- ✅ Alerta temprana al 90% del presupuesto
- ✅ Verifica cumplimiento del objetivo ≤1.5× baseline
- ✅ Proporciona visibilidad en tiempo real
- ✅ Genera reportes comparativos para Sprint2.md

**Dependencias resueltas:** S2-05, S2-06, S2-10 ahora pueden avanzar con seguridad de costos.
