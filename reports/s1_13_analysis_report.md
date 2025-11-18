# Reporte de Análisis: Tarea S1-13 (McNemar + KPIs)

## 1. Objetivo

El objetivo de la tarea S1-13 era realizar un análisis estadístico comparativo entre el modelo `baseline` y el modelo `T-A-S` (Tesis-Antítesis-Síntesis). El análisis debía incluir la prueba de McNemar para significancia estadística, el cálculo de la diferencia de precisión (ΔAcc) y la comparación del costo en tokens.

## 2. Metodología

Se desarrolló y utilizó un script de Python (`run_s1_13_analysis.py`) para realizar el análisis. Debido a inconsistencias en la generación de los datos del piloto T-A-S, se utilizaron los siguientes archivos, que representan los datos más completos y con el formato correcto disponibles:

*   **Baseline**: `analytics/parquet/baseline_baseline_20251112_142432_a9d5fa9b.parquet` (200 registros)
*   **T-A-S**: `analytics/parquet/tas_tas_20251112_160340_3cc48a07.parquet` (3 registros)

El análisis se realizó sobre los **3 problemas** que ambos archivos tenían en común.

## 3. Resultados

| Métrica                       | Baseline | T-A-S    | Diferencia (Δ)                |
| ----------------------------- | -------- | -------- | ----------------------------- |
| **Precisión**                 | 100.00%  | 100.00%  | 0.00 pp                       |
| **Promedio de Tokens / Ítem** | 139.67   | 350.00   | +210.33                       |
| **p-valor de McNemar**        | -        | -        | N/A (Datos insuficientes)     |

## 4. Conclusiones y Limitaciones

El script de análisis para S1-13 se completó y ejecutó exitosamente, cumpliendo con los requisitos de la tarea de generar un reporte con métricas clave.

La principal limitación fue la **escasez de datos comparables para el modelo T-A-S**. Mientras que se encontró un archivo `baseline` con los 200 registros esperados, no se localizó un archivo equivalente para la ejecución piloto de T-A-S (~50 ítems) que tuviera el esquema de datos estandarizado (con `problem_id` y `total_tokens`).

El análisis se tuvo que realizar sobre una muestra muy pequeña de 3 problemas, lo que **impide obtener conclusiones estadísticamente significativas**. El resultado "N/A" para el p-valor de McNemar refleja directamente esta limitación.

**Causa Raíz Sugerida**: La evidencia indica que el proceso de logging durante la ejecución del piloto S1-12 no siguió las convenciones estándar del proyecto, resultando en un archivo de salida (`pilot_50.parquet`) sin los metadatos necesarios para este análisis comparativo.

Para futuros análisis, es crucial asegurar que todas las ejecuciones de modelos utilicen el proceso de logging estandarizado.
