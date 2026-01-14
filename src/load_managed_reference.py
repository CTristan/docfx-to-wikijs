"""Logic for loading managed reference YAML files."""

import re
from pathlib import Path
from typing import Any

import yaml

from src.strip_yaml_mime_header import strip_yaml_mime_header


def load_managed_reference(path: Path) -> dict[str, Any]:
    """Load and parse a DocFX ManagedReference YAML file."""
    raw = strip_yaml_mime_header(path.read_text(encoding="utf-8"))
    # Fix unquoted equals sign in VB names which confuses PyYAML
    # Matches: "  name.vb: =" -> "  name.vb: '='"
    raw = re.sub(r"^(\s*[\w\.]+\.vb:\s+)(=$)", r"\1'='", raw, flags=re.MULTILINE)
    doc = yaml.safe_load(raw)
    return doc or {}
