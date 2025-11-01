import argparse
import pathlib

import pandas as pd


def convert_jsonl_to_parquet(input_path: str, output_path: str):
    """
    Reads a JSONL file, converts it to a pandas DataFrame,
    and saves it as a Parquet file.
    """
    print(f"Reading JSONL file from: {input_path}")
    df = pd.read_json(input_path, lines=True, dtype_backend="pyarrow")

    # Ensure the output directory exists
    pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    print(f"Writing Parquet file to: {output_path}")
    df.to_parquet(output_path, index=False)
    print("Conversion complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert JSONL file to Parquet format.")
    parser.add_argument("input_file", type=str, help="Path to the input JSONL file.")
    parser.add_argument("output_file", type=str, help="Path to the output Parquet file.")

    args = parser.parse_args()

    convert_jsonl_to_parquet(args.input_file, args.output_file)
