# reports/Sprint4.md
## S4-03: McNemar y KPIs finales por dataset y variante

### Resumen de KPIs Finales

| dataset     | experiment   |   accuracy_pct |   delta_accuracy_vs_baseline_pct |   pvalue_vs_baseline |   total_tokens |     cost_usd | prompt_tokens   | completion_tokens   |
|:------------|:-------------|---------------:|---------------------------------:|---------------------:|---------------:|-------------:|:----------------|:--------------------|
| gsm8k       | baseline     |             98 |                                0 |        nan           |          15876 |   0.00366296 | 5588            | 10288               |
| gsm8k       | tas          |             96 |                               -2 |          1           |         255405 |   0.0499414  | 154086          | 101319              |
| gsm8k       | mamv         |             98 |                                0 |          0           |         757974 | nan          | 0               | 0                   |
| truthful_qa | baseline     |             98 |                                0 |        nan           |          15876 | nan          | 0               | 0                   |
| truthful_qa | tas          |              0 |                              -98 |          7.02514e-12 |         296641 | nan          | 0               | 0                   |
| truthful_qa | mamv         |             98 |                                0 |        nan           |         757974 | nan          | <NA>            | <NA>                |

## S4-09: Distribución de categorías de error + ejemplos

### Distribución de Categorías de Error
| Category       |   Count |   Percentage |
|:---------------|--------:|-------------:|
| ruptura        |      88 |        92.63 |
| formato        |       4 |         4.21 |
| aritmetica     |       2 |         2.11 |
| interpretacion |       1 |         1.05 |

### Ejemplos para las Top 5 Categorías de Error
#### Categoría: ruptura
- **Dataset:** gsm8k
- **Problem ID:** gsm8k_0006
- **Pregunta:** Don throws 3 darts.  One is a bullseye worth 50 points.  One completely missed the target, so received no points. The third was worth half the points of the bullseye.  What is the final score from these 3 throws?
- **Respuesta Correcta:** 75.0
- **Respuesta Predicha:** 75

- **Dataset:** gsm8k
- **Problem ID:** gsm8k_0007
- **Pregunta:** TreQuan is throwing rocks in the river and he notices that the bigger the rock, the wider the splash. Pebbles make a splash that is a 1/4 meter wide. Rocks make a splash that is 1/2 a meter wide, and boulders create a splash that is 2 meters wide. If he tosses 6 pebbles, 3 rocks, and 2 boulders, what is the total width of the splashes he makes?
- **Respuesta Correcta:** 7.0
- **Respuesta Predicha:** 7

#### Categoría: formato
- **Dataset:** gsm8k
- **Problem ID:** gsm8k-4632
- **Pregunta:**
- **Respuesta Correcta:** 4.0
- **Respuesta Predicha:**

- **Dataset:** gsm8k
- **Problem ID:** gsm8k-3082
- **Pregunta:**
- **Respuesta Correcta:** 16.0
- **Respuesta Predicha:** **SYNTHESIS APPROACH:**
I will integrate the step-by-step clarity of the thesis with the deeper mathematical insights and robustness checks from the antithesis. Specifically, I will:
- Use the sequential approach for clarity but enhance it with a unified expression for verification.
- Address the potential ambiguity regarding Kyle’s shells by explicitly justifying the interpretation.
- Incorporate unit preservation and fractional relationship chains to validate the result.
- Add a sense-check to ensure the answer is contextually reasonable.

---

**FINAL SOLUTION:**

**Step 1: Convert Mimi’s shells to individual units.**
- Mimi picked 2 dozen seashells.
- Since 1 dozen = 12 shells, Mimi has:
  \[
  2 \times 12 = 24 \text{ shells}
  \]

**Step 2: Determine Kyle’s shells.**
- Kyle found twice as many shells as Mimi:
  \[
  2 \times 24 = 48 \text{ shells}
  \]
- The detail that Kyle “put them in his pocket” does not affect the quantity Leigh took, as Leigh grabbed from “the shells Kyle found” (not necessarily from his pocket).

**Step 3: Calculate Leigh’s shells.**
- Leigh took one-third of what Kyle found:
  \[
  \frac{1}{3} \times 48 = 16 \text{ shells}
  \]

**Verification Methods:**
1. **Unified Expression:**
   \[
   \frac{1}{3} \times (2 \times (2 \times 12)) = \frac{1}{3} \times 48 = 16
   \]
2. **Fractional Relationship Chain:**
   Leigh’s shells = \(\frac{1}{3} \times 2 \times \text{Mimi’s shells} = \frac{2}{3} \times 24 = 16\).
3. **Unit Preservation (dozens):**
   Mimi: 2 dozen → Kyle: \(2 \times 2 = 4\) dozen → Leigh: \(\frac{1}{3} \times 4 = \frac{4}{3}\) dozen = \(1 \tfrac{1}{3} \times 12 = 16\) shells.

**Sense-Check:**
Mimi has 24 shells, Kyle has 48, and Leigh has 16. Since 16 is \(\frac{2}{3}\) of Mimi’s total and \(\frac{1}{3}\) of Kyle’s, the proportions align logically with the problem’s relationships.

---

**KEY IMPROVEMENTS:**
1. **Explicit Interpretation:** Clarified that “shells Kyle found” refers to the total he collected (48), not a subset after pocketing.
2. **Robust Verification:** Used multiple independent methods (unified expression, proportional reasoning, unit preservation) to confirm the result.
3. **Contextual Plausibility:** Added a sense-check to ensure the answer fits the problem’s relationships.
4. **Clear Final Answer:** Stated the conclusion in context: “Leigh has 16 seashells.”

---

**CONFIDENCE ASSESSMENT:**
- **High Confidence** due to consistent results across multiple calculation methods, clear logical progression, and reasonable contextual interpretation.

---

**FINAL ANSWER:**
#### 16

#### Categoría: aritmetica
- **Dataset:** gsm8k
- **Problem ID:** gsm8k_0029
- **Pregunta:** Jason is planning a parking garage that will have 12 floors. Every 3rd floor has a gate where drivers have to show ID, which takes two minutes. To get from one floor to the next, drivers have to drive 800 feet at 10 feet/second. How long, in seconds, does it take to get to the bottom of the garage from the top?
- **Respuesta Correcta:** 1440.0
- **Respuesta Predicha:** 1360

#### Categoría: interpretacion
- **Dataset:** gsm8k
- **Problem ID:** gsm8k-3703
- **Pregunta:**
- **Respuesta Correcta:** 1440.0
- **Respuesta Predicha:** 1240
