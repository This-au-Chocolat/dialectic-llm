import json
import os
from pathlib import Path


def check_pilot_log_file():
    """
    Opens the latest pilot_50.jsonl log file from logs/events/.
    Checks that each entry in the JSON lines file:
    - Has keys: 'thesis', 'antithesis', 'synthesis', and 'final_answer'
    - Does NOT contain sensitive strings like 'OPENAI_API_KEY', 'system_prompt', or 'raw_cot'
    Prints a warning if any entry is missing keys or contains forbidden tokens.
    """
    log_file_path = Path("logs/events/pilot_50.jsonl")

    if not log_file_path.exists():
        print(f"Warning: Log file not found at {log_file_path}")
        return

    required_keys = ["thesis", "antithesis", "synthesis", "final_answer"]
    forbidden_strings = ["OPENAI_API_KEY", "system_prompt", "raw_cot"]

    with open(log_file_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            try:
                entry = json.loads(line)

                # Check for required keys
                for key in required_keys:
                    if key not in entry:
                        print(
                            f"Warning in {log_file_path}, line {i + 1}: "
                            f"Missing required key '{key}' in entry: {entry}"
                        )

                # Check for forbidden strings
                entry_str = json.dumps(
                    entry
                )  # Convert entry back to string for sensitive content check
                for forbidden_str in forbidden_strings:
                    if forbidden_str in entry_str:
                        print(
                            f"Warning in {log_file_path}, line {i + 1}: "
                            f"Contains forbidden string '{forbidden_str}' in entry: {entry}"
                        )

            except json.JSONDecodeError as e:
                print(f"Error decoding JSON in {log_file_path}, line {i + 1}: {e}")
            except Exception as e:
                print(f"An unexpected error occurred in {log_file_path}, line {i + 1}: {e}")


if __name__ == "__main__":
    # Ensure this script can be run directly from the project root
    # or from within the src/utils directory.
    if Path("pyproject.toml").exists():  # Assume project root if pyproject.toml is there
        os.chdir(Path.cwd())
    else:
        # If in src/utils, move up two directories to project root
        os.chdir(Path(__file__).parents[2])

    check_pilot_log_file()
