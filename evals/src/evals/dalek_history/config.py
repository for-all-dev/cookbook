"""Configuration loading for the dalek history mining pipeline."""

import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MiningConfig:
    """Mining-related configuration."""

    repo_path: Path
    start_ref: str
    max_commits: int


@dataclass
class FilteringConfig:
    """File filtering configuration."""

    min_theorem_count: int
    min_tactic_blocks: int
    exclude_paths: list[str]


@dataclass
class VerificationConfig:
    """Verification-related configuration."""

    timeout_seconds: int
    lake_command: str


@dataclass
class OutputConfig:
    """Output-related configuration."""

    jsonl_path: Path
    log_dir: Path
    save_artifacts: bool


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str


@dataclass
class Config:
    """Complete configuration for the mining pipeline."""

    mining: MiningConfig
    filtering: FilteringConfig
    verification: VerificationConfig
    output: OutputConfig
    logging: LoggingConfig

    @classmethod
    def from_file(cls, path: Path | None = None) -> "Config":
        """Load configuration from TOML file.

        Args:
            path: Path to config file. If None, uses default in module directory.

        Returns:
            Loaded configuration object.
        """
        if path is None:
            path = Path(__file__).parent / "config.toml"

        with open(path, "rb") as f:
            data = tomllib.load(f)

        return cls(
            mining=MiningConfig(
                repo_path=Path(data["mining"]["repo_path"]),
                start_ref=data["mining"]["start_ref"],
                max_commits=data["mining"]["max_commits"],
            ),
            filtering=FilteringConfig(
                min_theorem_count=data["filtering"]["min_theorem_count"],
                min_tactic_blocks=data["filtering"]["min_tactic_blocks"],
                exclude_paths=data["filtering"]["exclude_paths"],
            ),
            verification=VerificationConfig(
                timeout_seconds=data["verification"]["timeout_seconds"],
                lake_command=data["verification"]["lake_command"],
            ),
            output=OutputConfig(
                jsonl_path=Path(data["output"]["jsonl_path"]),
                log_dir=Path(data["output"]["log_dir"]),
                save_artifacts=data["output"]["save_artifacts"],
            ),
            logging=LoggingConfig(
                level=data["logging"]["level"],
            ),
        )


# Singleton instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance.

    Returns:
        The configuration singleton.
    """
    global _config
    if _config is None:
        _config = Config.from_file()
    return _config


def load_config(path: Path | None = None) -> Config:
    """Load configuration from file and set as global.

    Args:
        path: Path to config file. If None, uses default.

    Returns:
        The loaded configuration.
    """
    global _config
    _config = Config.from_file(path)
    return _config


def setup_logging(config: Config) -> None:
    """Setup logging based on configuration.

    Args:
        config: Configuration object with logging settings.
    """
    log_dir = config.output.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, config.logging.level.upper())

    # Create formatters
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # File handler
    file_handler = logging.FileHandler(log_dir / "mining.log")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
