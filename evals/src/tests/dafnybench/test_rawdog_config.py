"""Tests for rawdog configuration loading."""

from pathlib import Path

import pytest

from evals.dafnybench.rawdog.config import RawdogConfig, get_config


def test_load_default_config():
    """Test loading default configuration."""
    config = RawdogConfig.default()

    # Check that all sections loaded
    assert config.evaluation is not None
    assert config.logging is not None
    assert config.prompt is not None
    assert config.dataset is not None


def test_evaluation_config():
    """Test evaluation configuration values."""
    config = get_config()

    assert config.evaluation.max_iterations == 20
    assert config.evaluation.max_tokens == 8192
    assert config.evaluation.verification_timeout == 30
    assert config.evaluation.default_model == "claude-sonnet-4-5"


def test_logging_config():
    """Test logging configuration values."""
    config = get_config()

    assert config.logging.level == "INFO"
    assert config.logging.save_artifacts is True
    assert config.logging.artifacts_dir == "artifacts"
    assert config.logging.logs_dir == "logs"


def test_prompt_config():
    """Test prompt configuration."""
    config = get_config()

    # Check that prompt loaded and is non-empty
    assert config.prompt.system_prompt
    assert len(config.prompt.system_prompt) > 100
    assert "Dafny" in config.prompt.system_prompt
    assert "insert_invariant" in config.prompt.system_prompt


def test_dataset_config():
    """Test dataset configuration values."""
    config = get_config()

    assert config.dataset.name == "wendy-sun/DafnyBench"
    assert config.dataset.split == "test"


def test_config_file_location():
    """Test that config file exists at expected location."""
    from evals.dafnybench.rawdog import config as config_module

    config_path = Path(config_module.__file__).parent / "config.toml"
    assert config_path.exists()
    assert config_path.is_file()


def test_config_singleton():
    """Test that get_config returns same instance."""
    config1 = get_config()
    config2 = get_config()

    # Should be same object
    assert config1 is config2


def test_config_reload():
    """Test that reload parameter forces new instance."""
    config1 = get_config()
    config2 = get_config(reload=True)

    # Should have same values but might be different objects
    assert config1.evaluation.max_iterations == config2.evaluation.max_iterations


def test_prompt_templates():
    """Test that prompt templates exist and support interpolation."""
    config = get_config()

    # Check initial state template
    assert config.prompt.initial_state_template
    assert "{code}" in config.prompt.initial_state_template
    assert "CURRENT_CODE_STATE" in config.prompt.initial_state_template

    # Check state update template
    assert config.prompt.state_update_template
    assert "{code}" in config.prompt.state_update_template
    assert "CURRENT_CODE_STATE" in config.prompt.state_update_template

    # Test interpolation works
    test_code = "method Test() {}"
    initial = config.prompt.initial_state_template.format(code=test_code)
    assert test_code in initial
    assert "initial unhinted code" in initial

    update = config.prompt.state_update_template.format(code=test_code)
    assert test_code in update
    assert "State updated" in update
