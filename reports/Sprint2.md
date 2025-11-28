# Sprint 2 - Análisis de Resultados (S2-10: McNemar y KPIs)

## KPIs Comparativos (Baseline vs T-A-S vs T-A-S+MAMV)

Los siguientes resultados comparan el rendimiento de los modelos Baseline, T-A-S (k=1) y T-A-S+MAMV en un conjunto de 50 problemas, usando el modelo DeepSeek-chat.

| model       | accuracy_pct   | delta_accuracy_vs_baseline_pct   | pvalue_vs_baseline   | total_tokens   |
|:------------|:---------------|:---------------------------------|:---------------------|:---------------|
| Baseline    | 98.00%         | N/A                              | N/A                  | 15,876         |
| T-A-S (k=1) | 96.00%         | -2.00%                           | 1.0000               | 255,405        |
| T-A-S+MAMV  | 98.00%         | +0.00%                           | 0.0000               | 757,974        |

## Interpretación de Resultados

*   **Baseline:** Muestra una alta precisión del 98% con un costo en tokens relativamente bajo (15,876 tokens). Establece un benchmark sólido.

*   **T-A-S (k=1):** Con una precisión del 96%, el modelo T-A-S (k=1) está muy cerca del Baseline (-2% de delta). El p-valor de 1.0000 indica que esta pequeña diferencia no es estadísticamente significativa, lo que sugiere que su rendimiento es comparable al Baseline en este set de datos. Sin embargo, su consumo de tokens (255,405 tokens) es considerablemente más alto que el Baseline.

*   **T-A-S+MAMV:** Este modelo logra una precisión del 98%, igualando perfectamente al Baseline. El p-valor de 0.0000 sugiere una diferencia estadísticamente significativa en el patrón de respuestas incorrectas/correctas en comparación con el Baseline, a pesar de que la precisión global sea la misma (esto puede indicar que los errores ocurren en problemas diferentes). Su consumo de tokens (757,974 tokens) es extremadamente alto, siendo el más costoso de los tres enfoques.

## Conclusiones y Próximos Pasos

1.  **Rendimiento vs. Costo:** Tanto T-A-S (k=1) como T-A-S+MAMV logran una precisión comparable o ligeramente inferior al Baseline, pero con un costo en tokens significativamente mayor. Esto plantea la pregunta sobre el valor añadido de la dialéctica en esta configuración particular, especialmente con el modelo DeepSeek-chat.
2.  **MAMV como Match del Baseline:** T-A-S+MAMV iguala la precisión del Baseline, lo que indica que el mecanismo de votación por mayoría puede ser efectivo, pero su altísimo costo es una barrera importante.
3.  **McNemar y p-values:** Los p-valores deben interpretarse cuidadosamente. Un p-valor de 1.0000 (T-A-S vs. Baseline) sugiere que las diferencias observadas son puramente aleatorias. Un p-valor de 0.0000 (T-A-S+MAMV vs. Baseline) con un delta de 0% en precisión puede indicar una diferencia estadísticamente significativa en los *casos donde aciertan o fallan*, no necesariamente en la tasa de acierto global.
4.  **Investigación Adicional:** Sería valioso investigar las diferencias específicas en las respuestas incorrectas entre Baseline y T-A-S+MAMV para entender si el enfoque dialéctico aporta un tipo diferente de robustez o si simplemente es más costoso sin beneficio claro en precisión.