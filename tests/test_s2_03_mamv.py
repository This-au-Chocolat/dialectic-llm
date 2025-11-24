"""
Test suite for S2-03: MAMV (Majority Voting Multiple Instances).

Tests the MAMV implementation including:
- Majority voting logic (2 of 3, 3 of 3)
- Tie-breaking (default temperature selection)
- Vote traceability
- Integration with T-A-S flow
"""

import pytest

from src.flows.tas import TASFlowConfig, extract_numeric_answer, majority_vote, run_tas_mamv


class TestMAMVVotingLogic:
    """Test suite for MAMV voting logic (S2-03)."""

    def test_unanimous_vote_3_of_3(self):
        """Test unanimous vote (all 3 instances agree)."""
        answers = [
            "The answer is 42. Final: 42",
            "After calculation, Final: 42",
            "Therefore the answer is Final: 42",
        ]
        temps = [0.65, 0.70, 0.75]
        seeds = [101, 202, 303]

        result = majority_vote(answers, temps, seeds)

        assert result["final_answer"] == "42"
        assert result["decision_method"] == "majority_3_of_3"
        assert len(result["votes"]) == 3
        assert result["vote_counts"]["42"] == 3

    def test_majority_vote_2_of_3(self):
        """Test simple majority (2 instances agree, 1 disagrees)."""
        answers = [
            "The answer is 100. Final: 100",
            "After calculation, Final: 100",
            "Therefore the answer is Final: 50",  # Minority vote
        ]
        temps = [0.65, 0.70, 0.75]
        seeds = [101, 202, 303]

        result = majority_vote(answers, temps, seeds)

        assert result["final_answer"] == "100"
        assert result["decision_method"] == "majority_2_of_3"
        assert len(result["votes"]) == 3
        assert result["vote_counts"]["100"] == 2
        assert result["vote_counts"]["50"] == 1

    def test_triple_tie_uses_default_temperature(self):
        """Test tie-breaking: all 3 instances disagree, use default temp (0.70)."""
        answers = [
            "The answer is 10. Final: 10",  # T=0.65
            "After calculation, Final: 20",  # T=0.70 <- default
            "Therefore the answer is Final: 30",  # T=0.75
        ]
        temps = [0.65, 0.70, 0.75]
        seeds = [101, 202, 303]

        result = majority_vote(answers, temps, seeds)

        # Should pick the answer from T=0.70 (middle instance)
        assert result["final_answer"] == "20"
        assert result["decision_method"] == "tie_break_default_temp"
        assert len(result["votes"]) == 3
        assert result["vote_counts"]["10"] == 1
        assert result["vote_counts"]["20"] == 1
        assert result["vote_counts"]["30"] == 1

    def test_vote_traceability(self):
        """Test that all votes are traceable with metadata."""
        answers = ["Answer: Final: 42", "Result: Final: 42", "Solution: Final: 42"]
        temps = [0.65, 0.70, 0.75]
        seeds = [101, 202, 303]

        result = majority_vote(answers, temps, seeds)

        # Check traceability
        assert len(result["votes"]) == 3
        for i, vote in enumerate(result["votes"]):
            assert vote["instance"] == i
            assert vote["temperature"] == temps[i]
            assert vote["seed"] == seeds[i]
            assert vote["extracted_answer"] == "42"
            assert "raw_text" in vote

    def test_no_valid_answers(self):
        """Test handling of cases where no numeric answer can be extracted."""
        answers = ["I don't know the answer.", "This problem is unclear.", "Cannot determine."]
        temps = [0.65, 0.70, 0.75]
        seeds = [101, 202, 303]

        result = majority_vote(answers, temps, seeds)

        assert result["final_answer"] is None
        assert result["decision_method"] == "no_valid_answers"
        assert len(result["votes"]) == 3

    def test_partial_valid_answers(self):
        """Test when some instances fail to extract numeric answer."""
        answers = [
            "The answer is 100. Final: 100",
            "Cannot solve this problem.",
            "The answer is 100. Final: 100",
        ]
        temps = [0.65, 0.70, 0.75]
        seeds = [101, 202, 303]

        result = majority_vote(answers, temps, seeds)

        # Two valid votes for 100, one None
        assert result["final_answer"] == "100"
        assert result["decision_method"] == "majority_2_of_3"


