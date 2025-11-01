# S1-10: Agregación Parquet (Analytics)

## Descripción

S1-10 implementa la conversión automática de logs JSONL a formato Parquet para análisis eficiente de datos. Este sistema permite agregar eventos por run_id y generar archivos Parquet optimizados para análisis con pandas/pyarrow.

## Características Implementadas

### 🔄 Conversión JSONL → Parquet
- **Conversión individual**: Un archivo JSONL → un archivo Parquet
- **Conversión por directorio**: Todos los JSONL de un directorio
- **Agregación por run**: Combinar eventos de múltiples archivos JSONL filtrados por run_id

### 📊 Funcionalidades Analytics
- Preservación de estructuras nested JSON
- Optimización con pyarrow backend
- Compresión automática de archivos Parquet
- Validación de datos durante conversión

### 🛠️ CLI Completa
```bash
# Convertir archivo individual
python src/utils/jsonl_to_parquet.py file input.jsonl output.parquet

# Convertir directorio completo
python src/utils/jsonl_to_parquet.py directory logs/events analytics/parquet

# Agregar por run_id (funcionalidad principal S1-10)
python src/utils/jsonl_to_parquet.py aggregate run-baseline-001
```

## Uso Básico

### 1. Conversión Manual
```python
from utils.jsonl_to_parquet import convert_jsonl_to_parquet

# Convertir un archivo JSONL a Parquet
convert_jsonl_to_parquet(
    "logs/events/events_20251101.jsonl",
    "analytics/parquet/events_20251101.parquet"
)
```

### 2. Agregación por Run (Principal S1-10)
```python
from utils.jsonl_to_parquet import aggregate_analytics_run

# Agregar todos los eventos de un run específico
parquet_file = aggregate_analytics_run(
    run_id="baseline-run-001",
    events_dir="logs/events",
    output_dir="analytics/parquet"
)
# Resultado: analytics/parquet/run_baseline-run-001.parquet
```

### 3. Análisis con Pandas
```python
import pandas as pd

# Leer archivo Parquet para análisis
df = pd.read_parquet("analytics/parquet/run_baseline-run-001.parquet")

# Análisis básico
print(f"Total events: {len(df)}")
print(f"Unique problems: {df['problem_id'].nunique()}")

# Análisis de tokens
if 'tokens' in df.columns:
    total_tokens = df['tokens'].apply(lambda x: x.get('total_tokens', 0)).sum()
    print(f"Total tokens: {total_tokens:,}")

# Análisis de costos
if 'estimated_cost_usd' in df.columns:
    total_cost = df['estimated_cost_usd'].sum()
    print(f"Total cost: ${total_cost:.4f}")
```

## Integración con Baseline Runner

### Demo Completo S1-10
```bash
# Ejecutar baseline con conversión automática a Parquet
python demo_s1_10_analytics.py --problems 10

# Analizar archivo Parquet existente
python demo_s1_10_analytics.py --analyze analytics/parquet/run_baseline-001.parquet
```

### Workflow Automatizado
```python
from demo_s1_10_analytics import run_baseline_with_analytics

# Ejecutar baseline + conversión automática
parquet_file = run_baseline_with_analytics(
    n_problems=200,
    model="gpt-4",
    auto_convert=True
)
```

## Estructura de Archivos

```
analytics/
└── parquet/
    ├── .gitkeep
    ├── events_20251101.parquet          # Conversión directa
    ├── run_baseline-001.parquet         # Agregación por run_id
    └── run_tas-experiment-001.parquet   # Futuras agregaciones T-A-S
```

## Esquema de Datos Parquet

Los archivos Parquet mantienen la estructura completa de los eventos JSONL:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `run_id` | string | Identificador único del run |
| `problem_id` | string | ID del problema (ej: gsm8k-001) |
| `phase` | string | Fase del experimento (baseline, tas, etc.) |
| `timestamp` | string | ISO timestamp del evento |
| `model` | string | Modelo LLM utilizado |
| `tokens` | struct | Estructura con prompt_tokens, completion_tokens, total_tokens |
| `estimated_cost_usd` | double | Costo estimado en USD |
| `sanitization_info` | array | Metadata de sanitización aplicada |

## Ventajas del Formato Parquet

### 🚀 Performance
- **Lectura rápida**: 10-100x más rápido que JSONL para análisis
- **Compresión**: 70-90% menos espacio que JSONL
- **Queries columnar**: Ideal para agregaciones y filtros

### 🔍 Análisis
- **Pandas integración**: Lectura nativa con `pd.read_parquet()`
- **Schema validation**: Tipos de datos consistentes
- **Nested structures**: Soporte completo para JSON nested

### 🔧 Operacional
- **Append support**: Fácil agregación de nuevos datos
- **Metadata**: Preserva información de esquema
- **Cross-platform**: Compatible con Spark, R, Python

## Tests

El sistema incluye tests completos:

```bash
# Ejecutar tests específicos de S1-10
python -m pytest tests/test_jsonl_to_parquet.py -v

# Tests cubiertos:
# ✅ Conversión individual JSONL → Parquet
# ✅ Conversión por directorio
# ✅ Agregación por run_id
# ✅ Manejo de estructuras nested
# ✅ Archivos vacíos
```

## Criterios S1-10 Cumplidos

- ✅ **Job que convierte JSONL→Parquet por run**: `aggregate_analytics_run()`
- ✅ **Archivo `/analytics/parquet/*.parquet`**: Generación automática
- ✅ **Legible con pandas/pyarrow**: Compatibilidad completa
- ✅ **4h estimadas - José**: Implementación completa

## Próximos Pasos

S1-10 está **listo para S1-13** (McNemar + KPIs), que utilizará estos archivos Parquet para:
- Análisis estadístico baseline vs T-A-S
- Cálculo de ΔAcc y tokens
- Generación de reportes tabulares

## Comandos de Ejemplo

```bash
# Conversión básica
python src/utils/jsonl_to_parquet.py file logs/events/events_20251101.jsonl analytics/parquet/events.parquet

# Conversión masiva
python src/utils/jsonl_to_parquet.py directory logs/events analytics/parquet

# Agregación específica (S1-10 principal)
python src/utils/jsonl_to_parquet.py aggregate baseline-run-001

# Demo completo con baseline
python demo_s1_10_analytics.py --problems 5

# Análisis de resultados
python demo_s1_10_analytics.py --analyze analytics/parquet/run_baseline-001.parquet
```
