#!/usr/bin/env python3
"""
Script to test the baseline runner without API calls.

This script demonstrates how to use the baseline flow and shows
the expected structure without spending money on API calls.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from llm.client import create_baseline_prompt, extract_gsm8k_answer


def test_prompt_creation():
    """Test prompt creation and answer extraction."""
    print("=== Testing Prompt Creation ===")

    question = "Janet has 16 books. She read 5 books. How many books does she have left?"
    prompt = create_baseline_prompt(question)

    print(f"Question: {question}")
    print(f"Prompt:\n{prompt}")
    print()

    # Test answer extraction
    print("=== Testing Answer Extraction ===")

    test_completions = [
        "Janet has 16 - 5 = 11 books left. #### 11",
        "Let me calculate: 16 books - 5 books = 11 books remaining. The answer is #### 11",
        "She started with 16 books and read 5, so 16 - 5 = 11. Therefore, Janet has 11 books left.",
    ]

    for i, completion in enumerate(test_completions, 1):
        answer = extract_gsm8k_answer(completion)
        print(f"Completion {i}: {completion[:50]}...")
        print(f"Extracted answer: '{answer}'")
        print()


def show_baseline_structure():
    """Show the structure of the baseline flow."""
    print("=== Baseline Flow Structure ===")

    # Show what would happen without API calls
    print("The baseline flow consists of:")
    print("1. load_gsm8k_batch() - Load problems from dataset")
    print("2. solve_baseline_problem() - For each problem:")
    print("   - Create baseline prompt")
    print("   - Call LLM API")
    print("   - Extract answer")
    print("   - Evaluate correctness")
    print("   - Log result")
    print("3. create_results_parquet() - Save results to analytics/")
    print("4. create_run_summary() - Create run summary")
    print()

    print("Required environment variables:")
    print("- OPENAI_API_KEY: Your OpenAI API key")
    print("- SANITIZE_SALT: Salt for hashing (optional)")
    print()

    print("To run the actual baseline (with API costs):")
    print("1. Set up your .env file with OPENAI_API_KEY")
    print(
        '2. Run: python -c "from flows.baseline import run_baseline_gsm8k; '
        'run_baseline_gsm8k(n_problems=5)"'
    )
    print()


def estimate_costs():
    """Estimate costs for different run sizes."""
    print("=== Cost Estimation ===")

    # Rough estimates based on typical GSM8K problems
    avg_prompt_tokens = 100  # Problem + instructions
    avg_completion_tokens = 150  # Solution steps

    # GPT-4 pricing (as of 2024)
    gpt4_prompt_cost = 0.03 / 1000  # $0.03 per 1K prompt tokens
    gpt4_completion_cost = 0.06 / 1000  # $0.06 per 1K completion tokens

    cost_per_item = (avg_prompt_tokens * gpt4_prompt_cost) + (
        avg_completion_tokens * gpt4_completion_cost
    )

    print(f"Estimated cost per problem (GPT-4): ${cost_per_item:.4f}")
    print()

    for n_problems in [5, 50, 200, 500]:
        total_cost = n_problems * cost_per_item
        print(f"{n_problems:3d} problems: ${total_cost:.2f}")

    print()
    print("Note: These are rough estimates. Actual costs may vary based on:")
    print("- Problem complexity")
    print("- Model responses length")
    print("- Current OpenAI pricing")


def main():
    """Main test function."""
    print("Dialectic LLM - Baseline Runner Test")
    print("=" * 50)
    print()

    test_prompt_creation()
    show_baseline_structure()
    estimate_costs()

    print("=== Next Steps ===")
    print("1. Set up your .env file with OPENAI_API_KEY")
    print("2. Start with a small test: run_baseline_gsm8k(n_problems=5)")
    print("3. Scale up to S1-06 requirement: run_baseline_gsm8k(n_problems=200)")


if __name__ == "__main__":
    main()
