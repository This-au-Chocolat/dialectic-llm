"""
JSONL to Parquet conversion utility for S1-10.

This script converts JSONL log files to Parquet format for efficient analytics.
Supports both single file conversion and batch processing of entire directories.
"""

import argparse
import pathlib
from typing import List

import pandas as pd


def convert_jsonl_to_parquet(input_path: str, output_path: str) -> None:
    """
    Reads a JSONL file, converts it to a pandas DataFrame,
    and saves it as a Parquet file.

    Args:
        input_path: Path to the input JSONL file
        output_path: Path to the output Parquet file
    """
    print(f"Reading JSONL file from: {input_path}")

    try:
        df = pd.read_json(input_path, lines=True, dtype_backend="pyarrow")

        # Ensure the output directory exists
        pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        print(f"Writing Parquet file to: {output_path}")
        df.to_parquet(output_path, index=False)

        print(f"Conversion complete. Processed {len(df)} records.")

    except Exception as e:
        print(f"Error during conversion: {e}")
        raise


def convert_directory_jsonl_to_parquet(
    input_dir: str, output_dir: str, pattern: str = "*.jsonl"
) -> List[str]:
    """
    Convert all JSONL files in a directory to Parquet format.

    Args:
        input_dir: Directory containing JSONL files
        output_dir: Directory to write Parquet files
        pattern: File pattern to match (default: *.jsonl)

    Returns:
        List of created Parquet file paths
    """
    input_path = pathlib.Path(input_dir)
    output_path = pathlib.Path(output_dir)

    # Find all matching JSONL files
    jsonl_files = list(input_path.glob(pattern))

    if not jsonl_files:
        print(f"No JSONL files found in {input_dir} matching pattern {pattern}")
        return []

    print(f"Found {len(jsonl_files)} JSONL files to convert")

    created_files = []
    for jsonl_file in jsonl_files:
        # Create corresponding Parquet filename
        parquet_name = jsonl_file.stem + ".parquet"
        parquet_file = output_path / parquet_name

        try:
            convert_jsonl_to_parquet(str(jsonl_file), str(parquet_file))
            created_files.append(str(parquet_file))
        except Exception as e:
            print(f"Failed to convert {jsonl_file}: {e}")

    return created_files


def aggregate_analytics_run(
    run_id: str, events_dir: str = "logs/events", output_dir: str = "analytics/parquet"
) -> str:
    """
    Aggregate all JSONL events for a specific run into a single Parquet file.

    This is the main function for S1-10 requirements: converting JSONL→Parquet by run.

    Args:
        run_id: The run identifier to aggregate
        events_dir: Directory containing JSONL event files
        output_dir: Directory to write aggregated Parquet file

    Returns:
        Path to the created Parquet file
    """
    events_path = pathlib.Path(events_dir)
    output_path = pathlib.Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Find all JSONL files
    jsonl_files = list(events_path.glob("*.jsonl"))

    if not jsonl_files:
        raise ValueError(f"No JSONL files found in {events_dir}")

    # Read all JSONL files and filter by run_id
    all_events = []
    for jsonl_file in jsonl_files:
        try:
            df = pd.read_json(jsonl_file, lines=True, dtype_backend="pyarrow")
            # Filter by run_id if specified
            if run_id:
                run_events = df[df.get("run_id", "") == run_id]
                if len(run_events) > 0:
                    all_events.append(run_events)
            else:
                all_events.append(df)
        except Exception as e:
            print(f"Warning: Could not read {jsonl_file}: {e}")

    if not all_events:
        raise ValueError(f"No events found for run_id: {run_id}")

    # Combine all events
    combined_df = pd.concat(all_events, ignore_index=True)

    # Create output filename
    output_file = output_path / f"run_{run_id}.parquet"

    print(f"Aggregating {len(combined_df)} events for run {run_id}")
    combined_df.to_parquet(output_file, index=False)

    print(f"Created aggregated Parquet file: {output_file}")
    return str(output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert JSONL files to Parquet format for analytics (S1-10)."
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Single file conversion
    file_parser = subparsers.add_parser("file", help="Convert a single JSONL file")
    file_parser.add_argument("input_file", type=str, help="Path to the input JSONL file")
    file_parser.add_argument("output_file", type=str, help="Path to the output Parquet file")

    # Directory conversion
    dir_parser = subparsers.add_parser("directory", help="Convert all JSONL files in a directory")
    dir_parser.add_argument("input_dir", type=str, help="Directory containing JSONL files")
    dir_parser.add_argument("output_dir", type=str, help="Directory to write Parquet files")
    dir_parser.add_argument("--pattern", default="*.jsonl", help="File pattern to match")

    # Run aggregation (main S1-10 function)
    run_parser = subparsers.add_parser("aggregate", help="Aggregate events by run_id")
    run_parser.add_argument("run_id", type=str, help="Run ID to aggregate")
    run_parser.add_argument("--events-dir", default="logs/events", help="Events directory")
    run_parser.add_argument("--output-dir", default="analytics/parquet", help="Output directory")

    args = parser.parse_args()

    if args.command == "file":
        convert_jsonl_to_parquet(args.input_file, args.output_file)
    elif args.command == "directory":
        created_files = convert_directory_jsonl_to_parquet(
            args.input_dir, args.output_dir, args.pattern
        )
        print(f"Created {len(created_files)} Parquet files")
    elif args.command == "aggregate":
        output_file = aggregate_analytics_run(args.run_id, args.events_dir, args.output_dir)
        print(f"Aggregation complete: {output_file}")
    else:
        parser.print_help()
