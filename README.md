# Dialectic LLM: Tesis–Antítesis–Síntesis

Sistema de razonamiento dialéctico para evaluar su eficacia en la mejora de la precisión de LLMs en benchmarks de razonamiento, centrándose en el proceso **Tesis → Antítesis → Síntesis (T-A-S)**.

## 🎯 Descripción General del Proyecto

Este proyecto explora la hipótesis de que un framework de razonamiento dialéctico puede mejorar la capacidad de los Large Language Models (LLMs) para resolver problemas complejos. El framework opera en tres fases:
- **Thesis**: Genera una solución inicial (exploración creativa).
- **Antithesis**: Critica y cuestiona la solución propuesta.
- **Synthesis**: Unifica ambas perspectivas en una respuesta mejorada y más robusta.

**Objetivo**: Evaluar empíricamente si este método dialéctico ofrece una mejora estadísticamente significativa en la precisión (ΔAcc) y/o una mayor robustez en la resolución de problemas, considerando siempre la eficiencia en el consumo de tokens (costo de generación).

### Criterios de Éxito Mínimo (Proyecto)

Para considerar el método dialéctico exitoso, se esperaba que:
- **En al menos un dataset:** ΔAcc ≥ +5pp Y costo ≤2.5× tokens de generación.
- **En el otro dataset:** ΔAcc ≥ 0pp (no-regresión) Y `invalid/format` ≤ baseline + 2pp.

## 📊 Estado Actual y Hallazgos Clave

### GSM8K (Problemas de razonamiento matemático estructurado)

*   **Evaluación:** Realizada con 50 problemas (Sprint 2).
*   **Resultados:**
    *   **Baseline:** Alta precisión (e.g., 98% accuracy).
    *   **T-A-S (k=1):** Mostró una **disminución** de precisión (ej. -2pp accuracy) con un **incremento significativo en el costo** (ej. 16× más tokens).
    *   **T-A-S+MAMV (k=1):** No mejoró la precisión (0pp) y fue aún **más costoso** (ej. 47× más tokens).
*   **Conclusión:** El método dialéctico T-A-S **no aportó beneficios en precisión** para el dataset GSM8K, un benchmark con respuestas numéricas y directas. La narrativa honesta es que, para este tipo de problemas, el costo computacional no se justifica por una mejora en el rendimiento.

### TruthfulQA (Preguntas engañosas/ambiguas que requieren pensamiento crítico)

*   **Evaluación:** Realizada con 50 problemas (Sprint 3).
*   **Resultados:** Ambos métodos (Baseline y T-A-S) obtuvieron **0% de precisión** bajo una evaluación de `exact-match` estricta. T-A-S incurrió en **32× más costo**.
*   **Hallazgo:** La baja precisión se debe principalmente a la **incompatibilidad de la métrica `exact-match`** con las respuestas verbose y de meta-razonamiento generadas por los LLMs (especialmente T-A-S), no a una falla inherente de los métodos. El contenido semántico de las respuestas a menudo es correcto, pero el formato no coincide con la respuesta esperada.
*   **Conclusión:** TruthfulQA, bajo la métrica actual, **no es un dataset útil para evaluar mejoras de precisión** de nuestro método dialéctico en este contexto.

### Contexto del Método T-A-S

