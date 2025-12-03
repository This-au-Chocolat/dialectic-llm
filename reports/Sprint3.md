# Sprint 3 Report

## S3-13: McNemar & KPI Analysis for GSM8K

This analysis was performed on a common set of 50 problems from the GSM8K dataset, comparing the performance of the Baseline, T-A-S (k=1), and T-A-S+MAMV methods.

| model       | accuracy_pct   | delta_accuracy_vs_baseline_pct   | pvalue_vs_baseline   | total_tokens   |
|:------------|:---------------|:---------------------------------|:---------------------|:---------------|
| Baseline    | 98.00%         | N/A                              | N/A                  | 15,876         |
| T-A-S (k=1) | 0.00%          | -98.00%                          | 0.0000               | 296,641        |
| T-A-S+MAMV  | 98.00%         | +0.00%                           | N/A                  | 757,974        |

### Key Findings

- The T-A-S method, when combined with a strict exact-match evaluation, resulted in a 0% accuracy due to its verbose output format. The drop in performance is statistically significant (p < 0.0001).
- The T-A-S+MAMV method recovered the accuracy to the baseline level (98.00%) but at a prohibitively high token cost (48x the baseline).
- The results confirm that the dialectical methods, as implemented, do not provide a performance benefit on the GSM8K dataset and significantly increase computational cost.
