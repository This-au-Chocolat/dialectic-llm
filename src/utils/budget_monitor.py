"""Budget monitoring and token cap utilities for Sprint 2.

This module provides:
1. Per-item token caps (≤8k tokens/item)
2. Sprint budget monitoring with alerts at 90% threshold
3. Cost comparison reporting vs baseline (generation ≤1.5×)

Task: S2-09 - Token caps por ítem y budget monitor por sprint
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pyarrow.parquet as pq


@dataclass
class TokenUsage:
    """Token usage for a single item."""

    problem_id: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    phase: str = "unknown"
    model: str = "gpt-4"


@dataclass
class BudgetStatus:
    """Current budget status for a sprint run."""

    run_id: str
    total_items: int
    processed_items: int
    total_tokens: int
    total_cost_usd: float
    budget_limit_usd: float
    baseline_tokens: Optional[int] = None
    baseline_cost_usd: Optional[float] = None
    items_over_cap: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def budget_used_pct(self) -> float:
        """Percentage of budget used."""
        if self.budget_limit_usd == 0:
            return 0.0
        return (self.total_cost_usd / self.budget_limit_usd) * 100

    @property
    def avg_tokens_per_item(self) -> float:
        """Average tokens per processed item."""
        if self.processed_items == 0:
            return 0.0
        return self.total_tokens / self.processed_items

    @property
    def projected_total_cost(self) -> float:
        """Projected total cost if all items are processed."""
        if self.processed_items == 0:
            return 0.0
        avg_cost_per_item = self.total_cost_usd / self.processed_items
        return avg_cost_per_item * self.total_items

    @property
    def tokens_vs_baseline_ratio(self) -> Optional[float]:
        """Token usage ratio vs baseline (None if baseline unknown)."""
        if self.baseline_tokens is None or self.baseline_tokens == 0:
            return None
        return self.total_tokens / self.baseline_tokens

    @property
    def cost_vs_baseline_ratio(self) -> Optional[float]:
        """Cost ratio vs baseline (None if baseline unknown)."""
        if self.baseline_cost_usd is None or self.baseline_cost_usd == 0:
            return None
        return self.total_cost_usd / self.baseline_cost_usd

    def is_within_budget_target(self, target_multiplier: float = 1.5) -> bool:
        """Check if within budget target (default ≤1.5× baseline)."""
        ratio = self.cost_vs_baseline_ratio
        if ratio is None:
            return True  # Can't check if no baseline
        return ratio <= target_multiplier


# Token cap per item (Sprint 2 requirement: ≤8k tokens/item)
MAX_TOKENS_PER_ITEM = 8000

# Budget alert threshold (Sprint 2 requirement: alert at 90%)
BUDGET_ALERT_THRESHOLD_PCT = 90.0


def check_item_token_cap(usage: TokenUsage, cap: int = MAX_TOKENS_PER_ITEM) -> bool:
    """
    Check if an item exceeds the token cap.

    Args:
        usage: Token usage for the item
        cap: Maximum tokens allowed per item (default: 8000)

    Returns:
        True if within cap, False if exceeds cap
    """
    return usage.total_tokens <= cap


def calculate_budget_status(
    run_id: str,
    processed_results: List[Dict],
    total_items: int,
    budget_limit_usd: float,
    baseline_stats: Optional[Dict] = None,
) -> BudgetStatus:
    """
    Calculate current budget status from processed results.

    Args:
        run_id: Run identifier
        processed_results: List of result dictionaries with token usage
        total_items: Total number of items to process
        budget_limit_usd: Budget limit in USD
        baseline_stats: Optional baseline statistics for comparison

    Returns:
        BudgetStatus with current state and projections
    """
    total_tokens = 0
    total_cost = 0.0
    items_over_cap = []

    for result in processed_results:
        # Extract token usage from result
        usage_dict = result.get("tas_usage") or result.get("usage") or {}
        tokens = usage_dict.get("total_tokens", 0)
        cost = result.get("estimated_cost_usd", 0.0)

        total_tokens += tokens
        total_cost += cost

        # Check if item exceeds cap
        if tokens > MAX_TOKENS_PER_ITEM:
            items_over_cap.append(result.get("problem_id", "unknown"))

    # Extract baseline stats if provided
    baseline_tokens = None
    baseline_cost = None
    if baseline_stats:
        baseline_tokens = baseline_stats.get("total_tokens")
        baseline_cost = baseline_stats.get("total_cost_usd")

    return BudgetStatus(
        run_id=run_id,
        total_items=total_items,
        processed_items=len(processed_results),
        total_tokens=total_tokens,
        total_cost_usd=total_cost,
        budget_limit_usd=budget_limit_usd,
        baseline_tokens=baseline_tokens,
        baseline_cost_usd=baseline_cost,
        items_over_cap=items_over_cap,
    )


def should_alert_budget(
    status: BudgetStatus, threshold_pct: float = BUDGET_ALERT_THRESHOLD_PCT
) -> bool:
    """
    Check if budget alert should be triggered.

    Args:
        status: Current budget status
        threshold_pct: Alert threshold percentage (default: 90%)

    Returns:
        True if alert should be triggered
    """
    # Alert if current usage exceeds threshold
    if status.budget_used_pct >= threshold_pct:
        return True

    # Alert if projected total would exceed budget
    if status.projected_total_cost >= status.budget_limit_usd:
        return True

    return False


def format_budget_alert(status: BudgetStatus) -> str:
    """
    Format budget alert message.

    Args:
        status: Current budget status

    Returns:
        Formatted alert message
    """
    lines = [
        "⚠️  BUDGET ALERT",
        f"Run ID: {status.run_id}",
        f"Progress: {status.processed_items}/{status.total_items} items",
        "",
        "Current Usage:",
        f"  Tokens: {status.total_tokens:,}",
        f"  Cost: ${status.total_cost_usd:.4f}",
        f"  Budget: ${status.budget_limit_usd:.2f}",
        f"  Used: {status.budget_used_pct:.1f}%",
        "",
        "Projections:",
        f"  Est. total cost: ${status.projected_total_cost:.4f}",
        f"  Avg tokens/item: {status.avg_tokens_per_item:.0f}",
    ]

    # Add baseline comparison if available
    if status.baseline_cost_usd:
        lines.extend(
            [
                "",
                "vs Baseline:",
                f"  Token ratio: {status.tokens_vs_baseline_ratio:.2f}×",
                f"  Cost ratio: {status.cost_vs_baseline_ratio:.2f}×",
                "  Target: ≤1.5×",
            ]
        )

    # Add token cap violations
    if status.items_over_cap:
        cap_items = ", ".join(status.items_over_cap[:5])
        suffix = "..." if len(status.items_over_cap) > 5 else ""
        lines.extend(
            [
                "",
                f"Items over {MAX_TOKENS_PER_ITEM:,} token cap: {len(status.items_over_cap)}",
                f"  {cap_items}{suffix}",
            ]
        )

    return "\n".join(lines)


def format_budget_summary(status: BudgetStatus) -> str:
    """
    Format budget summary report.

    Args:
        status: Budget status to format

    Returns:
        Formatted summary string
    """
    lines = [
        "📊 Budget Summary",
        f"Run: {status.run_id}",
        f"Timestamp: {status.timestamp}",
        "",
        f"Progress: {status.processed_items}/{status.total_items} items",
        "",
        "Token Usage:",
        f"  Total: {status.total_tokens:,}",
        f"  Avg/item: {status.avg_tokens_per_item:.0f}",
        f"  Items over cap: {len(status.items_over_cap)}",
        "",
        "Cost:",
        f"  Total: ${status.total_cost_usd:.4f}",
        f"  Budget: ${status.budget_limit_usd:.2f}",
        f"  Used: {status.budget_used_pct:.1f}%",
        f"  Projected: ${status.projected_total_cost:.4f}",
    ]

    # Add baseline comparison
    if status.baseline_cost_usd and status.baseline_tokens:
        ratio = status.cost_vs_baseline_ratio or 0
        token_ratio = status.tokens_vs_baseline_ratio or 0
        within_target = "✅" if status.is_within_budget_target() else "❌"

        lines.extend(
            [
                "",
                "vs Baseline:",
                f"  Baseline tokens: {status.baseline_tokens:,}",
                f"  Baseline cost: ${status.baseline_cost_usd:.4f}",
                f"  Token ratio: {token_ratio:.2f}×",
                f"  Cost ratio: {ratio:.2f}× {within_target}",
                "  Target: ≤1.5× baseline cost",
            ]
        )

    return "\n".join(lines)


def load_baseline_stats_from_parquet(parquet_path: str) -> Dict:
    """
    Load baseline statistics from a Parquet file.

    Args:
        parquet_path: Path to baseline Parquet file

    Returns:
        Dictionary with baseline stats (total_tokens, total_cost_usd)
    """
    path = Path(parquet_path)
    if not path.exists():
        return {}

    try:
        table = pq.read_table(parquet_path)
        df = table.to_pandas()

        # Calculate totals from tokens column (struct)
        total_tokens = 0
        if "tokens" in df.columns:
            for tokens_dict in df["tokens"]:
                if isinstance(tokens_dict, dict):
                    total_tokens += tokens_dict.get("total_tokens", 0)

        # Calculate total cost
        total_cost = 0.0
        if "estimated_cost_usd" in df.columns:
            total_cost = df["estimated_cost_usd"].sum()

        return {
            "total_tokens": int(total_tokens),
            "total_cost_usd": float(total_cost),
            "num_items": len(df),
        }

    except Exception as e:
        print(f"Warning: Could not load baseline stats from {parquet_path}: {e}")
        return {}


def create_budget_report_table(runs: List[BudgetStatus]) -> str:
    """
    Create a markdown table comparing budget across runs.

    Args:
        runs: List of BudgetStatus objects to compare

    Returns:
        Markdown formatted table
    """
    if not runs:
        return "No runs to compare."

    lines = [
        "| Run ID | Items | Tokens | Cost ($) | vs Baseline | Budget Used | Status |",
        "|--------|-------|--------|----------|-------------|-------------|--------|",
    ]

    for run in runs:
        run_id = run.run_id[:8]  # Truncate for readability
        items = f"{run.processed_items}/{run.total_items}"
        tokens = f"{run.total_tokens:,}"
        cost = f"{run.total_cost_usd:.4f}"

        vs_baseline = "N/A"
        if run.cost_vs_baseline_ratio:
            ratio = run.cost_vs_baseline_ratio
            vs_baseline = f"{ratio:.2f}×"

        budget_used = f"{run.budget_used_pct:.1f}%"

        status = "✅"
        if run.budget_used_pct >= 100:
            status = "❌ Over"
        elif run.budget_used_pct >= BUDGET_ALERT_THRESHOLD_PCT:
            status = "⚠️  Near"
        elif not run.is_within_budget_target():
            status = "⚠️  >1.5×"

        lines.append(
            f"| {run_id} | {items} | {tokens} | {cost} | {vs_baseline} | {budget_used} | {status} |"
        )

    return "\n".join(lines)
