
import argparse
import pandas as pd
from pathlib import Path
import sys
from statsmodels.stats.contingency_tables import mcnemar
import numpy as np

# Add src to the Python path to allow for absolute imports
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

def create_contingency_table(df: pd.DataFrame, col1: str, col2: str) -> np.ndarray:
    """Creates a 2x2 contingency table for McNemar's test."""
    true_true = ((df[col1] == True) & (df[col2] == True)).sum()
    true_false = ((df[col1] == True) & (df[col2] == False)).sum()
    false_true = ((df[col1] == False) & (df[col2] == True)).sum()
    false_false = ((df[col1] == False) & (df[col2] == False)).sum()
    return np.array([[true_true, true_false], [false_true, false_false]])


def calculate_metrics_for_run(
    baseline_path: str, tas_path: str, mamv_path: str, output_parquet_name: str = "metrics_s2.parquet"
):
    """
    Reads baseline, T-A-S, and T-A-S+MAMV results, validates them, calculates
    McNemar's test, Delta Accuracy, and token usage, then saves to a parquet
    file and prints a markdown table.
    """
    try:
        baseline_df = pd.read_parquet(baseline_path)
        tas_df = pd.read_parquet(tas_path)
        mamv_df = pd.read_parquet(mamv_path)
    except FileNotFoundError as e:
        print(f"Error: Could not find one of the input files. {e}")
        sys.exit(1)

    # --- Validation Step ---
    print("Validating input files...")
    required_cols = ["problem_id", "is_correct", "total_tokens"]
    for df, name in zip([baseline_df, tas_df, mamv_df], ["Baseline", "T-A-S", "MAMV"]):
        if not all(col in df.columns for col in required_cols):
            print(f"Error: {name} file must contain the columns: {required_cols}")
            sys.exit(1)

    # Find common problem_ids
    ids_base = set(baseline_df["problem_id"])
    ids_tas = set(tas_df["problem_id"])
    ids_mamv = set(mamv_df["problem_id"])
    common_ids = ids_base.intersection(ids_tas).intersection(ids_mamv)

    if len(common_ids) < 10:  # Set a reasonable threshold
        print(f"Error: Found only {len(common_ids)} common problems across the three files.")
        print("Please ensure the Parquet files correspond to the same set of problems.")
        sys.exit(1)

    print(f"Found {len(common_ids)} common problems. Proceeding with analysis...")

    # Filter dataframes to only common problems
    baseline_df = baseline_df[baseline_df["problem_id"].isin(common_ids)].copy()
    tas_df = tas_df[tas_df["problem_id"].isin(common_ids)].copy()
    mamv_df = mamv_df[mamv_df["problem_id"].isin(common_ids)].copy()

    # --- Merge DataFrames ---
    merged_df = baseline_df.set_index("problem_id").join(
        tas_df.set_index("problem_id"), lsuffix="_base", rsuffix="_tas"
    ).join(
        mamv_df.set_index("problem_id"), rsuffix="_mamv"
    )

    # Clean up column names after joins
    merged_df = merged_df.rename(columns={
        "is_correct": "is_correct_mamv",
        "total_tokens": "total_tokens_mamv",
    })


    # --- Accuracy and Delta Accuracy ---
    acc_base = merged_df["is_correct_base"].mean()
    acc_tas = merged_df["is_correct_tas"].mean()
    acc_mamv = merged_df["is_correct_mamv"].mean()

    delta_acc_tas_vs_base = acc_tas - acc_base
    delta_acc_mamv_vs_base = acc_mamv - acc_base

    # --- Token Usage ---
    tokens_base = merged_df["total_tokens_base"].mean()
    tokens_tas = merged_df["total_tokens_tas"].mean()
    tokens_mamv = merged_df["total_tokens_mamv"].mean()

    # --- McNemar's Test ---
    # Baseline vs T-A-S
    contingency_table_tas = create_contingency_table(merged_df, "is_correct_base", "is_correct_tas")
    mcnemar_result_tas = mcnemar(contingency_table_tas, exact=False)
    p_value_tas_vs_base = mcnemar_result_tas.pvalue

    # Baseline vs T-A-S+MAMV
    contingency_table_mamv = create_contingency_table(merged_df, "is_correct_base", "is_correct_mamv")
    mcnemar_result_mamv = mcnemar(contingency_table_mamv, exact=False)
    p_value_mamv_vs_base = mcnemar_result_mamv.pvalue


    # --- Create metrics_s2.parquet ---
    metrics_data = {
        "metric": [
            "Accuracy_Baseline", "Accuracy_TAS", "Accuracy_MAMV",
            "Delta_Acc_TAS_vs_Base", "Delta_Acc_MAMV_vs_Base",
            "Avg_Tokens_Baseline", "Avg_Tokens_TAS", "Avg_Tokens_MAMV",
            "P_Value_McNemar_TAS_vs_Base", "P_Value_McNemar_MAMV_vs_Base",
            "N_Common_Problems",
        ],
        "value": [
            acc_base, acc_tas, acc_mamv,
            delta_acc_tas_vs_base, delta_acc_mamv_vs_base,
            tokens_base, tokens_tas, tokens_mamv,
            p_value_tas_vs_base, p_value_mamv_vs_base,
            len(common_ids),
        ],
    }
    metrics_df = pd.DataFrame(metrics_data)

    output_dir = Path("analytics/parquet")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_parquet_name
    metrics_df.to_parquet(output_path, index=False)
    print(f"\nMetrics saved to {output_path}")

    # --- Print Markdown Table and Interpretation ---
    print("\n# S2-10: McNemar y KPIs Reporte")
    print("\n## Resumen de Métricas")
    print(f"(Basado en N={len(common_ids)} problemas en común)")
    print("| Métrica                     | Baseline  | T-A-S     | T-A-S+MAMV |")
    print("| :-------------------------- | :-------- | :-------- | :--------- |")
    print(f"| Precisión (Accuracy)        | {acc_base:.3f}    | {acc_tas:.3f}    | {acc_mamv:.3f}   |")
    print(f"| Δ Precisión (vs Baseline)   | -         | {delta_acc_tas_vs_base:+.3f}   | {delta_acc_mamv_vs_base:+.3f}  |")
    print(f"| P-Value (McNemar vs Base)   | -         | {p_value_tas_vs_base:.4f}  | {p_value_mamv_vs_base:.4f} |")
    print(f"| Tokens Promedio por Ítem    | {tokens_base:,.0f} | {tokens_tas:,.0f} | {tokens_mamv:,.0f} |")

    print("\n## Interpretación")
    if p_value_tas_vs_base < 0.05:
        tas_significance = f"la mejora de {(delta_acc_tas_vs_base * 100):.1f}pp es **estadísticamente significativa**"
    else:
        tas_significance = f"la diferencia de {(delta_acc_tas_vs_base * 100):.1f}pp **no es estadísticamente significativa**"

    if p_value_mamv_vs_base < 0.05:
        mamv_significance = f"la mejora de {(delta_acc_mamv_vs_base * 100):.1f}pp es **estadísticamente significativa**"
    else:
        mamv_significance = f"la diferencia de {(delta_acc_mamv_vs_base * 100):.1f}pp **no es estadísticamente significativa**"

    print(f"- El enfoque T-A-S ({acc_tas:.3f}) muestra un cambio de {delta_acc_tas_vs_base:+.3f} en precisión sobre el Baseline ({acc_base:.3f}). Con un p-valor de {p_value_tas_vs_base:.4f}, {tas_significance}.")
    print(f"- El enfoque T-A-S+MAMV ({acc_mamv:.3f}) muestra un cambio de {delta_acc_mamv_vs_base:+.3f} en precisión sobre el Baseline. Con un p-valor de {p_value_mamv_vs_base:.4f}, {mamv_significance}.")
    print(f"- En términos de costo, T-A-S consume un promedio de {tokens_tas:,.0f} tokens, mientras que MAMV consume {tokens_mamv:,.0f}, comparado con los {tokens_base:,.0f} del Baseline.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Perform McNemar's test and KPI comparison for T-A-S models."
    )
    parser.add_argument(
        "--baseline",
        type=str,
        required=True,
        help="Path to the Baseline Parquet file.",
    )
    parser.add_argument(
        "--tas",
        type=str,
        required=True,
        help="Path to the T-A-S Parquet file.",
    )
    parser.add_argument(
        "--mamv",
        type=str,
        required=True,
        help="Path to the T-A-S+MAMV Parquet file.",
    )
    parser.add_argument(
        "--output-name",
        type=str,
        default="metrics_s2.parquet",
        help="Name for the output Parquet file (e.g., metrics_s2.parquet).",
    )
    args = parser.parse_args()

    calculate_metrics_for_run(
        baseline_path=args.baseline,
        tas_path=args.tas,
        mamv_path=args.mamv,
        output_parquet_name=args.output_name,
    )
