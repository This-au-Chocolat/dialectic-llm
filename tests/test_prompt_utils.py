"""Tests for prompt templating and hashing utilities.

Task: S1-16 - Tests for templating de prompts + hashing
"""

import hashlib
import json

import pytest

from src.utils.prompt_utils import (
    PROMPT_TEMPLATES,
    create_prompt,
    get_template,
    hash_dict,
    hash_prompt,
    hash_response,
    list_templates,
    register_template,
)


class TestHashingFunctions:
    """Test hashing functions for prompts and responses."""

    def test_hash_prompt_basic(self):
        """Test basic prompt hashing."""
        prompt = "This is a test prompt"
        expected = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        assert hash_prompt(prompt) == expected

    def test_hash_prompt_consistency(self):
        """Test that same prompt always produces same hash."""
        prompt = "Test prompt for consistency"
        hash1 = hash_prompt(prompt)
        hash2 = hash_prompt(prompt)
        assert hash1 == hash2

    def test_hash_prompt_different_inputs(self):
        """Test that different prompts produce different hashes."""
        prompt1 = "First prompt"
        prompt2 = "Second prompt"
        assert hash_prompt(prompt1) != hash_prompt(prompt2)

    def test_hash_response_basic(self):
        """Test basic response hashing."""
        response = "This is a test response"
        expected = hashlib.sha256(response.encode("utf-8")).hexdigest()
        assert hash_response(response) == expected

    def test_hash_response_consistency(self):
        """Test that same response always produces same hash."""
        response = "Test response for consistency"
        hash1 = hash_response(response)
        hash2 = hash_response(response)
        assert hash1 == hash2

    def test_hash_response_different_inputs(self):
        """Test that different responses produce different hashes."""
        response1 = "First response"
        response2 = "Second response"
        assert hash_response(response1) != hash_response(response2)

    def test_hash_dict_basic(self):
        """Test basic dictionary hashing."""
        data = {"key1": "value1", "key2": "value2"}
        json_str = json.dumps(data, sort_keys=True)
        expected = hashlib.sha256(json_str.encode("utf-8")).hexdigest()
        assert hash_dict(data) == expected

    def test_hash_dict_order_independent(self):
        """Test that dict hash is independent of insertion order."""
        dict1 = {"a": 1, "b": 2, "c": 3}
        dict2 = {"c": 3, "a": 1, "b": 2}
        assert hash_dict(dict1) == hash_dict(dict2)

    def test_hash_dict_different_data(self):
        """Test that different dicts produce different hashes."""
        dict1 = {"key": "value1"}
        dict2 = {"key": "value2"}
        assert hash_dict(dict1) != hash_dict(dict2)

    def test_hash_empty_string(self):
        """Test hashing empty strings."""
        assert hash_prompt("") == hashlib.sha256(b"").hexdigest()
        assert hash_response("") == hashlib.sha256(b"").hexdigest()

    def test_hash_unicode(self):
        """Test hashing unicode strings."""
        prompt = "Test with émojis 🎉 and ñ"
        response = "Respuesta con acentúas"
        # Should not raise encoding errors
        hash1 = hash_prompt(prompt)
        hash2 = hash_response(response)
        assert isinstance(hash1, str)
        assert isinstance(hash2, str)
        assert len(hash1) == 64  # SHA-256 hex length
        assert len(hash2) == 64


