"""Tests for baseline flow and LLM client."""

from unittest.mock import Mock, patch

import pytest

from llm.client import LLMClient, create_baseline_prompt, extract_gsm8k_answer


class TestLLMClient:
    """Tests for LLM client functionality."""

    def test_create_baseline_prompt(self):
        """Test baseline prompt creation."""
        question = "Sarah has 5 apples and buys 3 more. How many apples does she have?"
        prompt = create_baseline_prompt(question)

        assert question in prompt
        assert "step by step" in prompt.lower()
        assert "####" in prompt
        assert "[final_answer]" in prompt

    def test_extract_gsm8k_answer_with_format(self):
        """Test answer extraction with GSM8K format."""
        completion = """
        Let me solve this step by step.
        5 + 3 = 8
        #### 8
        """

        answer = extract_gsm8k_answer(completion)
        assert answer == "8"

    def test_extract_gsm8k_answer_with_text(self):
        """Test answer extraction with extra text."""
        completion = """
        The calculation is:
        5 + 3 = 8
        #### 8 apples
        """

        answer = extract_gsm8k_answer(completion)
        assert "8" in answer

    def test_extract_gsm8k_answer_fallback(self):
        """Test answer extraction fallback to last number."""
        completion = """
        First we have 5, then we add 3.
        The final result is 8.
        """

        answer = extract_gsm8k_answer(completion)
        assert "8" in answer

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_llm_client_init(self):
        """Test LLM client initialization."""
        client = LLMClient(model="gpt-4")
        assert client.default_model == "gpt-4"
        assert client.api_key == "test-key"

    def test_llm_client_no_api_key(self):
        """Test LLM client fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                LLMClient()


class TestBaselineFlow:
    """Tests for baseline flow components."""

    @patch("llm.client.OpenAI")
    def test_llm_call_success(self, mock_openai):
        """Test successful LLM call with mocked response."""
        # Mock the OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "The answer is 8. #### 8"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 70
        mock_response.id = "test-response-id"
        mock_response.created = 1234567890

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # Test the call
        client = LLMClient(api_key="test-key")
        result = client.call("What is 5 + 3?")

        assert result["completion"] == "The answer is 8. #### 8"
        assert result["usage"]["total_tokens"] == 70
        assert "error" not in result

    @patch("llm.client.OpenAI")
    def test_llm_call_error(self, mock_openai):
        """Test LLM call with error handling."""
        # Mock an exception
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client

        client = LLMClient(api_key="test-key")
        result = client.call("Test prompt")

        assert result["completion"] == ""
        assert "error" in result
        assert result["error"] == "API Error"
        assert result["usage"]["total_tokens"] == 0

    @patch("flows.baseline.LLMClient")
    @patch("flows.baseline.load_gsm8k_batch_task")
    def test_baseline_flow_integration(self, mock_load_batch, mock_llm_client):
        """Test baseline flow integration with mocks."""
        # Mock the data loader
        mock_problems = [
            {
                "problem_id": "gsm8k_0000",
                "question": "What is 2 + 2?",
                "answer": 4.0,
                "answer_raw": "4",
            }
        ]
        mock_load_batch.return_value = mock_problems

        # Mock the LLM client
        mock_client_instance = Mock()
        mock_client_instance.call.return_value = {
            "completion": "2 + 2 = 4. #### 4",
            "model": "gpt-4",
            "usage": {"prompt_tokens": 30, "completion_tokens": 10, "total_tokens": 40},
        }
        mock_llm_client.return_value = mock_client_instance

        # Import and test (after mocking)
        from flows.baseline import solve_baseline_problem

        # Test solving a problem
        result = solve_baseline_problem(
            problem=mock_problems[0],
            run_id="test-run",
            llm_client=mock_client_instance,
            model="gpt-4",
        )

        assert result["problem_id"] == "gsm8k_0000"
        assert result["is_correct"]  # 4.0 matches "4"
        assert result["phase"] == "baseline"
        assert "prompt" in result
        assert "completion" in result

    def test_baseline_flow_small_run(self):
        """Test that we can import and structure the baseline flow."""
        # This tests the structure without actually calling APIs
        # Check that the flow function exists and has expected signature
        import inspect

        from flows.baseline import run_baseline_gsm8k

        sig = inspect.signature(run_baseline_gsm8k)

        expected_params = {"n_problems", "seed", "model", "run_id"}
        actual_params = set(sig.parameters.keys())

        assert expected_params.issubset(actual_params)
