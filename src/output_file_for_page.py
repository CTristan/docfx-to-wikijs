"""Utility for determining the output file path for a page."""

from pathlib import Path


def output_file_for_page(out_root: Path, page_path: str) -> Path:
    """Determine the output file path for a given Wiki.js page path."""
    # /api/Foo.Bar -> out_root/api/Foo.Bar.md
    rel = page_path.lstrip("/") + ".md"
    p = out_root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
