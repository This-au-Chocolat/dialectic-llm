# Baseline Runner - S1-06

Este documento explica cómo usar el baseline runner para ejecutar evaluaciones en ≥200 problemas GSM8K.

## Configuración

1. **Configurar variables de entorno:**
```bash
cp .env.example .env
# Editar .env con tu API key de OpenAI
```

2. **Instalar dependencias:**
```bash
uv sync
```

## Uso Básico

### Corrida de prueba (5 problemas)
```python
from flows.baseline import run_baseline_gsm8k

# Prueba pequeña (~$0.06)
result = run_baseline_gsm8k(n_problems=5, model="gpt-4")
print(f"Accuracy: {result['accuracy']:.3f}")
```

### Corrida completa S1-06 (200 problemas)
```python
# Corrida completa para S1-06 (~$2.40)
result = run_baseline_gsm8k(n_problems=200, seed=42, model="gpt-4")
```

### Usando Prefect CLI
```bash
# Configurar servidor local de Prefect
prefect server start

# En otra terminal
python -c "from flows.baseline import run_baseline_gsm8k; run_baseline_gsm8k(n_problems=200)"
```

## Artefactos Generados

### 1. Logs JSONL (`/logs/events/`)
Eventos sanitizados por día:
```
logs/events/events_20241027.jsonl
```

Cada línea contiene:
```json
{
  "run_id": "baseline_20241027_143052_a1b2c3d4",
  "problem_id": "gsm8k_0001",
  "dataset": "gsm8k",
  "phase": "baseline",
  "model": "gpt-4",
  "is_correct": true,
  "tokens": {
    "prompt_tokens": 95,
    "completion_tokens": 142,
    "total_tokens": 237
  },
  "estimated_cost_usd": 0.0139,
  "timestamp": "2024-10-27T14:30:52.123456Z"
}
```

### 2. Resultados Parquet (`/analytics/parquet/`)
Archivo agregado para análisis:
```
analytics/parquet/baseline_20241027_143052_a1b2c3d4.parquet
```

Columnas:
- `run_id`, `problem_id`, `dataset`, `phase`, `model`
- `is_correct`, `true_answer`, `predicted_answer_raw`
- `has_error`, `prompt_tokens`, `completion_tokens`, `total_tokens`

### 3. Resumen de corrida (`/logs/events/`)
```
logs/events/summary_baseline_20241027_143052_a1b2c3d4.json
```

## Controles de Costo

### Límites automáticos
- **Máximo por corrida:** $50 USD
- **Máximo por ítem:** 8,000 tokens
- **Parada automática** si se exceden límites

### Estimaciones
- **5 problemas:** ~$0.06
- **50 problemas:** ~$0.60
- **200 problemas:** ~$2.40 (S1-06)

## Monitoreo

### Durante la ejecución
```
Starting baseline run: baseline_20241027_143052_a1b2c3d4
Problems: 200, Model: gpt-4, Seed: 42
Loading GSM8K problems...
Loaded 200 problems
Solving problems...
Solving problem 1/200: gsm8k_0000
Solving problem 2/200: gsm8k_0001
...
Completed 200 problems
Accuracy: 0.847 (169/200)
Errors: 3
Estimated cost: $2.34
Results saved to: analytics/parquet/baseline_20241027_143052_a1b2c3d4.parquet
```

### Después de la ejecución
```python
import pandas as pd

# Cargar resultados
df = pd.read_parquet("analytics/parquet/baseline_20241027_143052_a1b2c3d4.parquet")

# Análisis básico
print(f"Accuracy: {df['is_correct'].mean():.3f}")
print(f"Total tokens: {df['total_tokens'].sum():,}")
print(f"Avg tokens per problem: {df['total_tokens'].mean():.1f}")
print(f"Errors: {df['has_error'].sum()}")
```

## Solución de Problemas

### Error: API key no configurada
```
ValueError: OpenAI API key is required. Set OPENAI_API_KEY environment variable.
```
**Solución:** Configurar `OPENAI_API_KEY` en el archivo `.env`

### Error: Rate limit
El sistema tiene reintentos automáticos, pero si persiste:
- Reducir `n_problems`
- Esperar unos minutos
- Verificar límites de tu cuenta OpenAI

### Error: Costo excedido
```
WARNING: Cost limit reached ($50.00). Stopping at 150 problems.
```
**Normal:** El sistema para automáticamente para evitar gastos excesivos.

## Próximos Pasos

Una vez completado S1-06:
1. **S1-10:** Usar los Parquet generados para análisis
2. **S1-13:** Comparar baseline vs T-A-S con McNemar
3. **S2:** Escalado con retry/backoff y control de rate-limits
