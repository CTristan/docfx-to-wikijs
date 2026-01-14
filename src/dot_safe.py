"""Utility for making strings safe for use in DOT files or paths."""

import re

# Conservative: keep letters, digits, underscore, dash. Dots are replaced with hyphens.
DOT_SAFE_RE = re.compile(r"[^A-Za-z0-9_-]+")


def dot_safe(name: str) -> str:
    """Make a stable filename-ish token.

    Replaces dots with hyphens for Wiki.js compatibility. Also normalize nested types
    and generics markers.
    """
    name = name.replace("+", "-")  # nested types Outer+Inner -> Outer-Inner
    name = name.replace("`", "")  # generics Foo`1 -> Foo1-ish
    name = name.replace(".", "-")  # dots -> hyphens for Wiki.js compatibility
    name = DOT_SAFE_RE.sub("-", name).strip("-")
    # Avoid pathological emptiness
    return name or "Unknown"
