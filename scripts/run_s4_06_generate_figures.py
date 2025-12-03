# scripts/run_s4_06_generate_figures.py
"""
Generates bar charts visualizing ΔAcc vs Cost for each dataset.
Task: S4-06
DoD: PNG formal para paper (ambos datasets)
Dependencies: S4-03 (kpi_final_s4.parquet)
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Define constants
BASE_DIR = Path(__file__).parent.parent
RELEASES_DIR = BASE_DIR / "releases" / "v1.0"
RESULTS_DIR = RELEASES_DIR / "results"
FIGS_DIR = RELEASES_DIR / "figs"
KPI_FILE = RESULTS_DIR / "kpi_final_s4.parquet"

# Ensure output directories exist
FIGS_DIR.mkdir(parents=True, exist_ok=True)

# Define colors and styles
ACC_COLOR = "#1f77b4"  # Matplotlib default blue for accuracy
TOKENS_COLOR = "#8B5CF6"  # Purple accent for tokens (as per spec)
BAR_WIDTH = 0.35


def plot_kpis(df_kpi: pd.DataFrame, dataset_name: str):
    """
    Generates a dual-axis bar chart for a given dataset, showing accuracy and tokens.
    """
    df_dataset = df_kpi[df_kpi["dataset"] == dataset_name.lower()].copy()

    # Define the order of experiments for plotting
    experiment_order = ["baseline", "tas", "mamv"]
    df_dataset["experiment"] = pd.Categorical(
        df_dataset["experiment"], categories=experiment_order, ordered=True
    )
    df_dataset = df_dataset.sort_values("experiment")

    # Filter out MAMV if not applicable (i.e., if cost_usd is NA)
    # The plot should only show what was actually run
    if dataset_name.lower() == "truthful_qa":
        df_dataset = df_dataset[df_dataset["experiment"] != "mamv"]

    # Prepare data for plotting
    experiments = df_dataset["experiment"].apply(lambda x: x.upper().replace("_", "-")).tolist()
    accuracy = df_dataset["accuracy_pct"].fillna(0).tolist()
    total_tokens_k = (df_dataset["total_tokens"] / 1000).fillna(0).tolist()  # Convert to K tokens

    # Set up the plot
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Bar positions
    x = np.arange(len(experiments))

    # Plot Accuracy on primary Y-axis
    ax1.bar(x, accuracy, BAR_WIDTH, label="Accuracy (%)", color=ACC_COLOR)
    ax1.set_xlabel("Experimento")
    ax1.set_ylabel("Accuracy (%)", color=ACC_COLOR)
    ax1.tick_params(axis="y", labelcolor=ACC_COLOR)
    ax1.set_ylim(0, 100)  # Accuracy is always between 0-100%

    # Plot Tokens on secondary Y-axis
    ax2 = ax1.twinx()
    ax2.bar(x + BAR_WIDTH, total_tokens_k, BAR_WIDTH, label="Tokens (miles)", color=TOKENS_COLOR)
    ax2.set_ylabel("Tokens (miles)", color=TOKENS_COLOR)
    ax2.tick_params(axis="y", labelcolor=TOKENS_COLOR)
    ax2.set_yscale("log")  # Use log scale for tokens due to large differences
    ax2.set_ylim(1, 1000)  # Adjust as needed, 1k to 1M tokens

    # Set X-axis ticks and labels
    ax1.set_xticks(x + BAR_WIDTH / 2)
    ax1.set_xticklabels(experiments)

    # Add titles and legend
    plt.title(f"ΔAccuracy vs Cost (Tokens) for {dataset_name.upper()}")
    fig.tight_layout()  # Adjust layout to prevent labels overlapping

    # Combine legends from both axes
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc="upper left")

    # Save the figure
    output_filename = FIGS_DIR / f"fig_acc_cost_{dataset_name.lower()}.png"
    plt.savefig(output_filename, dpi=300, bbox_inches="tight")
    logging.info(f"Generated figure: {output_filename}")
    plt.close(fig)  # Close the figure to free memory


def main():
    """
    Main function to orchestrate the generation of KPI figures.
    """
    logging.info("Starting S4-06: Generate Figures ΔAcc vs Cost.")

    if not KPI_FILE.exists():
        logging.error(f"KPI file not found: {KPI_FILE}")
        logging.error("Cannot generate figures. Please run S4-03 first.")
        return

    df_kpi = pd.read_parquet(KPI_FILE)
    logging.info(f"Loaded KPI data from {KPI_FILE}")

    for dataset_name in df_kpi["dataset"].unique():
        plot_kpis(df_kpi, dataset_name)

    logging.info("S4-06 Figure generation script finished.")


if __name__ == "__main__":
    main()
