"""Configuration management for dialectic T-A-S system."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class TASConfig:
    """Configuration manager for T-A-S dialectic system."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to config file (defaults to configs/model.yaml)
        """
        self.config_path = config_path or self._get_default_config_path()
        self._config = self._load_config()
        self._validate_config()

    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        # Find project root (where pyproject.toml exists)
        current = Path(__file__).parent
        while current != current.parent:
            if (current / "pyproject.toml").exists():
                return str(current / "configs" / "model.yaml")
            current = current.parent

        # Fallback to relative path
        return "configs/model.yaml"

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file and environment variables."""
        # Load from YAML file
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"Warning: Config file {self.config_path} not found. Using defaults.")
            config = {}

        # Override with environment variables if present
        env_overrides = {
            "thesis": {
                "temperature": float(
                    os.getenv(
                        "TAS_THESIS_TEMPERATURE", config.get("thesis", {}).get("temperature", 0.7)
                    )
                )
            },
            "antithesis": {
                "temperature": float(
                    os.getenv(
                        "TAS_ANTITHESIS_TEMPERATURE",
                        config.get("antithesis", {}).get("temperature", 0.5),
                    )
                )
            },
            "synthesis": {
                "temperature": float(
                    os.getenv(
                        "TAS_SYNTHESIS_TEMPERATURE",
                        config.get("synthesis", {}).get("temperature", 0.2),
                    )
                )
            },
            "tas": {"k": int(os.getenv("TAS_K_VALUE", config.get("tas", {}).get("k", 1)))},
            "models": {
                "primary": os.getenv(
                    "TAS_DEFAULT_MODEL", config.get("models", {}).get("primary", "gpt-4")
                ),
                "fallback": os.getenv(
                    "TAS_FALLBACK_MODEL", config.get("models", {}).get("fallback", "gpt-3.5-turbo")
                ),
            },
            "limits": {
                "max_tokens_per_phase": int(
                    os.getenv(
                        "TAS_MAX_TOKENS_PER_PHASE",
                        config.get("limits", {}).get("max_tokens_per_phase", 2000),
                    )
                ),
                "total_session_limit": int(
                    os.getenv(
                        "TAS_TOTAL_TOKEN_LIMIT",
                        config.get("limits", {}).get("total_session_limit", 6000),
                    )
                ),
                "timeout_seconds": int(
                    os.getenv(
                        "TAS_REQUEST_TIMEOUT", config.get("limits", {}).get("timeout_seconds", 30)
                    )
                ),
                "max_retries": int(
                    os.getenv("TAS_MAX_RETRIES", config.get("limits", {}).get("max_retries", 3))
                ),
            },
            "logging": {
                "save_cot_local": os.getenv("TAS_SAVE_COT_LOCAL", "true").lower() == "true",
                "sanitize_shared": os.getenv("TAS_SANITIZE_SHARED_LOGS", "true").lower() == "true",
                "session_tracking": os.getenv("TAS_SESSION_TRACKING", "true").lower() == "true",
            },
        }

        # Deep merge configurations
        return self._deep_merge(config, env_overrides)

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _validate_config(self):
        """Validate configuration values."""
        # Validate temperature ranges
        for phase in ["thesis", "antithesis", "synthesis"]:
            temp = self.get_temperature(phase)
            if not 0.0 <= temp <= 1.0:
                raise ValueError(f"Temperature for {phase} must be between 0.0 and 1.0, got {temp}")

        # Validate k value
        k = self.get_k_value()
        if k < 1:
            raise ValueError(f"K value must be >= 1, got {k}")

        # Validate token limits
        max_per_phase = self.get_max_tokens_per_phase()
        total_limit = self.get_total_session_limit()
        if max_per_phase <= 0:
            raise ValueError(f"Max tokens per phase must be > 0, got {max_per_phase}")
        if total_limit <= 0:
            raise ValueError(f"Total session limit must be > 0, got {total_limit}")

    # Temperature getters
    def get_temperature(self, phase: str) -> float:
        """Get temperature for a specific phase."""
        if phase not in ["thesis", "antithesis", "synthesis"]:
            raise ValueError(f"Invalid phase: {phase}")
        return self._config.get(phase, {}).get("temperature", 0.7)

    def get_thesis_temperature(self) -> float:
        """Get thesis temperature."""
        return self.get_temperature("thesis")

    def get_antithesis_temperature(self) -> float:
        """Get antithesis temperature."""
        return self.get_temperature("antithesis")

    def get_synthesis_temperature(self) -> float:
        """Get synthesis temperature."""
        return self.get_temperature("synthesis")

    # Model configuration
    def get_primary_model(self) -> str:
        """Get primary model name."""
        return self._config.get("models", {}).get("primary", "gpt-4")

    def get_fallback_model(self) -> str:
        """Get fallback model name."""
        return self._config.get("models", {}).get("fallback", "gpt-3.5-turbo")

    # TAS configuration
    def get_k_value(self) -> int:
        """Get k value for T-A-S."""
        return self._config.get("tas", {}).get("k", 1)

    # Limits and constraints
    def get_max_tokens_per_phase(self) -> int:
        """Get maximum tokens per phase."""
        return self._config.get("limits", {}).get("max_tokens_per_phase", 2000)

    def get_total_session_limit(self) -> int:
        """Get total token limit per session."""
        return self._config.get("limits", {}).get("total_session_limit", 6000)

    def get_timeout_seconds(self) -> int:
        """Get request timeout in seconds."""
        return self._config.get("limits", {}).get("timeout_seconds", 30)

    def get_max_retries(self) -> int:
        """Get maximum number of retries."""
        return self._config.get("limits", {}).get("max_retries", 3)

    # Logging configuration
    def should_save_cot_local(self) -> bool:
        """Check if CoT should be saved locally."""
        return self._config.get("logging", {}).get("save_cot_local", True)

    def should_sanitize_shared(self) -> bool:
        """Check if shared logs should be sanitized."""
        return self._config.get("logging", {}).get("sanitize_shared", True)

    def should_track_sessions(self) -> bool:
        """Check if sessions should be tracked."""
        return self._config.get("logging", {}).get("session_tracking", True)

    def get_all_config(self) -> Dict[str, Any]:
        """Get the complete configuration."""
        return self._config.copy()


# Global configuration instance
_config_instance: Optional[TASConfig] = None


def get_tas_config(config_path: Optional[str] = None) -> TASConfig:
    """
    Get the global TAS configuration instance.

    Args:
        config_path: Optional path to config file (only used on first call)

    Returns:
        TASConfig instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = TASConfig(config_path)
    return _config_instance


def reset_config():
    """Reset the global configuration instance (mainly for testing)."""
    global _config_instance
    _config_instance = None
