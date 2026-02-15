"""
Configuration management for Cursor Chronicle.

Handles reading/writing export settings from a JSON config file.
Default config location: ~/.cursor-chronicle/config.json
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional


# Default config directory
DEFAULT_CONFIG_DIR = Path.home() / ".cursor-chronicle"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"

# Verbosity levels
VERBOSITY_COMPACT = 1   # Minimal: user/AI text only, tool names without details
VERBOSITY_STANDARD = 2  # Standard: includes tool parameters, short outputs
VERBOSITY_FULL = 3      # Full: complete tool outputs, file contents, thinking

# Default export path (temporary directory for initial testing)
DEFAULT_EXPORT_PATH = Path(tempfile.gettempdir()) / "cursor-chronicle-export"

# Default configuration values
DEFAULT_CONFIG = {
    "export_path": str(DEFAULT_EXPORT_PATH),
    "verbosity": VERBOSITY_STANDARD,
}


def get_config_path() -> Path:
    """Get the path to the configuration file."""
    return DEFAULT_CONFIG_FILE


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load configuration from file.

    If the config file doesn't exist, returns default values.

    Args:
        config_path: Optional path to config file. Uses default if not provided.

    Returns:
        Dict with configuration values.
    """
    if config_path is None:
        config_path = get_config_path()

    config = dict(DEFAULT_CONFIG)

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            if isinstance(user_config, dict):
                for key in DEFAULT_CONFIG:
                    if key in user_config:
                        config[key] = user_config[key]
        except (json.JSONDecodeError, OSError):
            pass

    return config


def save_config(config: Dict[str, Any], config_path: Optional[Path] = None) -> None:
    """
    Save configuration to file.

    Creates the config directory if it doesn't exist.

    Args:
        config: Configuration dict to save.
        config_path: Optional path to config file. Uses default if not provided.
    """
    if config_path is None:
        config_path = get_config_path()

    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def ensure_config_exists(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Ensure config file exists with default values.

    If the file doesn't exist, creates it with defaults.
    If it exists, loads and returns current values.

    Args:
        config_path: Optional path to config file. Uses default if not provided.

    Returns:
        Dict with configuration values.
    """
    if config_path is None:
        config_path = get_config_path()

    config = load_config(config_path)

    if not config_path.exists():
        save_config(config, config_path)

    return config


def get_export_path(config: Optional[Dict[str, Any]] = None) -> Path:
    """
    Get the export path from config.

    Args:
        config: Optional config dict. Loads from file if not provided.

    Returns:
        Path to the export directory.
    """
    if config is None:
        config = load_config()

    return Path(config.get("export_path", str(DEFAULT_EXPORT_PATH)))


def get_verbosity(config: Optional[Dict[str, Any]] = None) -> int:
    """
    Get the verbosity level from config.

    Args:
        config: Optional config dict. Loads from file if not provided.

    Returns:
        Verbosity level (1=compact, 2=standard, 3=full).
    """
    if config is None:
        config = load_config()

    verbosity = config.get("verbosity", VERBOSITY_STANDARD)
    if not isinstance(verbosity, int) or verbosity < 1 or verbosity > 3:
        return VERBOSITY_STANDARD
    return verbosity
