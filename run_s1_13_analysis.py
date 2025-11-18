
import pandas as pd
from statsmodels.stats.contingency_tables import mcnemar


def analyze_(baseline_path, tas_path):
    print(f"Analyzing S1-13 with Baseline: {baseline_path} and TAS: {tas_path}\n")

    try:
        baseline_df = pd.read_parquet(baseline_path)
        tas_df = pd.read_parquet(tas_path)
    except Exception as e:
        print(f"Error loading parquet files: {e}")
        return

    # Ensure problem_ids are common for McNemar's test
    common_problem_ids = pd.merge(
        baseline_df[["problem_id"]], tas_df[["problem_id"]], on="problem_id", how="inner"
    )["problem_id"]

    if common_problem_ids.empty:
        print(
            "No common problem_ids found between baseline and TAS datasets. "
            "Cannot perform McNemar's test."
        )
        return

    baseline_common = baseline_df[baseline_df["problem_id"].isin(common_problem_ids)].set_index(
        "problem_id"
    )
    tas_common = tas_df[tas_df["problem_id"].isin(common_problem_ids)].set_index("problem_id")

    # Align dataframes based on common problem_ids
    aligned_df = pd.merge(
        baseline_common, tas_common, on="problem_id", suffixes=("_baseline", "_tas")
    )

    # McNemar's Test Preparation
    # a: Baseline Correct, TAS Incorrect
    # b: Baseline Incorrect, TAS Correct
    # c: Baseline Correct, TAS Correct
    # d: Baseline Incorrect, TAS Incorrect

    # The contingency table for McNemar's test is based on discordant pairs.
    # We need to count (Baseline Correct, TAS Incorrect) and (Baseline Incorrect, TAS Correct).
    b = aligned_df[
        (~aligned_df["is_correct_baseline"]) & (aligned_df["is_correct_tas"])
    ].shape[0]
    c = aligned_df[
        (aligned_df["is_correct_baseline"]) & (~aligned_df["is_correct_tas"])
    ].shape[0]

    # Check if we have enough discordant pairs for McNemar's test
    if (b + c) < 2:  # At least two discordant pairs are recommended for McNemar's.
        print(
            f"Not enough discordant pairs ({b + c}) to perform McNemar's test "
            "meaningfully. Need at least 2."
        )
        print(f"Baseline Correct, TAS Incorrect (c_count): {c}")
        print(f"Baseline Incorrect, TAS Correct (b_count): {b}")
        p_value = "N/A (Insufficient discordant pairs)"
    else:
        # Create a 2x2 table for mcnemar.
        # table[0,0] = Baseline correct, TAS correct
        # table[0,1] = Baseline correct, TAS incorrect
        # table[1,0] = Baseline incorrect, TAS correct
        # table[1,1] = Baseline incorrect, TAS incorrect

        n00 = aligned_df[
            (aligned_df["is_correct_baseline"]) & (aligned_df["is_correct_tas"])
        ].shape[0]
        n01 = c  # Baseline correct, TAS incorrect
        n10 = b  # Baseline incorrect, TAS correct
        n11 = aligned_df[
            (~aligned_df["is_correct_baseline"]) & (~aligned_df["is_correct_tas"])
        ].shape[0]

        table = [[n00, n01], [n10, n11]]

        contingency_table = pd.DataFrame(
            table,
            index=["Baseline Correct", "Baseline Incorrect"],
            columns=["TAS Correct", "TAS Incorrect"],
        )
        print(f"McNemar Contingency Table:\n{contingency_table}\n")

        result = mcnemar(table, exact=True)  # exact=True is good for small samples
        p_value = result.pvalue

    # Calculate KPIs
    accuracy_baseline = aligned_df["is_correct_baseline"].mean() * 100
    accuracy_tas = aligned_df["is_correct_tas"].mean() * 100
    delta_acc = accuracy_tas - accuracy_baseline

    avg_tokens_baseline = aligned_df["total_tokens_baseline"].mean()
    avg_tokens_tas = aligned_df["total_tokens_tas"].mean()

    # Report
    print("--- S1-13 Analysis Report ---")
    print(f"Common problems analyzed: {len(common_problem_ids)}")
    print(f"Baseline Accuracy: {accuracy_baseline:.2f}%")
    print(f"TAS Accuracy: {accuracy_tas:.2f}%")
    print(f"ΔAcc (TAS - Baseline): {delta_acc:.2f} percentage points")
    print(f"McNemar's p-value: {p_value}")
    print(f"Average Total Tokens (Baseline): {avg_tokens_baseline:.2f}")
    print(f"Average Total Tokens (TAS): {avg_tokens_tas:.2f}")
    print("\nNote: Small sample size might limit the statistical significance of McNemar's test.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python run__analysis.py <path_to_baseline.parquet> <path_to_tas.parquet>")
        sys.exit(1)

    baseline_file = sys.argv[1]
    tas_file = sys.argv[2]

    analyze_(baseline_file, tas_file)
