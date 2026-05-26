"""
Configuration module for loading and accessing project configuration.
All paths, URLs, and keys should be loaded from this module.
"""

import json
import os
from typing import Any, Dict

# Get the directory where this config.py file is located
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "project_config.json")

_config: Dict[str, Any] = {}


def load_config() -> Dict[str, Any]:
    """Load configuration from project_config.json."""
    global _config
    if not _config:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            _config = json.load(f)
    return _config


def get_config() -> Dict[str, Any]:
    """Get the loaded configuration (lazy loads if not already loaded)."""
    if not _config:
        load_config()
    return _config


def get_path(key: str) -> str:
    """Get a path value from config paths section."""
    config = get_config()
    return config.get("paths", {}).get(key, "")


def get_solver() -> Dict[str, Any]:
    """Get solver configuration."""
    config = get_config()
    return config.get("solver", {})


def get_optimization() -> Dict[str, Any]:
    """Get optimization parameters."""
    config = get_config()
    return config.get("optimization", {})


def get_weights() -> Dict[str, Any]:
    """Get optimization weights."""
    config = get_config()
    return config.get("weights", {})


def get_constraints() -> Dict[str, Any]:
    """Get optimization constraints."""
    config = get_config()
    return config.get("constraints", {})


def get_output() -> Dict[str, Any]:
    """Get output file paths."""
    config = get_config()
    return config.get("output", {})


# Convenience functions for common paths
def get_data_dir() -> str:
    """Get the data directory path."""
    return get_path("data_dir")


def get_output_dir() -> str:
    """Get the output directory path."""
    return get_path("output_dir")


def get_logs_dir() -> str:
    """Get the logs directory path."""
    return get_path("logs_dir")


def get_ipopt_executable() -> str:
    """Get the IPOPT executable path."""
    return get_solver().get("ipopt_executable", "ipopt")


# Initialize config on module import
load_config()
