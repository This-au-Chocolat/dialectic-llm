import argparse
import sys
from pathlib import Path

import pandas as pd

# Add src to the Python path to allow for absolute imports
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from llm.client import extract_gsm8k_answer
from utils.evaluation import evaluate_exact_match


def fix_tas_k1_output(input_file: str, output_file: str):
    """
    Loads a T-A-S (k=1) Parquet file, extracts the numeric answer from the
    predicted_answer_raw column, recalculates is_correct, and saves the
    corrected data to a new Parquet file.
    """
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: Input file not found at {input_path}")
        sys.exit(1)

    print(f"Loading data from {input_path}...")
    df = pd.read_parquet(input_path)

    # Ensure required columns are present
    required_cols = ["true_answer", "predicted_answer_raw", "problem_id"]
    if not all(col in df.columns for col in required_cols):
        print(f"Error: Input file must contain the columns: {required_cols}")
        sys.exit(1)

    print("Extracting numeric answers and recalculating 'is_correct'...")

    # Apply extraction and recalculation
    df["predicted_numeric_answer"] = df["predicted_answer_raw"].apply(extract_gsm8k_answer)
    df["is_correct_recalculated"] = df.apply(
        lambda row: evaluate_exact_match(
            y_true=float(
                row["true_answer"].split("#### ")[-1].strip()
            ),  # Extract numeric part from true_answer too
            y_pred_raw=row["predicted_numeric_answer"],
        ),
        axis=1,
    )
    # Overwrite the original 'is_correct' with the recalculated one
    df["is_correct"] = df["is_correct_recalculated"]

    # Drop the temporary column
    df = df.drop(columns=["predicted_numeric_answer", "is_correct_recalculated"])

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure output directory exists

    print(f"Saving corrected data to {output_path}...")
    df.to_parquet(output_path, index=False)
    print("Correction complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fix T-A-S (k=1) output: extract numeric answers and recalculate correctness."
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the input T-A-S (k=1) Parquet file with full text predictions.",
    )
    parser.add_argument("output_file", type=str, help="Path for the corrected output Parquet file.")
    args = parser.parse_args()

    fix_tas_k1_output(args.input_file, args.output_file)
