# Dialectic LLM: Tesis–Antítesis–Síntesis

Sistema de razonamiento dialéctico para mejorar la precisión de LLMs en problemas matemáticos mediante el proceso **Tesis → Antítesis → Síntesis (T-A-S)**.

## 🎯 Descripción

Este proyecto implementa un framework de razonamiento dialéctico que:
- **Thesis**: Genera una solución inicial con exploración creativa
- **Antithesis**: Critica y cuestiona la solución propuesta
- **Synthesis**: Unifica ambas perspectivas en una respuesta mejorada

**Objetivo**: Demostrar mejora estadísticamente significativa (ΔAcc ≥ +5pp con ≤2.5× tokens de generación) vs baseline en datasets matemáticos.

## 📊 Resultados Actuales (Sprint 1)

### Baseline (GSM8K)
- **Dataset**: 200 problemas GSM8K
- **Accuracy**: 82.5% (165/200 correctos)
- **Modelo**: gpt-4o-mini-2024-07-18

### T-A-S Pilot
- **Dataset**: 50 problemas GSM8K (3 comparables con baseline)
- **Accuracy**: 100% en subset comparable (3/3)
- **Sistema completo**: Implementado y funcionando end-to-end

### Análisis Estadístico (S1-13)
- **McNemar Test**: Completo y funcionando
- **KPIs**: Métricas de accuracy, tokens y costos
- **Reportes**: `/reports/s1_13_analysis_report.md`

## 🚀 Instalación

### Requisitos
- Python 3.13+
- `uv` (gestor de paquetes)

### Setup

```bash
# 1. Clonar repositorio
git clone https://github.com/This-au-Chocolat/dialectic-llm.git
cd dialectic-llm

# 2. Instalar dependencias con uv
uv sync

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tu OPENAI_API_KEY y otros parámetros
```

## 🏗️ Estructura del Proyecto

```
dialectic-llm/
├── src/
│   ├── flows/              # Prefect flows (baseline, T-A-S)
│   │   ├── baseline.py     # Flow baseline (single-call)
│   │   └── tas.py          # Flow T-A-S dialectico (k=1)
│   ├── utils/              # Utilidades compartidas
│   │   ├── data_utils.py   # Carga de datos GSM8K consolidada
│   │   ├── parquet_utils.py # Creación de Parquet consolidada
│   │   ├── prompt_utils.py  # Templating y hashing (S1-16)
│   │   ├── sanitize.py     # Sanitización y anonimización
│   │   ├── log_utils.py    # Logging JSONL
│   │   └── tokens.py       # Conteo de tokens
│   ├── eval/               # Evaluación
│   └── agents/             # (Futuro: MAMV, k=2)
├── configs/
│   └── model.yaml          # Configuración de modelos
├── prompts/
│   └── tas/                # Templates de prompts
│       ├── thesis.txt
│       ├── antithesis.txt
│       └── synthesis.txt
├── logs/
│   └── events/             # JSONL compartidos (sanitizados)
├── logs_local/             # JSONL locales con CoT (gitignored)
├── analytics/
│   └── parquet/            # Datasets para análisis
├── tests/                  # 81 tests unitarios
└── reports/                # Análisis y documentación
```

## 🎮 Uso

### 1. Ejecutar Baseline

```bash
# Ejecutar baseline en 200 problemas GSM8K
uv run python -m src.flows.baseline --n 200 --seed 42

# Resultados en:
# - logs/events/baseline_*.jsonl
# - analytics/parquet/baseline_*.parquet
```

### 2. Ejecutar T-A-S Flow

```bash
# Ejecutar T-A-S en N problemas
uv run python -m src.flows.tas --n 50 --seed 42

# Resultados en:
# - logs/events/tas_*.jsonl (sanitizados)
# - logs_local/tas_*.jsonl (con CoT completo)
# - analytics/parquet/tas_*.parquet
```

### 3. Análisis Estadístico

```bash
# Ejecutar McNemar test y KPIs
uv run python run_s1_13_analysis.py

# Genera: reports/s1_13_analysis_report.md
```

## 🧪 Tests

```bash
# Ejecutar todos los tests
uv run pytest tests/

# Tests específicos
uv run pytest tests/test_prompt_utils.py -v
uv run pytest tests/test_data_utils.py -v

# Con cobertura
uv run pytest tests/ --cov=src --cov-report=html
```

**Estado actual**: 81/81 tests pasando ✅

## 🔐 Seguridad y Privacidad

### Chain-of-Thought (CoT)
- ⚠️ **NUNCA** se comparten los logs con CoT completo
- CoT solo en `logs_local/` (gitignored)
- Logs compartidos en `logs/events/` están sanitizados

### Sanitización
- PII detectado y redactado (emails, teléfonos, SSN, etc.)
- Prompts y respuestas hasheados (`prompt_hash`, `response_hash`)
- Whitelist estricta de campos permitidos

### Seguridad de Costos
- Límite de $5 por ejecución
- Alertas antes de exceder presupuesto
- Conteo de tokens automático