Es crucial entender que el método T-A-S original (Abdali et al., 2025) fue diseñado para **generación de ideas y creatividad**, no para optimizar la precisión en benchmarks de razonamiento como GSM8K o TruthfulQA. Nuestro proyecto ha sido el **primero en evaluar empíricamente T-A-S en estos benchmarks**, demostrando que su valor reside en la generación de razonamiento detallado más que en la mejora de una métrica de precisión estricta.

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
# Editar .env con tu OPENAI_API_KEY o DEEPSEEK_API_KEY (requerido para los runs)
```

## 🏗️ Estructura del Proyecto

```
dialectic-llm/
├── src/
│   ├── flows/              # Prefect flows (baseline, T-A-S)
│   │   ├── baseline.py     # Flow baseline (single-call)
│   │   └── tas.py          # Flow T-A-S dialéctico (k=1)
│   ├── utils/              # Utilidades compartidas (data loading, evaluation, logging, etc.)
├── configs/
│   └── model.yaml          # Configuración de modelos
├── prompts/
│   └── tas/                # Templates de prompts (thesis, antithesis, synthesis)
├── logs/
│   └── events/             # Logs JSONL sanitizados de las ejecuciones
├── logs_local/             # Logs JSONL locales con Chain-of-Thought completo (gitignored)
├── analytics/
│   └── parquet/            # Archivos Parquet para análisis de resultados
├── tests/                  # Tests unitarios del proyecto
└── reports/                # Documentación y análisis de sprints
```

## 🎮 Uso (Reproducción de Corridas Clave)

Este proyecto se enfoca en la evaluación del método T-A-S. Para reproducir las corridas principales:

### 1. Preparar IDs de Problemas Comunes (TruthfulQA)

Para asegurar la comparabilidad estadística, se utiliza un conjunto fijo de `problem_ids`.

```bash
# (Este archivo ya debería existir en `data/processed/common_problem_ids.txt`)
# Si no existe, puedes generarlo desde el script de preparación de datos,
# asegurándote de usar los mismos 50 IDs de TruthfulQA para todos los runs.
```

### 2. Ejecutar Baseline en TruthfulQA (50 problemas)

Este script ejecuta la línea base en el dataset TruthfulQA.

```bash
uv run python scripts/run_s3_07_baseline_tqa_50.py
# Resultados en: analytics/parquet/baseline_tqa_50_*.parquet
```

### 3. Ejecutar T-A-S (k=1) en TruthfulQA (50 problemas)

Este script ejecuta el flujo T-A-S dialéctico en TruthfulQA.

```bash
uv run python scripts/run_s3_08_tas_tqa_50.py
# Resultados en: analytics/parquet/tas_tqa_50_*.parquet
```

### 4. Análisis de KPI y Taxonomía de Errores

Tras ejecutar las corridas, se pueden generar los KPIs y la taxonomía de errores.

```bash
# Ejecutar el análisis de KPIs (si está disponible un script actualizado para TQA)
# `scripts/run_s3_13_mcnemar_analysis.py` -> Aún enfocado en GSM8K, adaptable para TQA.

# Generar taxonomía de errores (ya realizada con resultados en analytics/parquet/)
# Los resultados de la taxonomía de errores (S3-15) ya están disponibles en:
# - `analytics/parquet/error_taxonomy_labeled.parquet`
# - `analytics/parquet/error_category_counts.json`
```

## ❌ Características No Exploradas/Eliminadas

Durante el desarrollo, se tomaron decisiones de diseño y alcance para mantener el enfoque y la eficiencia del proyecto:

*   **Uso explícito de "Debate"**: Si bien el método T-A-S es inherentemente dialéctico, la implementación de un "corpus de debate" o prompts de debate explícitos (más allá de T-A-S) se consideró un feature adicional costoso y no esencial para la hipótesis principal, siendo eliminada del plan.
*   **T-A-S con k=2 (múltiples rondas)**: La ejecución de T-A-S con `k=2` (dos rondas de T-A-S) fue eliminada debido a su **alto costo computacional** (ej. 100× el baseline) y a que el desempeño de `k=1` no justificó una mayor exploración.
*   **Re-corridas extensas en GSM8K**: Tras los resultados del Sprint 2, que mostraron que T-A-S no mejoró la precisión en GSM8K, se decidió no realizar re-corridas extensas en este dataset para el análisis final, priorizando TruthfulQA.

## 🔐 Seguridad y Privacidad

### Chain-of-Thought (CoT)
- ⚠️ **NUNCA** se comparten los logs con CoT completo
- CoT solo en `logs_local/` (gitignored)
- Logs compartidos en `logs/events/` están sanitizados

### Sanitización
- Información Personal Identificable (PII) detectada y redactada.
- Prompts y respuestas hasheados (`prompt_hash`, `response_hash`).
- Whitelist estricta de campos permitidos.

### Seguridad de Costos
- Límites de costo por ejecución y alertas para evitar exceder el presupuesto.
- Conteo de tokens automático para monitoreo.

## 🧪 Tests

```bash
# Ejecutar todos los tests
uv run pytest tests/

# Tests específicos (ejemplo)
uv run pytest tests/test_prompt_utils.py -v

# Con cobertura
uv run pytest tests/ --cov=src --cov-report=html
```

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
- [Paper Original T-A-S (Abdali et al., 2025)](https://arxiv.org/abs/2501.14917)
- [Paper del Proyecto (TBD)]

---

**Última Actualización**: 2 de diciembre de 2025
