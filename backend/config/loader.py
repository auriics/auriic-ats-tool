import os
import yaml
from typing import Dict, Any

_CACHED_CONFIG = None

def load_scoring_config() -> Dict[str, Any]:
    """Robustly find and load scoring_config.yaml across local and serverless environments."""
    global _CACHED_CONFIG
    if _CACHED_CONFIG is not None:
        return _CACHED_CONFIG

    base_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(base_dir, "scoring_config.yaml"),
        os.path.join(os.path.dirname(base_dir), "config", "scoring_config.yaml"),
        os.path.join(os.path.dirname(os.path.dirname(base_dir)), "backend", "config", "scoring_config.yaml"),
        "/var/task/backend/config/scoring_config.yaml",
        "/var/task/config/scoring_config.yaml",
        "backend/config/scoring_config.yaml",
        "config/scoring_config.yaml",
    ]

    for path in possible_paths:
        if os.path.exists(path) and os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                _CACHED_CONFIG = yaml.safe_load(f)
                return _CACHED_CONFIG

    raise FileNotFoundError(f"Could not locate scoring_config.yaml in paths: {possible_paths}")
