"""Utility for iterating over primary items in YAML files."""

from collections.abc import Iterable
from typing import Any


def iter_main_items(doc: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """Iterate over the main items in a DocFX YAML document."""
    items = doc.get("items") or []
    for it in items:
        if isinstance(it, dict) and it.get("uid"):
            yield it
