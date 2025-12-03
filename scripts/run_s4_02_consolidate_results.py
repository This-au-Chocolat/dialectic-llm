# scripts/run_s4_02_consolidate_results.py
"""
Consolidates the results from S2 (GSM8K) and S3 (TQA) into a unified format.

Task: S4-02
DoD: Unified schema: baseline / T-A-S / MAMV.
Acceptance Criteria: releases/v1.0/results/*.{parquet,csv} with a valid schema.
"""

import logging
from pathlib import Path

import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Define constants
BASE_DIR = Path(__file__).parent.parent
ANALYTICS_DIR = BASE_DIR / "analytics"
RELEASES_DIR = BASE_DIR / "releases" / "v1.0" / "results"

# Define the unified schema columns
UNIFIED_COLUMNS = [
    "problem_id",
    "dataset",
    "experiment",
    "is_correct",
    "true_answer",
    "predicted_answer",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "run_id",
    "has_error",
    "question",
]

# --- File Mappings ---
# Maps source files to their experiment type and processing details.
# This is the single source of truth for the consolidation process.
FILE_MAPPINGS = {
    "gsm8k_baseline_s2": {
        "path": ANALYTICS_DIR / "parquet" / "baseline_baseline_20251127_152753_b9f53dc0.parquet",
        "experiment": "baseline",
        "dataset_name": "gsm8k",
        "rename_cols": {"predicted_answer": "predicted_answer"},
        "output_filename": "gsm8k_baseline_s2.parquet",
    },
    "gsm8k_tas_s2": {
        "path": ANALYTICS_DIR / "parquet" / "tas_s2_tas_deepseek_k1_FIXED_20251127_153923.parquet",
        "experiment": "tas",
        "dataset_name": "gsm8k",
        "rename_cols": {"predicted_answer_raw": "predicted_answer"},
        "output_filename": "gsm8k_tas_s2.parquet",
    },
    "gsm8k_mamv_s2": {
        "path": ANALYTICS_DIR / "parquet" / "mamv_results_s2_06_mamv_20251127_164429.parquet",
        "experiment": "mamv",
        "dataset_name": "gsm8k",
        "rename_cols": {"predicted_answer_raw": "predicted_answer"},
        "output_filename": "gsm8k_mamv_s2.parquet",
    },
    "tqa_baseline_s3": {
        "path": (
            ANALYTICS_DIR / "parquet" / "baseline_tqa_50_s3_baseline_tqa_20251202_152055.parquet"
        ),
        "experiment": "baseline",
        "dataset_name": "truthful_qa",
        "rename_cols": {"predicted_answer": "predicted_answer"},
        "output_filename": "tqa_baseline_s3.parquet",
    },
    "tqa_tas_s3": {
        "path": ANALYTICS_DIR / "parquet" / "tas_tqa_50_s3_tas_tqa_20251202_160525.parquet",
        "experiment": "tas",
        "dataset_name": "truthful_qa",
        "rename_cols": {"predicted_answer_raw": "predicted_answer"},
        "output_filename": "tqa_tas_s3.parquet",
    },
}


def normalize_problem_id(series: pd.Series) -> pd.Series:
    """Replaces '-' with '_' in problem_id for consistency."""
    return series.str.replace("-", "_", regex=False)


def load_and_transform(file_key: str, mapping: dict) -> pd.DataFrame | None:
    """
    Loads a single parquet file, applies transformations, and selects columns
    to match the unified schema.
    """
    path = mapping["path"]
    if not path.exists():
        logging.warning(f"File not found, skipping: {path}")
        return None

    logging.info(f"Processing file: {path.name}")
    df = pd.read_parquet(path)

    # 1. Add experiment and dataset identifiers
    df["experiment"] = mapping["experiment"]
    df["dataset"] = mapping["dataset_name"]

    # 2. Rename columns to unify schema
    df = df.rename(columns=mapping["rename_cols"])

    # 3. Normalize problem_id
    if "problem_id" in df.columns:
        df["problem_id"] = normalize_problem_id(df["problem_id"])

    # 4. Ensure all unified columns exist, filling missing ones with NaN
    for col in UNIFIED_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    # 5. Handle special cases
    # For MAMV, `has_error` is derived from the `error` column.
    # An empty string or NA should be considered as no error.
    if mapping["experiment"] == "mamv" and "error" in df.columns:
        df["has_error"] = df["error"].fillna("").astype(str).str.strip().astype(bool)

    # Handle predicted_answer specifically if not present after rename
    if "predicted_answer" not in df.columns:
        if "predicted_answer_raw" in df.columns:
            df["predicted_answer"] = df["predicted_answer_raw"]

    # Sanitize predicted_answer to remove CoT prefixes (e.g., "**SYNTHESIS APPROACH:**")
    # This ensures "no CoT en outputs públicos"
    if "predicted_answer" in df.columns:
        df["predicted_answer"] = (
            df["predicted_answer"]
            .astype(str)
            .str.replace(r"^\*\*SYNTHESIS APPROACH:\*\*.*", "", regex=True)
            .str.strip()
        )

    # 6. Select and reorder columns according to the unified schema
    df_unified = df[UNIFIED_COLUMNS].copy()

    # 7. Coerce types to prevent merge errors
    df_unified["is_correct"] = pd.to_numeric(df_unified["is_correct"], errors="coerce").astype(
        "boolean"
    )
    for token_col in ["prompt_tokens", "completion_tokens", "total_tokens"]:
        df_unified[token_col] = pd.to_numeric(df_unified[token_col], errors="coerce").astype(
            "Int64"
        )

    # Explicitly cast answer columns to string to avoid type inference errors
    df_unified["true_answer"] = df_unified["true_answer"].astype(str)
    df_unified["predicted_answer"] = df_unified["predicted_answer"].astype(str)

    return df_unified


def main():
    """
    Main function to orchestrate the consolidation of result files.
    """
    logging.info("Starting S4-02: Consolidate final tables.")
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    logging.info(f"Output directory: {RELEASES_DIR}")

    all_dfs = []

    for key, mapping in FILE_MAPPINGS.items():
        df = load_and_transform(key, mapping)
        if df is not None:
            all_dfs.append(df)

            # Save the normalized individual file
            output_path = RELEASES_DIR / mapping["output_filename"]
            df.to_parquet(output_path, index=False)
            logging.info(f"Saved normalized file: {output_path}")

    if not all_dfs:
        logging.error("No dataframes were loaded. No output generated.")
        return

    # Concatenate all dataframes into a single one
    consolidated_df = pd.concat(all_dfs, ignore_index=True)

    # Save the final consolidated file
    consolidated_path = RELEASES_DIR / "kpi_consolidated.parquet"
    consolidated_df.to_parquet(consolidated_path, index=False)

    logging.info(f"Successfully saved consolidated KPI file: {consolidated_path}")
    logging.info(f"Total rows in consolidated file: {len(consolidated_df)}")
    logging.info("S4-02 consolidation script finished.")


if __name__ == "__main__":
    main()
