"""Tests for logging utilities."""

import json
import tempfile
from pathlib import Path

from utils.logging import create_run_summary, log_event_jsonl, log_local_cot


def test_log_event_jsonl():
    """Test JSONL event logging with token counting."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test event
        event = {
            "run_id": "test-run-001",
            "problem_id": "gsm8k-001",
            "prompt": "What is 2 + 2?",
            "completion": "The answer is 4.",
            "phase": "baseline",
        }

        # Log the event
        log_event_jsonl(event, model="gpt-4", log_dir=temp_dir)

        # Check that file was created
        log_files = list(Path(temp_dir).glob("events_*.jsonl"))
        assert len(log_files) == 1

        # Read and verify content
        with open(log_files[0], "r") as f:
            logged_event = json.loads(f.read().strip())

        # Check that required fields are present
        assert logged_event["run_id"] == "test-run-001"
        assert logged_event["problem_id"] == "gsm8k-001"
        assert "tokens" in logged_event
        assert "estimated_cost_usd" in logged_event
        assert "timestamp" in logged_event
        assert "model" in logged_event

        # Check that sensitive content was sanitized (no prompt/completion in clean log)
        assert "prompt" not in logged_event
        assert "completion" not in logged_event

        # Check token structure
        tokens = logged_event["tokens"]
        assert "prompt_tokens" in tokens
        assert "completion_tokens" in tokens
        assert "total_tokens" in tokens


def test_log_local_cot():
    """Test local CoT logging (unsanitized)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test event with CoT
        event = {
            "run_id": "test-run-002",
            "problem_id": "gsm8k-002",
            "prompt": "Solve this step by step: 5 * 6 = ?",
            "completion": "Let me think: 5 * 6 = 30",
            "chain_of_thought": "First I multiply 5 by 6...",
            "phase": "tas",
        }

        # Log locally
        log_local_cot(event, log_dir=temp_dir)

        # Check that file was created
        log_files = list(Path(temp_dir).glob("cot_*.jsonl"))
        assert len(log_files) == 1

        # Read and verify content
        with open(log_files[0], "r") as f:
            logged_event = json.loads(f.read().strip())

        # Check that ALL content is preserved (including sensitive)
        assert logged_event["prompt"] == "Solve this step by step: 5 * 6 = ?"
        assert logged_event["completion"] == "Let me think: 5 * 6 = 30"
        assert logged_event["chain_of_thought"] == "First I multiply 5 by 6..."
        assert "timestamp" in logged_event


def test_create_run_summary():
    """Test run summary creation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create summary
        create_run_summary(run_id="test-run-003", total_items=50, total_cost=2.34, log_dir=temp_dir)

        # Check that file was created
        summary_files = list(Path(temp_dir).glob("summary_*.json"))
        assert len(summary_files) == 1

        # Read and verify content
        with open(summary_files[0], "r") as f:
            summary = json.load(f)

        assert summary["run_id"] == "test-run-003"
        assert summary["total_items"] == 50
        assert summary["total_estimated_cost_usd"] == 2.34
        assert summary["status"] == "completed"
        assert "timestamp" in summary


def test_multiple_events_same_day():
    """Test that multiple events on same day go to same file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Log multiple events
        for i in range(3):
            event = {
                "run_id": f"test-run-{i:03d}",
                "problem_id": f"gsm8k-{i:03d}",
                "prompt": f"What is {i} + 1?",
                "completion": f"The answer is {i + 1}.",
                "phase": "baseline",
            }
            log_event_jsonl(event, log_dir=temp_dir)

        # Should only have one file
        log_files = list(Path(temp_dir).glob("events_*.jsonl"))
        assert len(log_files) == 1

        # Should have 3 lines
        with open(log_files[0], "r") as f:
            lines = f.read().strip().split("\n")
        assert len(lines) == 3

        # Each line should be valid JSON
        for line in lines:
            event = json.loads(line)
            assert "tokens" in event
            assert "estimated_cost_usd" in event
