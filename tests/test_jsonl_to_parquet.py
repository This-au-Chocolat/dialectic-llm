"""Tests for JSONL to Parquet conversion utility."""

import json
import tempfile
from pathlib import Path

import pandas as pd

from utils.jsonl_to_parquet import (
    aggregate_analytics_run,
    convert_directory_jsonl_to_parquet,
    convert_jsonl_to_parquet,
)


def test_convert_jsonl_to_parquet():
    """Test JSONL to Parquet conversion functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test JSONL data
        test_data = [
            {
                "run_id": "test-run-001",
                "problem_id": "gsm8k-001",
                "phase": "baseline",
                "timestamp": "2025-11-01T12:00:00",
                "tokens": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                "estimated_cost_usd": 0.005,
            },
            {
                "run_id": "test-run-001",
                "problem_id": "gsm8k-002",
                "phase": "baseline",
                "timestamp": "2025-11-01T12:01:00",
                "tokens": {"prompt_tokens": 120, "completion_tokens": 60, "total_tokens": 180},
                "estimated_cost_usd": 0.006,
            },
        ]

        # Write test JSONL file
        jsonl_file = Path(temp_dir) / "test.jsonl"
        with open(jsonl_file, "w") as f:
            for record in test_data:
                f.write(json.dumps(record) + "\n")

        # Convert to Parquet
        parquet_file = Path(temp_dir) / "test.parquet"
        convert_jsonl_to_parquet(str(jsonl_file), str(parquet_file))

        # Verify conversion
        assert parquet_file.exists()

        # Read back and verify data
        df = pd.read_parquet(parquet_file)
        assert len(df) == 2
        assert "run_id" in df.columns
        assert "problem_id" in df.columns
        assert "tokens" in df.columns
        assert df["run_id"].iloc[0] == "test-run-001"
        assert df["problem_id"].iloc[0] == "gsm8k-001"


def test_convert_empty_jsonl():
    """Test conversion with empty JSONL file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create empty JSONL file
        jsonl_file = Path(temp_dir) / "empty.jsonl"
        jsonl_file.touch()

        # Convert to Parquet
        parquet_file = Path(temp_dir) / "empty.parquet"
        convert_jsonl_to_parquet(str(jsonl_file), str(parquet_file))

        # Verify conversion creates empty Parquet
        assert parquet_file.exists()
        df = pd.read_parquet(parquet_file)
        assert len(df) == 0


def test_convert_with_nested_data():
    """Test conversion with nested JSON structures."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test data with nested structures
        test_data = [
            {
                "run_id": "test-nested",
                "metadata": {"model": "gpt-4", "temperature": 0.7},
                "results": [{"metric": "accuracy", "value": 0.85}],
            }
        ]

        # Write test JSONL file
        jsonl_file = Path(temp_dir) / "nested.jsonl"
        with open(jsonl_file, "w") as f:
            for record in test_data:
                f.write(json.dumps(record) + "\n")

        # Convert to Parquet
        parquet_file = Path(temp_dir) / "nested.parquet"
        convert_jsonl_to_parquet(str(jsonl_file), str(parquet_file))

        # Verify conversion preserves nested structures
        assert parquet_file.exists()
        df = pd.read_parquet(parquet_file)
        assert len(df) == 1
        assert "metadata" in df.columns
        assert "results" in df.columns


def test_convert_directory():
    """Test batch conversion of directory containing JSONL files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir) / "input"
        output_dir = Path(temp_dir) / "output"
        input_dir.mkdir()

        # Create multiple JSONL files
        test_files = ["events_20251101.jsonl", "events_20251102.jsonl", "summary.jsonl"]
        for filename in test_files:
            file_path = input_dir / filename
            with open(file_path, "w") as f:
                f.write(json.dumps({"file": filename, "test": True}) + "\n")

        # Convert directory
        created_files = convert_directory_jsonl_to_parquet(str(input_dir), str(output_dir))

        # Verify all files were converted
        assert len(created_files) == 3
        for created_file in created_files:
            assert Path(created_file).exists()
            assert created_file.endswith(".parquet")


def test_aggregate_analytics_run():
    """Test aggregation of events by run_id (main S1-10 functionality)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        events_dir = Path(temp_dir) / "events"
        output_dir = Path(temp_dir) / "analytics"
        events_dir.mkdir()

        # Create test events across multiple files
        run_001_events = [
            {"run_id": "test-run-001", "problem_id": "gsm8k-001", "phase": "baseline"},
            {"run_id": "test-run-001", "problem_id": "gsm8k-002", "phase": "baseline"},
        ]
        run_002_events = [{"run_id": "test-run-002", "problem_id": "gsm8k-001", "phase": "tas"}]

        # Write events to multiple JSONL files
        file1 = events_dir / "events_20251101.jsonl"
        with open(file1, "w") as f:
            for event in run_001_events + run_002_events[:1]:
                f.write(json.dumps(event) + "\n")

        file2 = events_dir / "events_20251102.jsonl"
        with open(file2, "w") as f:
            for event in run_002_events:
                f.write(json.dumps(event) + "\n")

        # Aggregate run-001
        output_file = aggregate_analytics_run("test-run-001", str(events_dir), str(output_dir))

        # Verify aggregation
        assert Path(output_file).exists()
        df = pd.read_parquet(output_file)
        assert len(df) == 2  # Only run-001 events
        assert all(df["run_id"] == "test-run-001")
        assert set(df["problem_id"]) == {"gsm8k-001", "gsm8k-002"}
