"""Tests for budget monitoring and token caps (S2-09)."""

import pytest

from utils.budget_monitor import (
    BUDGET_ALERT_THRESHOLD_PCT,
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


def test_token_usage_creation():
    """Test TokenUsage dataclass creation."""
    usage = TokenUsage(
        problem_id="test-001",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        estimated_cost_usd=0.015,
        phase="thesis",
        model="gpt-4",
    )

    assert usage.problem_id == "test-001"
    assert usage.total_tokens == 150
    assert usage.estimated_cost_usd == 0.015


def test_check_item_token_cap_within():
    """Test token cap check for item within limit."""
    usage = TokenUsage(
        problem_id="test-001",
        prompt_tokens=3000,
        completion_tokens=4000,
        total_tokens=7000,
        estimated_cost_usd=0.5,
    )

    assert check_item_token_cap(usage, cap=MAX_TOKENS_PER_ITEM)
    assert usage.total_tokens <= MAX_TOKENS_PER_ITEM


def test_check_item_token_cap_exceeds():
    """Test token cap check for item exceeding limit."""
    usage = TokenUsage(
        problem_id="test-002",
        prompt_tokens=5000,
        completion_tokens=4000,
        total_tokens=9000,
        estimated_cost_usd=0.8,
    )

    assert not check_item_token_cap(usage, cap=MAX_TOKENS_PER_ITEM)
    assert usage.total_tokens > MAX_TOKENS_PER_ITEM


def test_budget_status_properties():
    """Test BudgetStatus computed properties."""
    status = BudgetStatus(
        run_id="test-run-001",
        total_items=200,
        processed_items=100,
        total_tokens=500000,
        total_cost_usd=25.0,
        budget_limit_usd=50.0,
        baseline_tokens=400000,
        baseline_cost_usd=20.0,
    )

    # Basic properties
    assert status.budget_used_pct == 50.0
    assert status.avg_tokens_per_item == 5000.0
    assert status.projected_total_cost == 50.0

    # Baseline comparisons
    assert status.tokens_vs_baseline_ratio == 1.25
    assert status.cost_vs_baseline_ratio == 1.25
    assert status.is_within_budget_target(target_multiplier=1.5)
    assert not status.is_within_budget_target(target_multiplier=1.0)


def test_budget_status_no_baseline():
    """Test BudgetStatus without baseline data."""
    status = BudgetStatus(
        run_id="test-run-002",
        total_items=100,
        processed_items=50,
        total_tokens=300000,
        total_cost_usd=15.0,
        budget_limit_usd=30.0,
    )

    assert status.tokens_vs_baseline_ratio is None
    assert status.cost_vs_baseline_ratio is None
    assert status.is_within_budget_target()  # Should return True when no baseline


def test_calculate_budget_status_basic():
    """Test basic budget status calculation."""
    results = [
        {
            "problem_id": "test-001",
            "tas_usage": {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500},
            "estimated_cost_usd": 0.1,
        },
        {
            "problem_id": "test-002",
            "tas_usage": {"prompt_tokens": 2000, "completion_tokens": 1000, "total_tokens": 3000},
            "estimated_cost_usd": 0.2,
        },
    ]

    status = calculate_budget_status(
        run_id="test-run", processed_results=results, total_items=10, budget_limit_usd=5.0
    )

    assert status.run_id == "test-run"
    assert status.total_items == 10
    assert status.processed_items == 2
    assert status.total_tokens == 4500
    assert status.total_cost_usd == pytest.approx(0.3)
    assert status.budget_limit_usd == 5.0


def test_calculate_budget_status_with_baseline():
    """Test budget status calculation with baseline comparison."""
    results = [
        {
            "problem_id": "test-001",
            "usage": {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500},
            "estimated_cost_usd": 0.15,
        }
    ]

    baseline_stats = {"total_tokens": 1000, "total_cost_usd": 0.10}

    status = calculate_budget_status(
        run_id="test-run",
        processed_results=results,
        total_items=1,
        budget_limit_usd=1.0,
        baseline_stats=baseline_stats,
    )

    assert status.baseline_tokens == 1000
    assert status.baseline_cost_usd == 0.10
    assert status.tokens_vs_baseline_ratio == pytest.approx(1.5)
    assert status.cost_vs_baseline_ratio == pytest.approx(1.5)


def test_calculate_budget_status_items_over_cap():
    """Test detection of items exceeding token cap."""
    results = [
        {
            "problem_id": "normal-001",
            "tas_usage": {"total_tokens": 5000},
            "estimated_cost_usd": 0.3,
        },
        {
            "problem_id": "over-001",
            "tas_usage": {"total_tokens": 9000},
            "estimated_cost_usd": 0.6,
        },
        {
            "problem_id": "over-002",
            "tas_usage": {"total_tokens": 10000},
            "estimated_cost_usd": 0.7,
        },
    ]

    status = calculate_budget_status(
        run_id="test-run", processed_results=results, total_items=3, budget_limit_usd=10.0
    )

    assert len(status.items_over_cap) == 2
    assert "over-001" in status.items_over_cap
    assert "over-002" in status.items_over_cap
    assert "normal-001" not in status.items_over_cap


def test_should_alert_budget_threshold():
    """Test budget alert at threshold."""
    # At 90% threshold
    status = BudgetStatus(
        run_id="test-run",
        total_items=100,
        processed_items=90,
        total_tokens=450000,
        total_cost_usd=45.0,
        budget_limit_usd=50.0,
    )

    assert should_alert_budget(status, threshold_pct=90.0)

    # Below threshold
    status.total_cost_usd = 40.0
    assert not should_alert_budget(status, threshold_pct=90.0)


def test_should_alert_budget_projection():
    """Test budget alert based on projection."""
    # Projected cost would exceed budget
    status = BudgetStatus(
        run_id="test-run",
        total_items=200,
        processed_items=100,
        total_tokens=250000,
        total_cost_usd=30.0,  # Current: 30, Projected: 60
        budget_limit_usd=50.0,
    )

    assert should_alert_budget(status)


def test_format_budget_alert():
    """Test budget alert formatting."""
    status = BudgetStatus(
        run_id="test-run-123",
        total_items=200,
        processed_items=150,
        total_tokens=750000,
        total_cost_usd=45.0,
        budget_limit_usd=50.0,
        baseline_tokens=600000,
        baseline_cost_usd=30.0,
        items_over_cap=["problem-001", "problem-002"],
    )

    alert = format_budget_alert(status)

    assert "⚠️  BUDGET ALERT" in alert
    assert "test-run-123" in alert
    assert "150/200" in alert
    assert "750,000" in alert
    assert "$45.00" in alert
    assert "90.0%" in alert
    assert "1.25×" in alert  # Cost ratio
    assert "Items over" in alert


def test_format_budget_summary():
    """Test budget summary formatting."""
    status = BudgetStatus(
        run_id="test-run-456",
        total_items=200,
        processed_items=200,
        total_tokens=1000000,
        total_cost_usd=55.0,
        budget_limit_usd=60.0,
        baseline_tokens=800000,
        baseline_cost_usd=40.0,
    )

    summary = format_budget_summary(status)

    assert "📊 Budget Summary" in summary
    assert "test-run-456" in summary
    assert "200/200" in summary
    assert "1,000,000" in summary
    assert "$55.00" in summary
    assert "1.38×" in summary  # Cost ratio
    assert "✅" in summary or "❌" in summary  # Status indicator


def test_create_budget_report_table():
    """Test budget report table creation."""
    runs = [
        BudgetStatus(
            run_id="run-baseline",
            total_items=200,
            processed_items=200,
            total_tokens=800000,
            total_cost_usd=40.0,
            budget_limit_usd=50.0,
            baseline_tokens=800000,
            baseline_cost_usd=40.0,
        ),
        BudgetStatus(
            run_id="run-tas-k1",
            total_items=200,
            processed_items=200,
            total_tokens=1000000,
            total_cost_usd=50.0,
            budget_limit_usd=60.0,
            baseline_tokens=800000,
            baseline_cost_usd=40.0,
        ),
        BudgetStatus(
            run_id="run-mamv",
            total_items=200,
            processed_items=180,
            total_tokens=1200000,
            total_cost_usd=65.0,
            budget_limit_usd=80.0,
            baseline_tokens=800000,
            baseline_cost_usd=40.0,
        ),
    ]

    table = create_budget_report_table(runs)

    assert "| Run ID | Items | Tokens | Cost ($) |" in table
    assert "run-base" in table
    assert "run-tas-" in table
    assert "run-mamv" in table
    assert "200/200" in table
    assert "1,000,000" in table
    assert "1.25×" in table  # TAS vs baseline
    assert "✅" in table or "⚠️" in table or "❌" in table


def test_create_budget_report_table_empty():
    """Test budget report with no runs."""
    table = create_budget_report_table([])
    assert "No runs to compare" in table


def test_budget_alert_threshold_constant():
    """Test that budget alert threshold is set correctly."""
    assert BUDGET_ALERT_THRESHOLD_PCT == 90.0


def test_max_tokens_per_item_constant():
    """Test that max tokens per item is set correctly."""
    assert MAX_TOKENS_PER_ITEM == 8000
