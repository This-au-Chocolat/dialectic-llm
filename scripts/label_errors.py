import argparse
import glob

import pandas as pd


def label_errors(file_patterns: list[str], n_samples: int = 50):
    """
    Reads Parquet files matching the patterns, filters for incorrect answers,
    and prepares a sample for manual error labeling.
    """
    all_files = []
    for pattern in file_patterns:
        all_files.extend(glob.glob(pattern, recursive=True))

    if not all_files:
        print("No files found for the given patterns.")
        return

    df_list = [pd.read_parquet(file) for file in all_files]
    df = pd.concat(df_list, ignore_index=True)

    # The schema of the different files can be different.
    # We need to make sure the columns we need are present.

    # The mamv files have 'question', but the tas files don't.
    # I need to get the question from the original dataset.
    # For now, I will proceed without the question, and will add it later if needed.

    if "question" not in df.columns:
        df["question"] = "Question not available in this file"

    errors_df = df[~df["is_correct"]].copy()

    if len(errors_df) == 0:
        print("No errors found in the files.")
        return

    sample_df = errors_df.head(n_samples)
    sample_df["error_category"] = ""

    output_path = "analytics/mamv/error_labeling_sample.csv"
    sample_df.to_csv(output_path, index=False)
    print(f"Sample of {len(sample_df)} errors saved to {output_path}")
    print("Please manually label the 'error_category' column in that file.")
    print("The categories are: aritmetica, interpretacion, ruptura, formato.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare a sample of errors for labeling.")
    parser.add_argument(
        "file_patterns", nargs="+", type=str, help="Glob patterns for the Parquet files."
    )
    parser.add_argument("--n_samples", type=int, default=50, help="Number of samples to label.")
    args = parser.parse_args()
    label_errors(args.file_patterns, args.n_samples)
