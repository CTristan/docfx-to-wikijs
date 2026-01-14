"""Predicate for deciding if an item belongs in the Global directory."""


def should_use_global_dir(namespace: str | None) -> bool:
    """Check if the item belongs in the Global directory."""
    return namespace is None or namespace == "Global"
