"""Demo script for S2-09: Budget Monitoring and Token Caps.

This script demonstrates:
1. Per-item token cap enforcement (≤8k tokens/item)
2. Sprint budget monitoring with alerts at 90% threshold
3. Cost comparison reporting vs baseline (generation ≤1.5×)
"""

from src.utils.budget_monitor import (
    MAX_TOKENS_PER_ITEM,
    BudgetStatus,
    TokenUsage,
    calculate_budget_status,
    check_item_token_cap,
    create_budget_report_table,
    format_budget_alert,
    format_budget_summary,
    should_alert_budget,
)


def demo_token_cap():
    """Demonstrate token cap checking."""
    print("=" * 70)
    print("1. TOKEN CAP PER ITEM (≤8k tokens)")
    print("=" * 70)
    print(f"\nConfigured cap: {MAX_TOKENS_PER_ITEM:,} tokens/item\n")

    test_items = [
        TokenUsage("problem-001", 2000, 3000, 5000, 0.35, "tas_k1", "gpt-4"),
        TokenUsage("problem-002", 3000, 4500, 7500, 0.55, "tas_k1", "gpt-4"),
        TokenUsage("problem-003", 4000, 5000, 9000, 0.70, "tas_k1", "gpt-4"),
    ]

    for item in test_items:
        within_cap = check_item_token_cap(item)
        status = "✅ Within cap" if within_cap else "❌ EXCEEDS CAP"
        print(
            f"{item.problem_id}: {item.total_tokens:,} tokens "
            f"(${item.estimated_cost_usd:.4f}) - {status}"
        )


def demo_budget_monitoring():
    """Demonstrate budget monitoring and alerts."""
    print("\n" + "=" * 70)
    print("2. BUDGET MONITORING & ALERTS")
    print("=" * 70)

    # Simulate a run with increasing token usage
    results = []
    for i in range(1, 101):
        # Simulate increasing complexity: some items use more tokens
        base_tokens = 5000 + (i * 20)  # Gradually increasing
        if i % 10 == 0:
            base_tokens += 2000  # Some problems are harder

        results.append(
            {
                "problem_id": f"gsm8k-{i:03d}",
                "tas_usage": {
                    "prompt_tokens": int(base_tokens * 0.6),
                    "completion_tokens": int(base_tokens * 0.4),
                    "total_tokens": base_tokens,
                },
                "estimated_cost_usd": base_tokens * 0.00007,  # ~$0.07 per 1k tokens avg
            }
        )

    # Baseline stats (from Sprint 1)
    baseline_stats = {
        "total_tokens": 400000,  # 200 items × 2000 tokens avg
        "total_cost_usd": 28.0,
        "num_items": 200,
    }

    print("\n📋 Simulating Sprint 2 Run...")
    print("   Total items planned: 200")
    print("   Budget limit: $60.00")
    print(f"   Baseline cost: ${baseline_stats['total_cost_usd']:.2f}\n")

    # Check at different progress points
    checkpoints = [50, 75, 90, 100]

    for checkpoint in checkpoints:
        status = calculate_budget_status(
            run_id="s2-tas-k1-demo",
            processed_results=results[:checkpoint],
            total_items=200,
            budget_limit_usd=60.0,
            baseline_stats=baseline_stats,
        )

        print(f"\n{'─' * 70}")
        print(f"After {checkpoint} items:")
        print(f"  Tokens: {status.total_tokens:,}")
        print(f"  Cost: ${status.total_cost_usd:.2f}")
        print(f"  Budget used: {status.budget_used_pct:.1f}%")
        print(f"  Projected total: ${status.projected_total_cost:.2f}")

        if status.cost_vs_baseline_ratio:
            print(f"  vs Baseline: {status.cost_vs_baseline_ratio:.2f}×")

        if status.items_over_cap:
            print(f"  ⚠️  Items over cap: {len(status.items_over_cap)}")

        # Check if alert should trigger
        if should_alert_budget(status):
            print("\n  🚨 ALERT TRIGGERED!")


def demo_budget_alert():
    """Demonstrate budget alert formatting."""
    print("\n" + "=" * 70)
    print("3. BUDGET ALERT FORMAT")
    print("=" * 70)

    # Create a status that will trigger alert
    status = BudgetStatus(
        run_id="s2-tas-k1-20251119",
        total_items=200,
        processed_items=150,
        total_tokens=825000,
        total_cost_usd=55.0,
        budget_limit_usd=60.0,
        baseline_tokens=400000,
        baseline_cost_usd=28.0,
        items_over_cap=["gsm8k-042", "gsm8k-089", "gsm8k-127"],
    )

    alert = format_budget_alert(status)
    print(f"\n{alert}")


