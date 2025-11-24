"""
Test suite for S2-02: MAMV configuration parameters.

Tests that the new temperature jitter and seed configuration
can be read correctly from configs/model.yaml.
"""

import pytest

from src.utils.config import TASConfig, get_tas_config, reset_config


@pytest.fixture(autouse=True)
def reset_global_config():
    """Reset global config before each test."""
    reset_config()
    yield
    reset_config()


class TestS2_02_MAMVConfiguration:
    """Test suite for MAMV configuration (S2-02)."""

    def test_thesis_temperatures_array_loaded(self):
        """Test that thesis temperatures array is loaded correctly."""
        config = get_tas_config()
        temps = config.get_thesis_temperatures()

        # S2-02 requirement: {0.65, 0.70, 0.75}
        assert isinstance(temps, list), "Should return a list"
        assert len(temps) == 3, "Should have 3 temperature values"
        assert temps == [0.65, 0.70, 0.75], "Should match configured temperatures"

    def test_thesis_temperatures_fallback(self):
        """Test fallback to single temperature if array not configured."""
        # Create config with minimal settings (no temperatures array)
        import tempfile
        from pathlib import Path

        import yaml

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "thesis": {"temperature": 0.80},
                    "antithesis": {"temperature": 0.50},
                    "synthesis": {"temperature": 0.20},
                },
                f,
            )
            temp_config_path = f.name

        try:
            config = TASConfig(config_path=temp_config_path)
            temps = config.get_thesis_temperatures()

            assert isinstance(temps, list), "Should return a list"
            assert len(temps) == 1, "Should fallback to single temperature"
            assert temps[0] == 0.80, "Should use thesis.temperature value"
        finally:
            Path(temp_config_path).unlink()

    def test_mamv_seeds_loaded(self):
        """Test that MAMV seeds are loaded correctly."""
        config = get_tas_config()
        seeds = config.get_mamv_seeds()

        # S2-02 requirement: {101, 202, 303}
        assert isinstance(seeds, list), "Should return a list"
        assert len(seeds) == 3, "Should have 3 seed values"
        assert seeds == [101, 202, 303], "Should match configured seeds"

    def test_mamv_enabled_default_false(self):
        """Test that MAMV is disabled by default."""
        config = get_tas_config()
        assert config.is_mamv_enabled() is False, "MAMV should be disabled by default"

    def test_mamv_num_instances_default(self):
        """Test that MAMV num_instances has correct default."""
        config = get_tas_config()
        num_instances = config.get_mamv_num_instances()
        assert num_instances == 3, "Should have 3 instances by default"

    def test_mamv_voting_strategy_default(self):
        """Test that MAMV voting strategy has correct default."""
        config = get_tas_config()
        strategy = config.get_mamv_voting_strategy()
        assert strategy == "majority", "Should default to majority voting"

    def test_temperature_validation_still_works(self):
        """Test that existing temperature validation still works."""
        config = get_tas_config()

        # These should all pass validation
        assert 0.0 <= config.get_thesis_temperature() <= 1.0
        assert 0.0 <= config.get_antithesis_temperature() <= 1.0
        assert 0.0 <= config.get_synthesis_temperature() <= 1.0

    def test_config_backwards_compatible(self):
        """Test that config is backwards compatible with S1 code."""
        config = get_tas_config()

        # All old methods should still work
        assert isinstance(config.get_thesis_temperature(), float)
        assert isinstance(config.get_antithesis_temperature(), float)
        assert isinstance(config.get_synthesis_temperature(), float)
        assert isinstance(config.get_primary_model(), str)
        assert isinstance(config.get_k_value(), int)

    def test_all_s2_02_requirements_met(self):
        """Comprehensive test for all S2-02 acceptance criteria."""
        config = get_tas_config()

        # 1. Temperature jitter configured
        temps = config.get_thesis_temperatures()
        assert temps == [0.65, 0.70, 0.75], "Temperature jitter must match S2-02 spec"

        # 2. Seeds configured
        seeds = config.get_mamv_seeds()
        assert seeds == [101, 202, 303], "Seeds must match S2-02 spec"

        # 3. k=1 still configured
        assert config.get_k_value() == 1, "k should still be 1"

        # 4. Config methods exist and work
        assert callable(config.get_thesis_temperatures)
        assert callable(config.get_mamv_seeds)
        assert callable(config.is_mamv_enabled)

        print("✅ All S2-02 requirements verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
