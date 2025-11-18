"""
This script executes the Prefect flow `run_tas_gsm8k` from `src/flows/tas.py`.

It performs the following steps:
1. Calls the `run_tas_gsm8k` flow for 50 problems.
2. After execution, it prints:
   - Number of correct predictions.
   - Final accuracy.
   - Total token cost.
3. Confirms that:
   - A new .jsonl log file was created in `logs/events/`.
   - A .parquet result file was saved.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to the Python path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from src.flows.tas import run_tas_gsm8k
except ImportError as e:
    print(
        f"Error importing modules. Make sure you are running from the project root "
        f"and your PYTHONPATH is set correctly. Details: {e}"
    )
    sys.exit(1)


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def find_latest_file(directory: Path, pattern: str) -> Path | None:
    """Finds the most recently modified file in a directory matching a pattern."""
    try:
        files = list(directory.glob(pattern))
        if not files:
            return None
        return max(files, key=lambda f: f.stat().st_mtime)
    except FileNotFoundError:
        return None


def main():
    """Main function to run the TAS flow and report results."""
    run_id = "pilot_50"
    num_problems = 50

    # Note: The user's request mentioned several functions/scripts that are
    # handled internally by the `run_tas_gsm8k` flow.
    # - `load_tas_batch` is called inside the flow.
    # - Token calculation is derived from the flow's results.
    # - Parquet conversion is also handled inside the flow.
    # This script acts as a simple caller and result processor as requested.

    try:
        logging.info(f"Starting TAS flow run with run_id: '{run_id}' for {num_problems} problems.")

        # The `save=True` parameter mentioned in the prompt is not needed
        # as the flow saves by default.
        # The `run_tas_gsm8k` was modified to return both summary and detailed results.
        summary, results = run_tas_gsm8k(n_problems=num_problems, run_id=run_id)

        if not summary or not results:
            logging.error("Flow execution did not return the expected summary and results.")
            return

        # --- Print Results ---
        correct_predictions = summary.get("correct", 0)
        accuracy = summary.get("accuracy", 0.0)

        # Calculate total tokens from the detailed results
        total_tokens = sum(r.get("tas_usage", {}).get("total_tokens", 0) for r in results)

        print("\n--- ✅ Execution Results ---")
        print(f"Correct Predictions: {correct_predictions}")
        print(f"Final Accuracy:      {accuracy:.3f}")
        print(f"Total Token Cost:    {total_tokens}")
        print("---------------------------\n")

        # --- Confirm File Creation ---
        logging.info("Confirming output file creation...")

        # 1. Confirm .jsonl log file
        logs_dir = Path("logs/events")
        # Give a time buffer of a few minutes for file system delays
        run_start_time = datetime.now().timestamp() - 300

        latest_log_file = find_latest_file(logs_dir, f"*{run_id}*.jsonl")
        if not latest_log_file:
            latest_log_file = find_latest_file(logs_dir, "*.jsonl")

        if latest_log_file and latest_log_file.stat().st_mtime > run_start_time:
            logging.info(f"Confirmed: Recent log file found -> {latest_log_file}")
        elif latest_log_file:
            logging.warning(
                f"A log file was found ({latest_log_file}), "
                f"but it does not seem to be from this run."
            )
        else:
            logging.error("Could not find any .jsonl log file in logs/events/.")

        # 2. Confirm .parquet result file
        parquet_path_str = summary.get("parquet_path")
        if parquet_path_str:
            parquet_path = Path(parquet_path_str)
            if parquet_path.exists():
                logging.info(f"Confirmed: Parquet result file found -> {parquet_path}")
            else:
                logging.error(f"Parquet file path reported but not found at: {parquet_path}")
        else:
            logging.error("Parquet file path not found in the run summary.")

    except Exception as e:
        logging.error(f"An error occurred during the flow execution: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
