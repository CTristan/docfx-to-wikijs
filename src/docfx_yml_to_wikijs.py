"""Main entry point for DocFX YAML to Wiki.js conversion."""

import argparse
from pathlib import Path

from src.run_conversion import run_conversion


def main() -> int:
    """Run the conversion process."""
    ap = argparse.ArgumentParser(
        description=(
            "Convert DocFX ManagedReference YAML to Wiki.js Markdown (DocFX-ish "
            "layout)."
        ),
    )
    ap.add_argument(
        "yml_dir",
        type=Path,
        help="Directory containing DocFX *.yml (ManagedReference) files",
    )
    ap.add_argument(
        "out_dir",
        type=Path,
        help="Output directory (a git repo root for Wiki.js Git storage)",
    )
    ap.add_argument(
        "--api-root",
        default="/api",
        help="Wiki path root for generated pages (default: /api)",
    )
    ap.add_argument(
        "--include-namespace-pages",
        action="store_true",
        help="Generate foo.md, foo.bar.md namespace landing pages",
    )
    ap.add_argument(
        "--include-member-details",
        action="store_true",
        help="Inline member sections (constructors/methods/etc.) on type pages",
    )
    ap.add_argument(
        "--home-page",
        action="store_true",
        help="Generate a simple Home page (home.md)",
    )
    ap.add_argument(
        "--config",
        help="Path to configuration file",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze and generate report without writing files",
    )
    ap.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Ignore cache and rebuild all clusters",
    )
    ap.add_argument(
        "--prune-stale",
        action="store_true",
        help="Remove stale entries from cache",
    )
    ap.add_argument(
        "--accept-legacy-cache",
        action="store_true",
        help="Accept and migrate legacy cache formats",
    )
    args = ap.parse_args()
    return run_conversion(args)


if __name__ == "__main__":
    raise SystemExit(main())
