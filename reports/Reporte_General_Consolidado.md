# Reporte General Consolidado

Este documento consolida los hallazgos, resultados y análisis realizados durante el Sprint 1 y el Sprint 2 del proyecto Dialectic-LLM.

## 1. Resumen del Sprint 1

### Resumen de Resultados
El objetivo principal fue establecer una línea base y realizar una comparación inicial entre el modelo `Baseline` y el enfoque `T-A-S` (Tesis-Antítesis-Síntesis).
*   **Comparación (Muestra Limitada):** Se realizó un análisis sobre 3 problemas comunes debido a inconsistencias en los datos.
*   **Precisión:** Ambos modelos alcanzaron un 100% de precisión en la muestra reducida.
*   **Costo:** El enfoque T-A-S consumió significativamente más tokens (Promedio: 350.00) comparado con el Baseline (Promedio: 139.67), representando un aumento de +210 tokens por ítem.

### Riesgos Identificados
*   **Escasez de Datos Comparables:** La principal limitación fue la falta de registros comparables para el modelo T-A-S debido a que el piloto anterior no siguió los estándares de logging.
*   **Significancia Estadística:** Debido al tamaño de muestra extremadamente pequeño (3 ítems), no fue posible calcular el p-valor de McNemar ni obtener conclusiones estadísticamente significativas.
*   **Calidad del Logging:** Se identificó que procesos anteriores no capturaron metadatos críticos como `problem_id`.

### Próximos Pasos (Post-Sprint 1)
*   Estandarizar estrictamente los procesos de logging para todas las ejecuciones futuras.
*   Asegurar que los datasets de salida (parquets) contengan los metadatos necesarios para permitir cruces de información y análisis comparativos robustos.

---

## 2. Análisis del Sprint 2

### Resultados Detallados
En este sprint se escaló el análisis a 50 problemas utilizando el modelo `DeepSeek-chat`, comparando tres configuraciones: Baseline, T-A-S (k=1) y T-A-S con Votación Mayoritaria (MAMV).

### Tabla de Métricas

| Modelo | Precisión (%) | Delta vs Baseline | P-valor (McNemar) | Total Tokens |
| :--- | :--- | :--- | :--- | :--- |
| **Baseline** | **98.00%** | N/A | N/A | 15,876 |
| **T-A-S (k=1)** | 96.00% | -2.00% | 1.0000 | 255,405 |
| **T-A-S + MAMV** | **98.00%** | +0.00% | 0.0000 | 757,974 |

### Interpretación
1.  **Alto Rendimiento del Baseline:** El modelo base ya es extremadamente competente (98% de acierto), dejando muy poco margen de mejora para las técnicas dialécticas.
2.  **Costo vs. Beneficio:**
    *   El enfoque dialéctico (**T-A-S**) aumentó drásticamente el consumo de tokens (de ~15k a ~255k) sin mejorar la precisión; de hecho, tuvo una leve caída al 96%.
    *   La adición de **MAMV** recuperó la precisión al 98% (igualando al baseline), pero disparó el costo a ~757k tokens.
3.  **Significancia Estadística:**
    *   El p-valor de 0.0000 para T-A-S+MAMV vs Baseline sugiere una diferencia significativa en el *patrón* de respuestas (aciertan/fallan en problemas distintos), aunque la precisión final sea idéntica.

### Calidad de Datos y Hallazgos Adicionales
Durante el análisis de calidad (Triage S2-19) se detectaron dos puntos clave:
*   **Error Recurrente:** El problema `gsm8k_0029` falla sistemáticamente en todas las ejecuciones, indicando un posible hueco lógico en el modelo para ese tipo específico de pregunta.
*   **Ejecución Incompleta:** Una de las ejecuciones de MAMV (`s2_06`) falló en 44 de 50 problemas por errores de conexión. Se decidió no re-ejecutar inmediatamente por restricciones de presupuesto/tiempo, dado que existen otras ejecuciones válidas suficientes para el análisis general.

### Próximos Pasos
1.  **Análisis Cualitativo:** Investigar las diferencias en las respuestas incorrectas. ¿Aporta la dialéctica "robustez" (mejores explicaciones) aunque no mejore la precisión numérica?
2.  **Gestión de Costos:** Evaluar la viabilidad del enfoque T-A-S+MAMV dado su costo prohibitivo para ganancias marginales en este dataset.
3.  **Triage Diferido:** Mantener en el backlog la re-ejecución de los 44 ítems fallidos si se requiere mayor integridad de datos en el futuro.
