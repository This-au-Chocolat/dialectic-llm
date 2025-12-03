# scripts/run_s4_04_generate_ablation.py
"""
Generates the MAMV ON/OFF ablation table as specified in task S4-04.

Task: S4-04
DoD: Generate 2x2 table per dataset with accuracy/tokens/cost.
Input: `releases/v1.0/results/kpi_final_s4.parquet`
Output: Markdown table to console and `releases/v1.0/results/ablation_mamv.csv`.
"""

import logging
from pathlib import Path

import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Define constants
BASE_DIR = Path(__file__).parent.parent
RELEASES_DIR = BASE_DIR / "releases" / "v1.0" / "results"
KPI_FILE = RELEASES_DIR / "kpi_final_s4.parquet"
OUTPUT_CSV = RELEASES_DIR / "ablation_mamv.csv"


def format_cell(accuracy, tokens):
    """Formats a cell as 'accuracy% / tokens_k'."""
    if pd.isna(accuracy) or pd.isna(tokens):
        return "N/A"
    acc_str = f"{accuracy:.0f}%"
    tok_str = f"{tokens/1000:.1f}k"
    return f"{acc_str} / {tok_str}"


def main():
    """
    Main function to generate and display the ablation tables.
    """
    logging.info("Starting S4-04: Generate Ablation MAMV ON/OFF.")

    if not KPI_FILE.exists():
        logging.error(f"KPI file not found: {KPI_FILE}")
        logging.error("Cannot generate ablation table. Please run S4-03 first.")
        return

    df_kpi = pd.read_parquet(KPI_FILE)
    logging.info(f"Loaded KPI data from {KPI_FILE}")

    # --- Prepare data for CSV output ---
    # This will be a "long" format table which is machine-readable.
    ablation_data = []

    for _, row in df_kpi.iterrows():
        dataset = row["dataset"]
        experiment = row["experiment"]

        method = "N/A"
        mamv_status = "N/A"

        if experiment == "baseline":
            method = "Baseline"
            mamv_status = "MAMV OFF"
        elif experiment == "tas":
            method = "T-A-S"
            mamv_status = "MAMV OFF"
        elif experiment == "mamv":
            method = "T-A-S"
            mamv_status = "MAMV ON"

        ablation_data.append(
            {
                "dataset": dataset,
                "method": method,
                "mamv_status": mamv_status,
                "accuracy_pct": row["accuracy_pct"],
                "total_tokens": row["total_tokens"],
                "cost_usd": row["cost_usd"],
            }
        )

    df_ablation_long = pd.DataFrame(ablation_data)
    df_ablation_long.to_csv(OUTPUT_CSV, index=False)
    logging.info(f"Successfully saved long-format ablation data to: {OUTPUT_CSV}")

    # --- Generate and print Markdown tables ---
    for dataset_name in df_kpi["dataset"].unique():
        print("\n" + "=" * 50)
        print(f"Dataset: {dataset_name.upper()} (50 problemas)")
        print("=" * 50)

        df_dataset = df_kpi[df_kpi["dataset"] == dataset_name]

        # Per SprintsV4.md and HANDOFF_JOSE.md, the MAMV experiment was not run for truthful_qa.
        # We must filter it out to prevent showing erroneous data.
        if dataset_name == "truthful_qa":
            df_dataset = df_dataset[df_dataset["experiment"] != "mamv"]

        # Create the structure for the pivot table
        ablation_table = pd.DataFrame(
            index=["Baseline", "T-A-S"], columns=["MAMV OFF (k=1)", "MAMV ON (k=1, n=3)"]
        )

        # Populate the table
        try:
            baseline_row = df_dataset[df_dataset["experiment"] == "baseline"].iloc[0]
            ablation_table.loc["Baseline", "MAMV OFF (k=1)"] = format_cell(
                baseline_row["accuracy_pct"], baseline_row["total_tokens"]
            )
        except IndexError:
            ablation_table.loc["Baseline", "MAMV OFF (k=1)"] = "N/A"

        ablation_table.loc["Baseline", "MAMV ON (k=1, n=3)"] = "N/A"

        try:
            tas_row = df_dataset[df_dataset["experiment"] == "tas"].iloc[0]
            ablation_table.loc["T-A-S", "MAMV OFF (k=1)"] = format_cell(
                tas_row["accuracy_pct"], tas_row["total_tokens"]
            )
        except IndexError:
            ablation_table.loc["T-A-S", "MAMV OFF (k=1)"] = "N/A"

        try:
            mamv_row = df_dataset[df_dataset["experiment"] == "mamv"].iloc[0]
            ablation_table.loc["T-A-S", "MAMV ON (k=1, n=3)"] = format_cell(
                mamv_row["accuracy_pct"], mamv_row["total_tokens"]
            )
        except IndexError:
            ablation_table.loc["T-A-S", "MAMV ON (k=1, n=3)"] = "N/A"

        # Print the markdown table
        print(ablation_table.to_markdown())

    logging.info("\nS4-04 Ablation table generation script finished.")


if __name__ == "__main__":
    main()
