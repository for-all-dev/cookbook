"""Configuration loading for DafnyBench rawdog implementation."""

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for Python < 3.11


@dataclass
class EvaluationConfig:
    """Evaluation settings."""

    max_iterations: int
    max_tokens: int
    verification_timeout: int
    default_model: str


@dataclass
class LoggingConfig:
    """Logging settings."""

    level: str
    save_artifacts: bool
    artifacts_dir: str
    logs_dir: str


@dataclass
class PromptConfig:
    """Prompt settings."""

    system_prompt: str


@dataclass
class DatasetConfig:
    """Dataset settings."""

    name: str
    split: str


@dataclass
class RawdogConfig:
    """Complete configuration for rawdog evaluation."""

    evaluation: EvaluationConfig
    logging: LoggingConfig
    prompt: PromptConfig
    dataset: DatasetConfig

    @classmethod
    def from_file(cls, config_path: Path | str | None = None) -> "RawdogConfig":
        """Load configuration from TOML file.

        Args:
            config_path: Path to config.toml. If None, uses default location
                        (same directory as this module)

        Returns:
            RawdogConfig instance
        """
        if config_path is None:
            # Default: config.toml in same directory as this module
            config_path = Path(__file__).parent / "config.toml"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        return cls(
            evaluation=EvaluationConfig(**data["evaluation"]),
            logging=LoggingConfig(**data["logging"]),
            prompt=PromptConfig(**data["prompt"]),
            dataset=DatasetConfig(**data["dataset"]),
        )

    @classmethod
    def default(cls) -> "RawdogConfig":
        """Get default configuration (loads from default config.toml location).

        Returns:
            RawdogConfig instance with default settings
        """
        return cls.from_file()


# Singleton instance
_config: RawdogConfig | None = None


def get_config(reload: bool = False) -> RawdogConfig:
    """Get the global configuration instance.

    Args:
        reload: If True, reload configuration from file

    Returns:
        RawdogConfig instance
    """
    global _config
    if _config is None or reload:
        _config = RawdogConfig.default()
    return _config


def load_config(config_path: Path | str) -> RawdogConfig:
    """Load configuration from a specific path and set as global.

    Args:
        config_path: Path to config.toml

    Returns:
        RawdogConfig instance
    """
    global _config
    _config = RawdogConfig.from_file(config_path)
    return _config
