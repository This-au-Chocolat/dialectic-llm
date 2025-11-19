"""Utilities for prompt templating and hashing.

This module provides:
1. Prompt templating functions for consistent prompt generation
2. Hashing functions for prompts and responses for tracking and deduplication
3. Template registry for managing different prompt types

Task: S1-16 - Templating de prompts + hashing de prompt/resp
"""

import hashlib
from typing import Any, Dict, Optional


def hash_prompt(prompt: str) -> str:
    """
    Generate a SHA-256 hash of a prompt for consistent identification.

    Args:
        prompt: The prompt text to hash

    Returns:
        Hexadecimal string representation of the hash
    """
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def hash_response(response: str) -> str:
    """
    Generate a SHA-256 hash of a response for consistent identification.

    Args:
        response: The response text to hash

    Returns:
        Hexadecimal string representation of the hash
    """
    return hashlib.sha256(response.encode("utf-8")).hexdigest()


def hash_dict(data: Dict[str, Any]) -> str:
    """
    Generate a hash of a dictionary by converting to sorted JSON string.

    Args:
        data: Dictionary to hash

    Returns:
        Hexadecimal string representation of the hash
    """
    import json

    # Sort keys for consistent hashing
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


# Prompt Templates Registry
PROMPT_TEMPLATES = {
    "baseline_gsm8k": (
        "You are solving a math word problem step by step.\n\n"
        "Question: {question}\n\n"
        "Please solve this step by step and end your response with "
        '"#### [final_answer]" where [final_answer] is just the number.'
    ),
    "tas_thesis": (
        "You are solving a math word problem. "
        "Provide a clear solution with step-by-step reasoning.\n\n"
        "Question: {question}\n\n"
        "Provide your solution with clear steps and end with "
        '"#### [final_answer]" where [final_answer] is the numeric answer.'
    ),
    "tas_antithesis": """Review and critique the following solution to a math problem.

Original Question: {question}

Proposed Solution:
{thesis_answer}

Critically analyze this solution. Identify any:
- Arithmetic errors
- Logical flaws
- Incorrect assumptions
- Missing steps

Provide your critique with specific issues found.""",
    "tas_synthesis": (
        "Synthesize the original solution and critique into a final answer.\n\n"
        "Question: {question}\n\n"
        "Original Solution:\n{thesis_answer}\n\n"
        "Critique:\n{antithesis_answer}\n\n"
        "Based on the original solution and the critique, "
        "provide a refined final answer. Keep correct reasoning, "
        "fix identified errors, and end with "
        '"#### [final_answer]" where [final_answer] is the numeric answer.'
    ),
}


def create_prompt(
    template_name: str, variables: Dict[str, str], custom_template: Optional[str] = None
) -> str:
    """
    Create a prompt from a template with variable substitution.

    Args:
        template_name: Name of the template to use from PROMPT_TEMPLATES
        variables: Dictionary of variables to substitute in the template
        custom_template: Optional custom template string to use instead

    Returns:
        Formatted prompt string

    Raises:
        KeyError: If template_name not found and no custom_template provided
        KeyError: If required variables are missing
    """
    if custom_template:
        template = custom_template
    else:
        if template_name not in PROMPT_TEMPLATES:
            raise KeyError(
                f"Template '{template_name}' not found. "
                f"Available templates: {list(PROMPT_TEMPLATES.keys())}"
            )
        template = PROMPT_TEMPLATES[template_name]

    try:
        return template.format(**variables)
    except KeyError as e:
        raise KeyError(f"Missing required variable in template: {e}") from e


def register_template(name: str, template: str) -> None:
    """
    Register a new prompt template.

    Args:
        name: Name for the template
        template: Template string with {variable} placeholders
    """
    PROMPT_TEMPLATES[name] = template


def get_template(name: str) -> str:
    """
    Get a template by name.

    Args:
        name: Name of the template

    Returns:
        Template string

    Raises:
        KeyError: If template not found
    """
    if name not in PROMPT_TEMPLATES:
        raise KeyError(
            f"Template '{name}' not found. Available templates: {list(PROMPT_TEMPLATES.keys())}"
        )
    return PROMPT_TEMPLATES[name]


def list_templates() -> list[str]:
    """
    List all available template names.

    Returns:
        List of template names
    """
    return list(PROMPT_TEMPLATES.keys())
