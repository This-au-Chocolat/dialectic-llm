# scripts/run_s4_03_generate_final_kpis.py
"""
Consolidates the pre-calculated KPI metrics from S2 (GSM8K) and S3 (TQA)
into a final table for the S4 report.

Task: S4-03
DoD: Generate final KPIs (ΔAcc, p-values, tokens, costo).
"""

import logging
from pathlib import Path

import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Define constants
BASE_DIR = Path(__file__).parent.parent
ANALYTICS_DIR = BASE_DIR / "analytics" / "parquet"
RELEASES_DIR = BASE_DIR / "releases" / "v1.0" / "results"

# Source files containing pre-calculated KPIs
METRICS_FILES = {
    "gsm8k": ANALYTICS_DIR / "metrics_s2.parquet",
    "truthful_qa": ANALYTICS_DIR / "metrics_s3.parquet",
}

# DeepSeek model pricing (as of Dec 2025, for deepseek-chat)
# Source: Fictional assumption for this project based on typical market rates.
# Price per 1 million input tokens (prompt)
PRICE_PER_MILLION_INPUT_TOKENS_USD = 0.14
# Price per 1 million output tokens (completion)
PRICE_PER_MILLION_OUTPUT_TOKENS_USD = 0.28


def calculate_cost(row: pd.Series) -> float | None:
    """
    Calculates the estimated cost in USD for a single row.
    Returns None (which becomes pd.NA) if token counts are missing or zero.
    """
    prompt_tokens = row.get("prompt_tokens")
    completion_tokens = row.get("completion_tokens")

    if (
        pd.isna(prompt_tokens)
        or pd.isna(completion_tokens)
        or (prompt_tokens == 0 and completion_tokens == 0)
    ):
        return None

    input_cost = (prompt_tokens / 1_000_000) * PRICE_PER_MILLION_INPUT_TOKENS_USD
    output_cost = (completion_tokens / 1_000_000) * PRICE_PER_MILLION_OUTPUT_TOKENS_USD

    return input_cost + output_cost


def main():
    """
    Main function to orchestrate the consolidation of KPI metrics.
    """
    logging.info("Starting S4-03: Generate Final KPIs.")
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)

    all_kpis = []

    # --- 1. Load pre-calculated metrics ---
    logging.info("Loading pre-calculated KPI metrics...")
    for dataset_name, file_path in METRICS_FILES.items():
        if not file_path.exists():
            logging.warning(f"Metrics file not found, skipping: {file_path}")
            continue

        df = pd.read_parquet(file_path)
        df["dataset"] = dataset_name
        all_kpis.append(df)

    if not all_kpis:
        logging.error("No metrics files found. Aborting.")
        return

    kpi_df = pd.concat(all_kpis, ignore_index=True)
    # The 'model' column actually represents the experiment type
    kpi_df = kpi_df.rename(columns={"model": "experiment"})

    # Harmonize experiment names for merging
    experiment_name_map = {
        "Baseline": "baseline",
        "T-A-S (k=1)": "tas",
        "T-A-S+MAMV": "mamv",
    }
    kpi_df["experiment"] = kpi_df["experiment"].replace(experiment_name_map)

    # --- 2. Load consolidated run data to get detailed token counts for cost calculation ---
    logging.info("Loading consolidated run data for cost calculation...")
    consolidated_data_path = RELEASES_DIR / "kpi_consolidated.parquet"
    if not consolidated_data_path.exists():
        logging.error(f"Consolidated data not found at: {consolidated_data_path}")
        logging.error("Cannot calculate detailed costs. Aborting.")
        return

    df_runs = pd.read_parquet(consolidated_data_path)

    # Group by dataset and experiment to get total prompt and completion tokens
    token_summary = (
        df_runs.groupby(["dataset", "experiment"])
        .agg(prompt_tokens=("prompt_tokens", "sum"), completion_tokens=("completion_tokens", "sum"))
        .reset_index()
    )

    # --- 3. Calculate cost ---
    logging.info("Calculating estimated costs...")
    token_summary["cost_usd"] = token_summary.apply(calculate_cost, axis=1)

    # --- 4. Merge costs and reorder columns ---
    final_kpi_df = pd.merge(kpi_df, token_summary, on=["dataset", "experiment"], how="left")

    # Reorder for clarity
    column_order = [
        "dataset",
        "experiment",
        "accuracy_pct",
        "delta_accuracy_vs_baseline_pct",
        "pvalue_vs_baseline",
        "total_tokens",
        "cost_usd",
        "prompt_tokens",
        "completion_tokens",
    ]
    final_kpi_df = final_kpi_df[column_order]

    # --- 5. Save final KPI table ---
    output_path = RELEASES_DIR / "kpi_final_s4.parquet"
    final_kpi_df.to_parquet(output_path, index=False)

    logging.info(f"Successfully saved final KPI table: {output_path}")
    logging.info("Final KPI Summary:")
    print(final_kpi_df.to_markdown(index=False))
    logging.info("S4-03 KPI generation script finished.")


if __name__ == "__main__":
    main()
