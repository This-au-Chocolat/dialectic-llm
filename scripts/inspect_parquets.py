
import argparse
import pandas as pd
from pathlib import Path

def inspect_parquet_files(file_paths):
    """
    Loads one or more Parquet files and prints a summary of their contents,
    focusing on problem_id and structure.
    """
    for file_path in file_paths:
        path = Path(file_path)
        print("---" * 20)
        if not path.exists():
            print(f"File not found: {path}\n")
            continue

        print(f"Inspecting file: {path.name}")
        
        try:
            df = pd.read_parquet(path)
            print(f"  - Total rows: {len(df)}")
            print(f"  - Columns: {df.columns.tolist()}")

            if "problem_id" in df.columns:
                print(f"  - First 5 problem_ids:\n{df['problem_id'].head().to_string(index=False)}")
            else:
                print("  - 'problem_id' column not found.")
            
            print("\n")

        except Exception as e:
            print(f"  - Error reading file: {e}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Inspect Parquet files to understand their structure and problem_ids."
    )
    parser.add_argument(
        "files",
        nargs='+',
        type=str,
        help="One or more paths to Parquet files to inspect.",
    )
    args = parser.parse_args()

    inspect_parquet_files(args.files)