## 📚 Features Implementados (Sprint 1)

### ✅ Infraestructura (S1-01 a S1-05)
- [x] Repo con `uv` y estructura de carpetas
- [x] CI/CD con GitHub Actions (lint + tests)
- [x] Loader GSM8K + normalización
- [x] Evaluador exact-match
- [x] Contador de tokens

### ✅ Flows Prefect (S1-06 a S1-08)
- [x] Baseline runner (≥200 problemas)
- [x] T-A-S núcleo con control de temperatura
- [x] Orquestación Prefect T→A→S (k=1)

### ✅ Logging y Analytics (S1-09 a S1-10)
- [x] Logger JSONL + sanitización
- [x] Agregación a Parquet

### ✅ Testing y Ejecución (S1-11 a S1-12)
- [x] 81 unit tests (cobertura crítica)
- [x] Pilot run T-A-S (~50 problemas)

### ✅ Análisis (S1-13)
- [x] McNemar test baseline vs T-A-S
- [x] KPIs (accuracy, tokens, costos)

### ✅ Documentación (S1-14 a S1-16)
- [x] README actualizado
- [x] Reporte Sprint 1
- [x] Templating de prompts + hashing (S1-16)

## � Features Implementados (Sprint 2)

### ✅ Robustez y Escalado (S2-01)
- [x] Retry logic con exponential backoff (1s→2s→4s)
- [x] Rate limit detection y manejo
- [x] Prefect flow enhancements

### ✅ Dataset Versioning (S2-04)
- [x] 200 problem IDs from S1 baseline (seed=42)
- [x] Content hash verification (3f35ab4bbd)
- [x] 1-to-1 statistical comparison support

### ✅ Coherencia Semántica (S2-07)
- [x] SentenceTransformer embeddings (all-mpnet-base-v2)
- [x] Coherence scoring (Thesis→Synthesis)
- [x] Cosine similarity calculations

### ✅ Budget Monitoring (S2-09)
- [x] Token cap per item (≤8k tokens)
- [x] Budget alerts at 90% threshold
- [x] Cost tracking vs baseline (≤1.5× target)
- [x] Real-time projections

## ️ Características Técnicas

### Budget Monitoring y Token Caps (S2-09)
```python
from src.utils.budget_monitor import (
    calculate_budget_status,
    should_alert_budget,
    format_budget_alert,
    load_baseline_stats_from_parquet
)

# Cargar baseline
baseline = load_baseline_stats_from_parquet("analytics/parquet/baseline_200.parquet")

# Calcular status actual
status = calculate_budget_status(
    run_id="s2-tas-k1",
    processed_results=results,
    total_items=200,
    budget_limit_usd=60.0,
    baseline_stats=baseline
)

# Verificar alertas
if should_alert_budget(status):
    print(format_budget_alert(status))

# Verificar objetivo ≤1.5× baseline
if status.is_within_budget_target():
    print("✅ Within target")
```

### Prompt Templating y Hashing (S1-16)
```python
from src.utils.prompt_utils import (
    hash_prompt,
    hash_response,
    create_prompt,
    list_templates
)

# Crear prompt desde template
prompt = create_prompt("tas_thesis", {"question": "What is 2 + 2?"})

# Generar hashes (SHA-256)
prompt_hash = hash_prompt(prompt)
response_hash = hash_response("The answer is 4")

# Templates disponibles
templates = list_templates()
# ['baseline_gsm8k', 'tas_thesis', 'tas_antithesis', 'tas_synthesis']
```

### Consolidación de Código
- **70% reducción** en funciones de creación de Parquet
- **97% reducción** en funciones de carga de datos GSM8K
- **80% reducción** en funciones de extracción de respuestas
- Wrappers legacy para compatibilidad hacia atrás

## 📈 Próximos Pasos (Sprint 2+)

### Sprint 2 Objetivos
- [ ] Alcanzar **Éxito mínimo**: ΔAcc ≥ +5pp con ≤2.5× tokens
- [ ] McNemar p < 0.05 en ≥200 ítems
- [ ] MAMV (3 instancias) con votación mayoría
- [ ] Análisis cualitativo (taxonomía de errores)

### Features Futuras
- [ ] T-A-S con k=2 (multiple rounds)
- [ ] Soporte para TriviaQA dataset
- [ ] Métricas de coherencia T→S
- [ ] CLI avanzada
- [ ] Dashboard de visualización

## 👥 Equipo

- **This au Chocolat** - Scrum Master + Orchestration
- **Julio de Aquino** - MLE
- **José Pech** - Data / Evaluación
- **Lorena Pérez** - AI Safety & Compliance
- **Valeria Hernández** - Tech Writing

## 📝 Licencia

[Especificar licencia]

## 🔗 Referencias

- [GSM8K Dataset](https://github.com/openai/grade-school-math)
- [Prefect Documentation](https://docs.prefect.io/)
- [Paper (TBD)]

---

**Sprint 1 Status**: 16/16 tareas completadas (100%) ✅
**Last Updated**: 2025-11-18
