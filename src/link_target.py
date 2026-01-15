"""Data models for representing link targets."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LinkTarget:
    """Represents a link target for an XRef."""

    title: str
    page_path: str  # Wiki path, e.g. /api/Foo.Bar