def demo_budget_summary():
    """Demonstrate budget summary report."""
    print("\n" + "=" * 70)
    print("4. BUDGET SUMMARY REPORT")
    print("=" * 70)

    status = BudgetStatus(
        run_id="s2-tas-k1-20251119",
        total_items=200,
        processed_items=200,
        total_tokens=1100000,
        total_cost_usd=70.0,
        budget_limit_usd=80.0,
        baseline_tokens=400000,
        baseline_cost_usd=28.0,
        items_over_cap=["gsm8k-042", "gsm8k-089"],
    )

    summary = format_budget_summary(status)
    print(f"\n{summary}")

    print("\n\nInterpretation:")
    if status.is_within_budget_target(target_multiplier=1.5):
        print("✅ Within target: Cost is ≤1.5× baseline")
    else:
        print("❌ Exceeds target: Cost is >1.5× baseline")


def demo_comparison_table():
    """Demonstrate budget comparison table."""
    print("\n" + "=" * 70)
    print("5. MULTI-RUN COMPARISON TABLE")
    print("=" * 70)

    # Create comparison between baseline, TAS k=1, and TAS+MAMV
    runs = [
        BudgetStatus(
            run_id="s1-baseline-seed42",
            total_items=200,
            processed_items=200,
            total_tokens=400000,
            total_cost_usd=28.0,
            budget_limit_usd=30.0,
            baseline_tokens=400000,
            baseline_cost_usd=28.0,
        ),
        BudgetStatus(
            run_id="s2-tas-k1-seed101",
            total_items=200,
            processed_items=200,
            total_tokens=1100000,
            total_cost_usd=38.0,
            budget_limit_usd=50.0,
            baseline_tokens=400000,
            baseline_cost_usd=28.0,
        ),
        BudgetStatus(
            run_id="s2-mamv-seed101",
            total_items=200,
            processed_items=180,
            total_tokens=2800000,
            total_cost_usd=95.0,
            budget_limit_usd=100.0,
            baseline_tokens=400000,
            baseline_cost_usd=28.0,
        ),
    ]

    table = create_budget_report_table(runs)
    print(f"\n{table}\n")

    print("Notes:")
    print("  • Baseline: Single LLM call per problem")
    print("  • TAS k=1: Thesis → Antithesis → Synthesis (3 calls)")
    print("  • MAMV: TAS with 3 temperature instances (9 calls)")
    print("  • Target: ≤1.5× baseline cost for generation")


def demo_parquet_loading():
    """Demonstrate loading baseline stats from Parquet."""
    print("\n" + "=" * 70)
    print("6. LOADING BASELINE FROM PARQUET")
    print("=" * 70)

    # Note: This will only work if you have actual parquet files
    print("\nTo load baseline stats from a Parquet file:")
    print("```python")
    print("from src.utils.budget_monitor import load_baseline_stats_from_parquet")
    print("")
    print('baseline = load_baseline_stats_from_parquet("analytics/parquet/baseline_200.parquet")')
    print("print(f'Baseline tokens: {baseline[\"total_tokens\"]:,}')")
    print("print(f'Baseline cost: ${baseline[\"total_cost_usd\"]:.2f}')")
    print("```")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print(" S2-09: BUDGET MONITORING & TOKEN CAPS - DEMO")
    print("=" * 70)

    demo_token_cap()
    demo_budget_monitoring()
    demo_budget_alert()
    demo_budget_summary()
    demo_comparison_table()
    demo_parquet_loading()

    print("\n" + "=" * 70)
    print("✅ S2-09 IMPLEMENTATION COMPLETE")
    print("=" * 70)
    print("\nKey Features:")
    print(f"  • Token cap per item: ≤{MAX_TOKENS_PER_ITEM:,} tokens")
    print("  • Budget alert threshold: 90% of limit")
    print("  • Target: ≤1.5× baseline cost for generation")
    print("  • Real-time monitoring with projections")
    print("  • Multi-run comparison tables")
    print("  • Parquet integration for baseline stats")
    print()


if __name__ == "__main__":
    main()
