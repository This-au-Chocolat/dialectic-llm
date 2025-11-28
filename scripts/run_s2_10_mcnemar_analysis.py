import argparse
import sys
from pathlib import Path

import pandas as pd
from statsmodels.stats.contingency_tables import mcnemar

# Add src to the Python path to allow for absolute imports
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))


def load_data(file_path, model_name):
    """Loads parquet data and standardizes columns."""
    df = pd.read_parquet(file_path)

    if df.empty:
        raise ValueError(f"File {file_path} is empty.")

    # Check for 'is_correct' column
    if "is_correct" not in df.columns:
        raise ValueError(f"File {file_path} is missing 'is_correct' column.")

    # Check for 'problem_id' column
    if "problem_id" not in df.columns:
        raise ValueError(f"File {file_path} is missing 'problem_id' column.")

    # Standardize 'is_correct' and 'problem_id' names
    df.rename(
        columns={
            "is_correct": f"is_correct_{model_name}",
            "problem_id": f"problem_id_{model_name}",
        },
        inplace=True,
    )

    # --- Standardize 'total_tokens' ---
    # The logic here dynamically finds the token column, as its name differs between scripts.
    token_col_name = None
    if "total_tokens" in df.columns:  # This column might exist directly
        token_col_name = "total_tokens"
    elif "llm_usage" in df.columns:  # For baseline
        token_col_name = "llm_usage"
    elif "tas_usage" in df.columns:  # For tas_k1
        token_col_name = "tas_usage"
    elif "mamv_usage" in df.columns:  # For mamv
        token_col_name = "mamv_usage"

    if token_col_name:
        if isinstance(df[token_col_name].iloc[0], dict):
            df[f"total_tokens_{model_name}"] = df[token_col_name].apply(
                lambda x: x.get("total_tokens", 0)
            )
        else:  # Assume it's already the total tokens if not a dict
            df[f"total_tokens_{model_name}"] = df[token_col_name]
    else:
        # Fallback if no specific usage column is found
        df[f"total_tokens_{model_name}"] = 0
        print(f"Warning: No specific token usage column found in {file_path}. Defaulting to 0.")

    return df[
        [f"problem_id_{model_name}", f"is_correct_{model_name}", f"total_tokens_{model_name}"]
    ]


def calculate_mcnemar(df, col1, col2):
    """Calculates McNemar's test and returns p-value."""
    contingency_table = pd.crosstab(df[col1], df[col2])

    # Ensure the table is 2x2, filling with 0 if necessary
    if True not in contingency_table.index:
        contingency_table.loc[True] = 0
    if False not in contingency_table.index:
        contingency_table.loc[False] = 0
    if True not in contingency_table.columns:
        contingency_table[True] = 0
    if False not in contingency_table.columns:
        contingency_table[False] = 0

    # Sort to ensure consistent (False, True) order
    contingency_table = contingency_table.sort_index(axis=0).sort_index(axis=1)

    result = mcnemar(contingency_table, exact=False, correction=True)
    return result.pvalue


