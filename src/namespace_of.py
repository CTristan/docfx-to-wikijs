"""Utility for determining the namespace of an item."""

from src.item_info import ItemInfo


def namespace_of(item: ItemInfo) -> str:
    """Determine the namespace of an item."""
    # Prefer explicit namespace field.
    if item.namespace:
        return item.namespace
    # Try derive from full_name if it looks dotted.
    parts = item.full_name.split(".")
    if len(parts) > 1:
        return ".".join(parts[:-1])
    return ""
