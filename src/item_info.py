"""Data models for representing DocFX items."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ItemInfo:
    """Represents a documented item (class, method, etc.)."""

    uid: str
    kind: str  # Namespace/Class/Method/Property/etc.
    name: str
    full_name: str
    parent: str | None
    namespace: str | None
    summary: str
    inheritance: list[str]
    implements: list[str]
    file: Path
    raw: dict[str, Any]  # original parsed item
