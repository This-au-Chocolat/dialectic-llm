import argparse

import pandas as pd


def label_and_summarize_errors(file_path: str):
    """
    Reads a CSV file with error samples, applies labels based on predefined rules,
    and then generates a Parquet file with error category counts.
    """
    df = pd.read_csv(file_path)

    # Initialize error_category column
    df["error_category"] = ""

    # 1. Label 'ruptura' errors (infrastructure issues)
    connection_error_mask = df["error"].str.contains(
        "Connection refused|Failed to reach API", na=False
    )
    df.loc[connection_error_mask, "error_category"] = "ruptura"

    # 2. Label 'formato' errors (correct answer, but parsing issue)
    # Based on manual inspection of the previously generated sample:
    format_error_problem_ids = ["gsm8k-4632", "gsm8k-3082", "gsm8k-2184", "gsm8k-5897"]
    df.loc[df["problem_id"].isin(format_error_problem_ids), "error_category"] = "formato"

    # 3. Label 'interpretacion' errors (flawed reasoning)
    # Based on manual inspection of the previously generated sample:
    df.loc[df["problem_id"] == "gsm8k-3703", "error_category"] = "interpretacion"

    # 4. Label remaining unassigned errors as 'aritmetica'
    df.loc[df["error_category"] == "", "error_category"] = "aritmetica"

    # Save the labeled sample for inspection (optional, but good for transparency)
    labeled_output_path = "analytics/mamv/error_labeled_sample.csv"
    df.to_csv(labeled_output_path, index=False)
    print(f"Labeled error sample saved to {labeled_output_path}")

    # Generate the Parquet file with category counts
    category_counts = df["error_category"].value_counts().reset_index()
    category_counts.columns = ["error_category", "count"]

    counts_output_path = "analytics/parquet/s2_11_error_taxonomy_counts.parquet"
    category_counts.to_parquet(counts_output_path, index=False)
    print(f"Error category counts saved to {counts_output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Label error samples and generate taxonomy counts."
    )
    parser.add_argument(
        "file_path",
        type=str,
        help=(
            "Path to the CSV file with error samples (e.g., "
            "analytics/mamv/error_labeling_sample.csv)."
        ),
    )
    args = parser.parse_args()
    label_and_summarize_errors(args.file_path)