class TestPromptTemplating:
    """Test prompt template functionality."""

    def test_create_prompt_baseline(self):
        """Test creating baseline GSM8K prompt."""
        question = "What is 2 + 2?"
        prompt = create_prompt("baseline_gsm8k", {"question": question})
        assert question in prompt
        assert "#### [final_answer]" in prompt

    def test_create_prompt_tas_thesis(self):
        """Test creating TAS thesis prompt."""
        question = "Calculate 5 * 6"
        prompt = create_prompt("tas_thesis", {"question": question})
        assert question in prompt
        assert "step-by-step" in prompt

    def test_create_prompt_tas_antithesis(self):
        """Test creating TAS antithesis prompt."""
        question = "What is 10 / 2?"
        thesis = "The answer is 4"
        prompt = create_prompt("tas_antithesis", {"question": question, "thesis_answer": thesis})
        assert question in prompt
        assert thesis in prompt
        assert "critique" in prompt.lower()

    def test_create_prompt_tas_synthesis(self):
        """Test creating TAS synthesis prompt."""
        question = "What is 3 * 3?"
        thesis = "3 * 3 = 9"
        antithesis = "The calculation is correct"
        prompt = create_prompt(
            "tas_synthesis",
            {
                "question": question,
                "thesis_answer": thesis,
                "antithesis_answer": antithesis,
            },
        )
        assert question in prompt
        assert thesis in prompt
        assert antithesis in prompt
        assert "synthesize" in prompt.lower() or "final answer" in prompt.lower()

    def test_create_prompt_custom_template(self):
        """Test creating prompt with custom template."""
        custom = "Hello {name}, you are {age} years old."
        prompt = create_prompt("unused", {"name": "Alice", "age": "25"}, custom_template=custom)
        assert "Hello Alice, you are 25 years old." == prompt

    def test_create_prompt_missing_variable(self):
        """Test that missing variable raises KeyError."""
        with pytest.raises(KeyError, match="Missing required variable"):
            create_prompt("baseline_gsm8k", {})

    def test_create_prompt_invalid_template(self):
        """Test that invalid template name raises KeyError."""
        with pytest.raises(KeyError, match="not found"):
            create_prompt("nonexistent_template", {})

    def test_register_template(self):
        """Test registering a new template."""
        name = "test_custom"
        template = "Custom template with {var1} and {var2}"
        register_template(name, template)

        assert name in PROMPT_TEMPLATES
        prompt = create_prompt(name, {"var1": "foo", "var2": "bar"})
        assert "Custom template with foo and bar" == prompt

    def test_get_template(self):
        """Test getting a template by name."""
        template = get_template("baseline_gsm8k")
        assert "{question}" in template
        assert isinstance(template, str)

    def test_get_template_not_found(self):
        """Test getting non-existent template raises error."""
        with pytest.raises(KeyError, match="not found"):
            get_template("nonexistent_template")

    def test_list_templates(self):
        """Test listing all templates."""
        templates = list_templates()
        assert isinstance(templates, list)
        assert "baseline_gsm8k" in templates
        assert "tas_thesis" in templates
        assert "tas_antithesis" in templates
        assert "tas_synthesis" in templates

    def test_all_default_templates_exist(self):
        """Test that all expected default templates are present."""
        expected = ["baseline_gsm8k", "tas_thesis", "tas_antithesis", "tas_synthesis"]
        templates = list_templates()
        for template_name in expected:
            assert template_name in templates


class TestIntegration:
    """Integration tests combining hashing and templating."""

    def test_hash_generated_prompt(self):
        """Test hashing a generated prompt."""
        question = "What is 7 + 8?"
        prompt = create_prompt("baseline_gsm8k", {"question": question})
        prompt_hash = hash_prompt(prompt)

        # Hash should be consistent
        prompt2 = create_prompt("baseline_gsm8k", {"question": question})
        prompt_hash2 = hash_prompt(prompt2)
        assert prompt_hash == prompt_hash2

    def test_different_questions_different_hashes(self):
        """Test that different questions produce different prompt hashes."""
        prompt1 = create_prompt("baseline_gsm8k", {"question": "What is 1 + 1?"})
        prompt2 = create_prompt("baseline_gsm8k", {"question": "What is 2 + 2?"})

        hash1 = hash_prompt(prompt1)
        hash2 = hash_prompt(prompt2)
        assert hash1 != hash2

    def test_workflow_simulation(self):
        """Simulate a full T-A-S workflow with hashing."""
        question = "A store has 12 apples. If 5 are sold, how many remain?"

        # Thesis
        thesis_prompt = create_prompt("tas_thesis", {"question": question})
        thesis_hash = hash_prompt(thesis_prompt)
        thesis_response = "12 - 5 = 7. #### 7"
        thesis_response_hash = hash_response(thesis_response)

        # Antithesis
        antithesis_prompt = create_prompt(
            "tas_antithesis",
            {"question": question, "thesis_answer": thesis_response},
        )
        antithesis_hash = hash_prompt(antithesis_prompt)
        antithesis_response = "The calculation is correct."
        antithesis_response_hash = hash_response(antithesis_response)

        # Synthesis
        synthesis_prompt = create_prompt(
            "tas_synthesis",
            {
                "question": question,
                "thesis_answer": thesis_response,
                "antithesis_answer": antithesis_response,
            },
        )
        synthesis_hash = hash_prompt(synthesis_prompt)
        synthesis_response = "Final answer: 12 - 5 = 7. #### 7"
        synthesis_response_hash = hash_response(synthesis_response)

        # All hashes should be unique (except responses might match if identical)
        assert thesis_hash != antithesis_hash
        assert thesis_hash != synthesis_hash
        assert antithesis_hash != synthesis_hash

        # All hashes should be 64 chars (SHA-256 hex)
        for h in [
            thesis_hash,
            thesis_response_hash,
            antithesis_hash,
            antithesis_response_hash,
            synthesis_hash,
            synthesis_response_hash,
        ]:
            assert len(h) == 64