class TestNumericAnswerExtraction:
    """Test numeric answer extraction used by MAMV."""

    def test_extract_numeric_simple(self):
        """Test extraction of simple numeric answers."""
        text = "The calculation gives us 42. Final: 42"
        result = extract_numeric_answer(text)
        assert result == "42"

    def test_extract_numeric_with_commas(self):
        """Test extraction with thousands separators."""
        text = "The total is 1,234. Final: 1,234"
        result = extract_numeric_answer(text)
        # Should normalize to remove commas
        assert result is not None

    def test_extract_numeric_decimal(self):
        """Test extraction of decimal numbers."""
        text = "The result is 3.14159. Final: 3.14159"
        result = extract_numeric_answer(text)
        assert result is not None

    def test_extract_numeric_no_answer(self):
        """Test when no numeric answer is present."""
        text = "I cannot solve this problem."
        result = extract_numeric_answer(text)
        assert result is None


class TestMAMVIntegration:
    """Integration tests for MAMV flow."""

    @pytest.mark.skip(reason="Requires OpenAI API key and costs money")
    def test_run_tas_mamv_integration(self):
        """
        Integration test for run_tas_mamv flow.

        Note: Skipped by default as it makes real API calls.
        Run with: pytest -v -k test_run_tas_mamv_integration --no-skip
        """
        problem = {
            "problem_id": "test-mamv-1",
            "question": "If John has 5 apples and buys 3 more, how many apples does he have?",
            "answer": "8",
        }

        config = TASFlowConfig(
            run_id="test-mamv-integration", dataset_name="test", model_name="gpt-3.5-turbo", seed=42
        )

        result = run_tas_mamv(problem, config)

        # Verify structure
        assert "instances" in result
        assert len(result["instances"]) == 3
        assert "mamv_result" in result
        assert "final_answer" in result
        assert "decision_method" in result

        # Verify each instance has different temperature
        temps = [inst["temperature"] for inst in result["instances"]]
        assert temps == [0.65, 0.70, 0.75]

        # Verify voting metadata
        assert result["mamv_result"]["decision_method"] in [
            "majority_2_of_3",
            "majority_3_of_3",
            "tie_break_default_temp",
        ]

    def test_mamv_config_loaded(self):
        """Test that MAMV configuration is loaded correctly."""
        from src.utils.config import get_tas_config

        config = get_tas_config()

        temps = config.get_thesis_temperatures()
        seeds = config.get_mamv_seeds()

        assert len(temps) == 3
        assert len(seeds) == 3
        assert temps == [0.65, 0.70, 0.75]
        assert seeds == [101, 202, 303]


class TestMAMVAcceptanceCriteria:
    """
    Test acceptance criteria for S2-03.

    Acceptance: synthesis_mamv() returns decision and votes; unit test basic.
    """

    def test_mamv_returns_decision_and_votes(self):
        """
        Test that MAMV function returns both decision and votes.

        This validates the main acceptance criterion for S2-03.
        """
        answers = ["Final: 42", "Final: 42", "Final: 50"]
        temps = [0.65, 0.70, 0.75]
        seeds = [101, 202, 303]

        result = majority_vote(answers, temps, seeds)

        # Must return decision
        assert "final_answer" in result
        assert result["final_answer"] is not None

        # Must return votes with traceability
        assert "votes" in result
        assert len(result["votes"]) == 3

        # Must have vote counts
        assert "vote_counts" in result

        # Must have decision method
        assert "decision_method" in result

        # Each vote must have traceability metadata
        for vote in result["votes"]:
            assert "instance" in vote
            assert "temperature" in vote
            assert "seed" in vote
            assert "extracted_answer" in vote
            assert "raw_text" in vote

        print("✅ S2-03 acceptance criteria verified: decision + votes returned")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
