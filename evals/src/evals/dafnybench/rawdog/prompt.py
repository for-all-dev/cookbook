"""System prompt for tool-based DafnyBench rawdog implementation.

DEPRECATED: This module is kept for backwards compatibility.
Use config.toml to configure the system prompt instead.
"""

from evals.dafnybench.rawdog.config import get_config


def get_system_prompt() -> str:
    """Get the system prompt from configuration.

    Returns:
        System prompt string
    """
    return get_config().prompt.system_prompt


# Backwards compatibility: Load prompt from config as module constant
# This allows existing code that imports RAWDOG_SYSTEM_PROMPT to still work
RAWDOG_SYSTEM_PROMPT = get_system_prompt()
