"""Logic for computing stable hashes of configuration objects."""

import hashlib
import json
from typing import Any


def compute_config_hash(config: dict[str, Any]) -> str:
    """Compute a stable hash of the configuration.

    Uses canonical JSON serialization (sorted keys).
    """
    config_json = json.dumps(config, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(config_json.encode("utf-8")).hexdigest()
