"""Predicate for checking if an item is a type (class, struct, etc.)."""


def is_type_kind(kind: str) -> bool:
    """Check if the kind represents a type (class, struct, etc.)."""
    k = kind.lower()
    return k in {"class", "struct", "interface", "enum", "delegate"}
