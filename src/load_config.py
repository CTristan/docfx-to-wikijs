"""Logic for loading and merging configuration files."""

from pathlib import Path
from typing import Any

import yaml

from src.deep_merge import deep_merge

DEFAULT_CONFIG: dict[str, Any] = {
    "thresholds": {
        "min_cluster_size": 3,
        "top_k": 20,
        "max_top_level_folders": 40,
        "max_folder_size": 250,
        "min_family_size": 3,
        "max_depth": 2,
        "fragmentation_limit": 0.50,
        "stale_prune_after_runs": 5,
    },
    "rules": {
        "priority_suffixes": ["UI", "Editor"],
        "keyword_clusters": {},
        "overflow_strategy": "reroute_to_best_kept",
        "reroute_bias": "stability",
        "pinned_allow_singleton": False,
        "pinned_roots": [],
        "stop_tokens": [
            "Manager",
            "Controller",
            "System",
            "Data",
            "Helper",
            "Util",
            "Base",
            "Common",
        ],
        "metadata_denylist": [
            "MonoBehaviour",
            "ScriptableObject",
            "Component",
            "Object",
            "Exception",
            "IEnumerator",
            "ValueType",
            "Enum",
            "Attribute",
        ],
    },
    "acronyms": [
        "UI",
        "XML",
        "JSON",
        "API",
        "URL",
        "HTTP",
        "HTTPS",
        "FTP",
        "SSH",
        "GUI",
        "HUD",
    ],
    "path_overrides": {},
    "hub_types": {},
}


def load_config(path: str | None = None) -> dict[str, Any]:
    """Load configuration from a YAML file and merge it with defaults."""
    config = DEFAULT_CONFIG.copy()
    if path:
        p = Path(path)
        if p.exists():
            user_config = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            config = deep_merge(config, user_config)
    return config
