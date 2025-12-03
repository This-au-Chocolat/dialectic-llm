# scripts/run_s4_09_error_analysis.py
"""
Analyzes the distribution of error categories and extracts examples for S4-09.

Task: S4-09
DoD: Top-5 categorías con 1-2 ejemplos
Input: `analytics/parquet/error_taxonomy_labeled.parquet`
Output: Console output and `reports/error_taxonomy_report.md`
"""

import logging
from pathlib import Path

import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Define constants
BASE_DIR = Path(__file__).parent.parent
ANALYTICS_DIR = BASE_DIR / "analytics" / "parquet"
ERROR_TAXONOMY_FILE = ANALYTICS_DIR / "error_taxonomy_labeled.parquet"
CONSOLIDATED_FILE = BASE_DIR / "releases" / "v1.0" / "results" / "kpi_consolidated.parquet"
OUTPUT_REPORT = BASE_DIR / "reports" / "error_taxonomy_report.md"


def main():
    """
    Main function to perform error analysis and generate a report.
    """
    logging.info("Starting S4-09: Error Distribution + Examples.")

    if not ERROR_TAXONOMY_FILE.exists():
        logging.error(f"Error taxonomy file not found: {ERROR_TAXONOMY_FILE}")
        logging.error("Cannot perform error analysis. Please ensure S3-15 was completed.")
        return

    df_errors = pd.read_parquet(ERROR_TAXONOMY_FILE)
    df_errors = df_errors.rename(columns={"predicted_answer_raw": "predicted_answer"})
    logging.info(f"Loaded error taxonomy data from {ERROR_TAXONOMY_FILE}")

    # Load consolidated KPI data to get 'question' and clean 'predicted_answer'
    df_kpi_consolidated = pd.read_parquet(CONSOLIDATED_FILE)
    logging.info(f"Loaded consolidated KPI data from {CONSOLIDATED_FILE}")

    # Rename columns in df_kpi_consolidated to avoid conflicts
    df_kpi_consolidated_rebranded = df_kpi_consolidated[
        ["problem_id", "dataset", "question", "predicted_answer"]
    ].rename(columns={"question": "question_kpi", "predicted_answer": "predicted_answer_kpi"})

    # Merge df_errors with df_kpi_consolidated to get question and clean predicted_answer
    # We'll use a left merge to keep all error entries
    df_errors = pd.merge(
        df_errors, df_kpi_consolidated_rebranded, on=["problem_id", "dataset"], how="left"
    )

    # Fill missing values in 'question' and 'predicted_answer'
    df_errors["question"] = df_errors["question"].combine_first(df_errors["question_kpi"])
    df_errors["predicted_answer"] = df_errors["predicted_answer"].combine_first(
        df_errors["predicted_answer_kpi"]
    )

    # Drop the temporary columns
    df_errors = df_errors.drop(columns=["question_kpi", "predicted_answer_kpi"])

    # Ensure 'error_category' is treated as a string and handle potential NaNs
    df_errors["error_category"] = df_errors["error_category"].fillna("Uncategorized").astype(str)

    # --- Create errors_{dataset}.csv files ---
    OUTPUT_REPORTS_DIR = BASE_DIR / "reports"
    datasets = df_errors["dataset"].unique()
    for dataset in datasets:
        dataset_errors = df_errors[df_errors["dataset"] == dataset]
        error_distribution_dataset = dataset_errors["error_category"].value_counts().reset_index()
        error_distribution_dataset.columns = ["Category", "Count"]
        error_distribution_dataset["Percentage"] = (
            error_distribution_dataset["Count"] / error_distribution_dataset["Count"].sum() * 100
        )
        output_csv = OUTPUT_REPORTS_DIR / f"errors_{dataset}.csv"
        error_distribution_dataset.to_csv(output_csv, index=False)
        logging.info(f"Saved error distribution for dataset '{dataset}' to {output_csv}")

    # 1. Analyze error distribution
    error_distribution = df_errors["error_category"].value_counts().reset_index()
    error_distribution.columns = ["Category", "Count"]
    error_distribution["Percentage"] = (
        error_distribution["Count"] / error_distribution["Count"].sum() * 100
    )

    logging.info("\n--- Error Category Distribution ---")
    print(error_distribution.to_markdown(index=False, floatfmt=".2f"))

    # 2. Identify top 5 categories
    top_5_categories = error_distribution.head(5)["Category"].tolist()
    logging.info(f"\nTop 5 Error Categories: {', '.join(top_5_categories)}")

    # 3. Extract examples for top 5 categories
    examples_report = []

    examples_report.append("# S4-09: Análisis de Distribución de Errores y Ejemplos\n\n")
    examples_report.append("## Distribución de Categorías de Error\n")
    examples_report.append(error_distribution.to_markdown(index=False, floatfmt=".2f"))
    examples_report.append("\n\n")

    examples_report.append("## Ejemplos para las Top 5 Categorías de Error\n")

    for category in top_5_categories:
        logging.info(f"\n--- Examples for category: {category} ---")
        examples_report.append(f"### Categoría: {category}\n")

        # Filter for the current category and select unique problem_ids
        category_df = df_errors[df_errors["error_category"] == category].drop_duplicates(
            subset=["problem_id"]
        )

        # Take up to 2 examples
        selected_examples = category_df.head(2)

        if selected_examples.empty:
            logging.info(f"No examples found for category: {category}")
            examples_report.append("No se encontraron ejemplos para esta categoría.\n\n")
            continue

        for idx, example in selected_examples.iterrows():
            question = str(example["question"]) if pd.notna(example["question"]) else ""
            predicted_answer = (
                str(example["predicted_answer"]) if pd.notna(example["predicted_answer"]) else ""
            )

            example_text = (
                f"- **Dataset:** {example['dataset']}\n"
                f"- **Problem ID:** {example['problem_id']}\n"
                f"- **Pregunta:** {question}\n"
                f"- **Respuesta Correcta:** {example['true_answer']}\n"
                f"- **Respuesta Predicha:** {predicted_answer}\n\n"
            )
            logging.info(f"  Example for {example['problem_id']}:")
            logging.info(f"    Question: {question[:50]}...")
            logging.info(f"    Predicted: {predicted_answer[:50]}...")
            examples_report.append(example_text)

    # Save report to Markdown file
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.writelines(examples_report)

    logging.info(f"\nError analysis report saved to: {OUTPUT_REPORT}")
    logging.info("S4-09 Error analysis script finished.")


if __name__ == "__main__":
    main()
