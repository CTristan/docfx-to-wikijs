"""Utility for generating slugs for Markdown headers."""

import re


def header_slug(s: str) -> str:
    """Generate a GitHub-ish anchor slug: lower, hyphenate non-alnum."""
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "section"
