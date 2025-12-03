# scripts/run_s4_05_check_no_regression.py
"""
Checks for no-regression of invalid/format errors, as specified in task S4-05.

Task: S4-05
DoD: Verify that the error rate for T-A-S and MAMV is not more than
     2 percentage points higher than the baseline's error rate.
Input: `releases/v1.0/results/kpi_consolidated.parquet`
"""

import logging
from pathlib import Path

import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Define constants
BASE_DIR = Path(__file__).parent.parent
RELEASES_DIR = BASE_DIR / "releases" / "v1.0" / "results"
CONSOLIDATED_FILE = RELEASES_DIR / "kpi_consolidated.parquet"

# The no-regression criterion: error rate must be <= baseline + THRESHOLD
THRESHOLD_PP = 2.0


def main():
    """
    Main function to load data, calculate error rates, and check the no-regression criterion.
    """
    logging.info("Starting S4-05: Check No-Regression (invalid/format).")

    if not CONSOLIDATED_FILE.exists():
        logging.error(f"Consolidated KPI file not found: {CONSOLIDATED_FILE}")
        logging.error("Cannot perform no-regression check. Please run S4-02 first.")
        return

    df = pd.read_parquet(CONSOLIDATED_FILE)
    logging.info(f"Loaded consolidated data from {CONSOLIDATED_FILE}")

    # The `has_error` column is boolean. The mean gives the percentage of True values.
    # We fill NA with False, assuming that if `has_error` is not specified, it's not an error.
    df["has_error"] = df["has_error"].fillna(False)
    error_rates = df.groupby(["dataset", "experiment"])["has_error"].mean() * 100

    print("\n" + "=" * 60)
    print("Invalid/Format Error Rate (%) per Experiment")
    print("-" * 60)
    print(error_rates.to_string(float_format="%.2f%%"))
    print("=" * 60)

    print("\n" + "=" * 60)
    print("No-Regression Check (Criterion: Error Rate <= Baseline + 2pp)")
    print("-" * 60)

    for dataset in error_rates.index.get_level_values("dataset").unique():
        try:
            baseline_rate = error_rates.loc[(dataset, "baseline")]
        except KeyError:
            logging.warning(f"No baseline data for dataset '{dataset}'. Skipping check.")
            continue

        logging.info(
            f"Processing dataset: {dataset.upper()} (Baseline Error Rate: {baseline_rate:.2f}%)"
        )

        for experiment in ["tas", "mamv"]:
            try:
                exp_rate = error_rates.loc[(dataset, experiment)]
                is_met = exp_rate <= (baseline_rate + THRESHOLD_PP)
                delta = exp_rate - baseline_rate

                status = "✅ PASSED" if is_met else "❌ FAILED"

                print(
                    f"  - {experiment.upper()} vs Baseline: "
                    f"({exp_rate:.2f}% vs {baseline_rate:.2f}%) | "
                    f"Delta: {delta:+.2f}pp | "
                    f"Status: {status}"
                )

            except KeyError:
                # This is expected if an experiment (e.g., mamv for tqa) was not run
                logging.info(f"  - No data for experiment '{experiment}'. Skipping check.")

    print("=" * 60)
    logging.info("\nS4-05 No-regression check script finished.")


if __name__ == "__main__":
    main()
