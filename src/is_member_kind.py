"""Predicate for checking if an item is a member."""


def is_member_kind(kind: str) -> bool:
    """Check if the kind represents a member (method, property, etc.)."""
    k = kind.lower()
    return k in {"method", "property", "field", "event", "operator", "constructor"}
