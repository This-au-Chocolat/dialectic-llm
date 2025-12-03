# Sprint 3 Report: Transferability to TruthfulQA

**Versión:** 1.0
**Fecha:** 2 de diciembre de 2025
**Autor:** José Pech

---

## Resumen Ejecutivo

Este informe resume los resultados del Sprint 3, cuyo objetivo fue evaluar la **transferibilidad del método dialéctico T-A-S** a un nuevo dominio de razonamiento: **TruthfulQA**. A diferencia de GSM8K, que se enfoca en problemas matemáticos estructurados, TruthfulQA presenta preguntas engañosas que requieren pensamiento crítico, una hipótesis de trabajo donde la dialéctica podría prosperar.

Los resultados fueron unívocos: aunque el método T-A-S se ejecutó con éxito, **no demostró una mejora en la precisión bajo la métrica de `exact-match`**. Ambos, Baseline y T-A-S, obtuvieron un 0% de precisión, con T-A-S siendo **32 veces más costoso**. El análisis de errores revela que esta métrica estricta es la principal causa del fallo, ya que la mayoría de los errores son de formato y no de contenido semántico.

**Conclusión clave:** La transferencia del método T-A-S a TruthfulQA no es exitosa en términos de mejora de precisión medible con `exact-match`, y el costo computacional adicional no se justifica.

---

## 🎯 Objetivo del Sprint

El objetivo principal del Sprint 3 fue **evaluar si el método de razonamiento dialéctico T-A-S (Tesis-Antítesis-Síntesis) podría mejorar la precisión y robustez de un LLM en el dataset TruthfulQA**.

La hipótesis era que las preguntas ambiguas y que requieren "pensamiento lateral" de TruthfulQA se beneficiarían de la estructura crítica de T-A-S, a diferencia de los problemas más directos de GSM8K donde el método no tuvo éxito.

## 📊 Resultados Cuantitativos

Se ejecutaron dos corridas sobre un conjunto de **50 problemas comunes** del dataset TruthfulQA, utilizando el modelo `deepseek-chat`.

| Métrica                      | Baseline (Single Pass) | T-A-S (k=1)      | Multiplicador vs Baseline |
| ---------------------------- | ---------------------- | ---------------- | ------------------------- |
| **Precisión (Accuracy)**     | 0.00% (0/50)           | 0.00% (0/50)     | N/A                       |
| **Tokens Totales**           | 9,964                  | 370,035          | **37.2×**                 |
| **Costo Estimado (USD)**     | $0.004                 | $0.127           | **31.9×**                 |

### Interpretación de Resultados

1.  **Precisión Nula (0%)**: El resultado de 0% de precisión en ambos métodos no indica una falla en el razonamiento del LLM, sino una **limitación fundamental de la métrica de `exact-match`**. Las respuestas generadas, especialmente por T-A-S, son verbosas e incluyen meta-razonamiento (ej. `"**SYNTHESIS APPROACH:**..."`), lo que las hace incompatibles con una comparación de texto estricta que espera respuestas cortas y directas (ej. `"Nauru"`).
2.  **Costo Computacional**: T-A-S es significativamente más caro, consumiendo **~32-37 veces más recursos** que una pasada de baseline. Sin una mejora demostrable en la precisión, este costo es prohibitivo y no justifica su uso en este contexto.

---

## 🔬 Análisis Cualitativo de Errores (S3-15)

Para entender la causa del 0% de precisión, se realizó una taxonomía de errores sobre una muestra de 52 errores (50 de TQA, 2 de GSM8K).

| Categoría de Error | Cantidad | Descripción                                                                                                |
| ------------------ | -------- | ---------------------------------------------------------------------------------------------------------- |
| **Formato**        | 50       | La respuesta semántica es correcta, pero no coincide con el `exact-match` debido a texto adicional, explicaciones, etc. |
| **Interpretación** | 2        | El modelo malinterpreta un aspecto clave de la pregunta, llevando a una respuesta incorrecta.             |
| **Aritmética**     | 0        | Errores de cálculo matemático puro.                                                                        |
| **Ruptura**        | 0        | La respuesta es incoherente, irrelevante o está truncada.                                                  |

*Nota: Estos conteos incluyen 2 errores de GSM8K para un análisis más amplio, pero la tendencia en TQA es abrumadoramente de formato.*

### Figuras Simples: Distribución de Errores

```
Categoría de Error | Conteo
------------------ | ------
Formato            | 50
Interpretación     | 2
```

Este análisis confirma que la **evaluación `exact-match` es el principal bloqueador** para medir el rendimiento en TruthfulQA, ya que casi todos los errores se deben al formato de la respuesta.

---

## 🏁 Conclusiones del Sprint 3

1.  **Transferencia No Exitosa (en Precisión)**: El método T-A-S **no logró transferir exitosamente** sus capacidades para mejorar la precisión en el dataset TruthfulQA bajo la métrica de `exact-match`. La hipótesis de que se beneficiaría de este dominio no se pudo validar.
2.  **La Métrica es Clave**: Este sprint subraya la importancia crítica de **alinear la métrica de evaluación con la naturaleza de la tarea y del modelo**. Las respuestas generativas y de razonamiento de los LLMs modernos son incompatibles con métricas de `exact-match` estrictas. Para una evaluación justa, se requerirían métricas más sofisticadas (ej. similitud semántica, LLM-as-a-judge), que están fuera del alcance de este proyecto.
3.  **El Costo de la Dialéctica**: El método dialéctico, si bien genera un razonamiento más explícito, lo hace a un costo computacional muy elevado. Esta inversión solo se justificaría con una mejora sustancial en el rendimiento, lo cual no se observó.
4.  **Contribución Científica**: Aunque los resultados son "negativos" en términos de mejora, el sprint aporta un hallazgo valioso: la **primera evaluación empírica de T-A-S en TruthfulQA**, demostrando sus limitaciones en benchmarks con evaluación estricta y reforzando la idea de que fue diseñado para tareas de creatividad, no de precisión en benchmarks.

**Recomendación:** Para el informe final del proyecto, el foco principal debe permanecer en los resultados de GSM8K, donde la evaluación es más robusta, y presentar los hallazgos de TruthfulQA como una limitación y un área para futura investigación con métricas de evaluación más adecuadas.