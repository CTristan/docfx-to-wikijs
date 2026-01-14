"""Logic for deep merging configuration dictionaries."""

from typing import Any


def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries.

    - Objects are merged recursively.
    - Arrays in 'update' replace 'base' arrays, EXCEPT for specific keys.
    - 'acronyms' is additive.
    """
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        elif (
            key == "acronyms"
            and isinstance(value, list)
            and isinstance(result.get(key), list)
        ):
            # Additive merge for acronyms, deduplicated and sorted
            base_list = result[key]
            # Ensure both are list of strings
            merged_set = set(base_list)
            merged_set.update(value)
            result[key] = sorted(merged_set)
        else:
            # Default: Replacement (scalars and other arrays)
            result[key] = value
    return result
