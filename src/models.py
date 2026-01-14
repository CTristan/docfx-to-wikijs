from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Dict

@dataclass
class ItemInfo:
    """Represents a documented item (class, method, etc.)."""
    uid: str
    kind: str  # Namespace/Class/Method/Property/etc.
    name: str
    full_name: str
    parent: Optional[str]
    namespace: Optional[str]
    summary: str
    inheritance: List[str]
    implements: List[str]
    file: Path
    raw: Dict[str, Any]  # original parsed item

@dataclass(frozen=True)
class LinkTarget:
    """Represents a link target for an XRef."""
    title: str
    page_path: str  # Wiki path, e.g. /api/Foo.Bar
