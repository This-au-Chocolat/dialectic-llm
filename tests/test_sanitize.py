"""Tests for sanitization functions."""
import pytest
from src.utils.sanitize import sanitize_advanced

def test_sanitize_advanced_llm_trace():
    """
    Tests the sanitize_advanced function with a sample LLM trace,
    ensuring it redacts PII and hashes specified fields.
    """
    llm_trace = {
        "run_id": "run-123",
        "user_id": "user-abc-123",
        "session_id": "session-xyz-456",
        "prompt": "My email is test@example.com and my phone is 555-123-4567. What is 2+2?",
        "response": {
            "completion": "The answer is 4. My IP is 192.168.1.1 and my credit card is 1234-5678-9012-3456.",
            "agent_name": "MathAgent",
            "api_key": "sk-thisisafakekeyfortesting12345"
        },
        "mathematical_reasoning": "<reasoning>2+2=4</reasoning>",
        "content_tags": ["math", "llm_trace"]
    }
    salt = "test-salt"
    fields_to_hash = ["user_id", "session_id", "api_key"]

    sanitized_trace = sanitize_advanced(
        data=llm_trace,
        salt=salt,
        fields_to_hash=fields_to_hash
    )

    # 1. Check if specified fields are hashed
    import hashlib
    expected_user_id_hash = hashlib.sha256((salt + "user-abc-123").encode()).hexdigest()
    expected_session_id_hash = hashlib.sha256((salt + "session-xyz-456").encode()).hexdigest()
    expected_api_key_hash = hashlib.sha256((salt + "sk-thisisafakekeyfortesting12345").encode()).hexdigest()

    assert sanitized_trace["user_id"] == expected_user_id_hash
    assert sanitized_trace["session_id"] == expected_session_id_hash
    assert sanitized_trace["response"]["api_key"] == expected_api_key_hash

    # 2. Check if sensitive data is redacted from strings
    assert "[REDACTED_EMAIL]" in sanitized_trace["prompt"]
    assert "test@example.com" not in sanitized_trace["prompt"]
    assert "[REDACTED_PHONE]" in sanitized_trace["prompt"]
    assert "555-123-4567" not in sanitized_trace["prompt"]

    assert "[REDACTED_IP_ADDRESS]" in sanitized_trace["response"]["completion"]
    assert "192.168.1.1" not in sanitized_trace["response"]["completion"]
    assert "[REDACTED_CREDIT_CARD]" in sanitized_trace["response"]["completion"]
    assert "1234-5678-9012-3456" not in sanitized_trace["response"]["completion"]

    # 3. Check if non-sensitive data is preserved
    assert sanitized_trace["run_id"] == "run-123"
    assert sanitized_trace["response"]["agent_name"] == "MathAgent"
    assert "What is 2+2?" in sanitized_trace["prompt"]
    assert "The answer is 4." in sanitized_trace["response"]["completion"]
    assert sanitized_trace["mathematical_reasoning"] == "<reasoning>2+2=4</reasoning>"
    assert sanitized_trace["content_tags"] == ["math", "llm_trace"]

    # 4. Check sanitization_info
    assert "sanitization_info" in sanitized_trace
    actions = { (d['field'], d['action']) for d in sanitized_trace["sanitization_info"] }
    assert ("user_id", "hashed") in actions
    assert ("session_id", "hashed") in actions
    assert ("api_key", "hashed") in actions
    assert ("string_pattern", "redacted_email") in actions
    assert ("string_pattern", "redacted_phone") in actions
    assert ("string_pattern", "redacted_ip_address") in actions
    assert ("string_pattern", "redacted_credit_card") in actions
