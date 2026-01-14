"""Predicate for checking if an item is a namespace."""


def is_namespace_kind(kind: str) -> bool:
    """Check if the kind represents a namespace."""
    return kind.lower() == "namespace"
