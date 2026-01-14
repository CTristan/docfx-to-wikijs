import hashlib
import json
from typing import Any, Dict, Optional, List
import yaml
from pathlib import Path

DEFAULT_CONFIG: Dict[str, Any] = {
    "thresholds": {
        "min_cluster_size": 10,
        "top_k": 20,
        "max_depth": 2,
        "fragmentation_limit": 0.50,
        "stale_prune_after_runs": 5,
    },
    "rules": {
        "priority_suffixes": ["UI", "Editor"],
        "keyword_clusters": {},
        "stop_tokens": [
            "Manager", "Controller", "System", "Data", "Helper", 
            "Util", "Base", "Common"
        ],
        "metadata_denylist": [
            "MonoBehaviour", "ScriptableObject", "Component", "Object", 
            "Exception", "IEnumerator", "ValueType", "Enum", "Attribute"
        ],
    },
    "acronyms": [
        "UI", "XML", "JSON", "API", "URL", "HTTP", "HTTPS", 
        "FTP", "SSH", "GUI", "HUD"
    ],
    "path_overrides": {},
    "hub_types": {}
}

def deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.
    - Objects are merged recursively.
    - Arrays in 'update' replace 'base' arrays, EXCEPT for specific keys.
    - 'acronyms' is additive.
    """
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        elif key == "acronyms" and isinstance(value, list) and isinstance(result.get(key), list):
             # Additive merge for acronyms, deduplicated and sorted
             base_list = result[key]
             # Ensure both are list of strings
             merged_set = set(base_list)
             merged_set.update(value)
             result[key] = sorted(list(merged_set))
        else:
            # Default: Replacement (scalars and other arrays)
            result[key] = value
    return result

def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from a YAML file and merge it with defaults.
    """
    config = DEFAULT_CONFIG.copy()
    if path and Path(path).exists():
        with open(path, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
        config = deep_merge(config, user_config)
    return config

def compute_config_hash(config: Dict[str, Any]) -> str:
    """
    Compute a stable hash of the configuration.
    Uses canonical JSON serialization (sorted keys).
    """
    config_json = json.dumps(config, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(config_json.encode("utf-8")).hexdigest()