def main():
    parser = argparse.ArgumentParser(
        description="Perform McNemar's test and KPI analysis for S2-10."
    )
    parser.add_argument("baseline_file", type=str, help="Path to Baseline Parquet file.")
    parser.add_argument("tas_file", type=str, help="Path to T-A-S Parquet file.")
    parser.add_argument("mamv_file", type=str, help="Path to T-A-S+MAMV Parquet file.")
    args = parser.parse_args()

    # Load data
    print("Loading and standardizing data...")
    try:
        df_baseline_raw = load_data(args.baseline_file, "baseline")
        df_tas_raw = load_data(args.tas_file, "tas")
        df_mamv_raw = load_data(args.mamv_file, "mamv")
    except ValueError as e:
        print(f"\n❌ Error loading data: {e}")
        sys.exit(1)

    # Ensure all dataframes are sorted by their generated problem_id to ensure consistent order
    # (assuming problem_id 'gsm8k_0000', 'gsm8k_0001' maps to original problems in order)
    df_baseline_raw = df_baseline_raw.sort_values(by="problem_id_baseline").reset_index(drop=True)
    df_tas_raw = df_tas_raw.sort_values(by="problem_id_tas").reset_index(drop=True)
    df_mamv_raw = df_mamv_raw.sort_values(by="problem_id_mamv").reset_index(drop=True)

    # Extract problem_id from T-A-S, which has the correct IDs
    master_problem_ids = df_tas_raw["problem_id_tas"]

    # Drop problem_id columns from the raw DFs before joining on index, as they are inconsistent
    df_baseline_processed = df_baseline_raw.drop(columns=["problem_id_baseline"])
    df_tas_processed = df_tas_raw.drop(columns=["problem_id_tas"])
    df_mamv_processed = df_mamv_raw.drop(columns=["problem_id_mamv"])

    # Join dataframes based on index
    print("Joining dataframes based on their index (assuming consistent order)...")
    merged_df = df_baseline_processed.join(df_tas_processed, lsuffix="_b", rsuffix="_t")
    merged_df = merged_df.join(df_mamv_processed, rsuffix="_m")

    # Add the correct master problem_ids
    merged_df["problem_id"] = master_problem_ids

    # Ensure problem_id is the first column
    cols = ["problem_id"] + [col for col in merged_df if col != "problem_id"]
    merged_df = merged_df[cols]

    if len(merged_df) == 0:
        print("\n❌ Error: Merging resulted in an empty dataframe. Check file contents and paths.")
        sys.exit(1)

    print(f"Successfully loaded and merged data for {len(merged_df)} problems.")

    # --- KPI Calculation ---
    acc_baseline = merged_df["is_correct_baseline"].mean() * 100
    acc_tas = merged_df["is_correct_tas"].mean() * 100
    acc_mamv = merged_df["is_correct_mamv"].mean() * 100

    tokens_baseline = merged_df["total_tokens_baseline"].sum()
    tokens_tas = merged_df["total_tokens_tas"].sum()
    tokens_mamv = merged_df["total_tokens_mamv"].sum()

    # --- McNemar's Test ---
    print("\nPerforming McNemar's tests...")
    pvalue_tas_vs_baseline = calculate_mcnemar(merged_df, "is_correct_baseline", "is_correct_tas")
    pvalue_mamv_vs_baseline = calculate_mcnemar(merged_df, "is_correct_baseline", "is_correct_mamv")

    # --- Prepare results for Parquet and Markdown ---
    kpis = {
        "model": ["Baseline", "T-A-S (k=1)", "T-A-S+MAMV"],
        "accuracy_pct": [acc_baseline, acc_tas, acc_mamv],
        "delta_accuracy_vs_baseline_pct": [0, acc_tas - acc_baseline, acc_mamv - acc_baseline],
        "pvalue_vs_baseline": [None, pvalue_tas_vs_baseline, pvalue_mamv_vs_baseline],
        "total_tokens": [tokens_baseline, tokens_tas, tokens_mamv],
    }
    metrics_df = pd.DataFrame(kpis)

    # --- Generate metrics_s2.parquet ---
    output_parquet_path = Path("analytics/parquet/metrics_s2.parquet")
    metrics_df.to_parquet(output_parquet_path, index=False)
    print(f"\nMetrics saved to {output_parquet_path}")

    # --- Generate Markdown Table for Sprint2.md ---
    print("\n--- S2-10 KPI Results (for Sprint2.md) ---")

    # For display purposes, format the dataframe to a string with desired precision
    # This prevents pandas from using scientific notation for small p-values
    md_df = metrics_df.copy()
    md_df["accuracy_pct"] = md_df["accuracy_pct"].map("{:.2f}%".format)
    md_df["delta_accuracy_vs_baseline_pct"] = md_df["delta_accuracy_vs_baseline_pct"].map(
        "{:+.2f}%".format
    )
    md_df["pvalue_vs_baseline"] = md_df["pvalue_vs_baseline"].map(
        lambda p: f"{p:.4f}" if pd.notna(p) else "N/A"
    )
    md_df["total_tokens"] = md_df["total_tokens"].map("{:,}".format)

    # Set the first row's delta/p-value to N/A
    md_df.loc[0, "delta_accuracy_vs_baseline_pct"] = "N/A"
    md_df.loc[0, "pvalue_vs_baseline"] = "N/A"

    print(md_df.to_markdown(index=False))


if __name__ == "__main__":
    main()
