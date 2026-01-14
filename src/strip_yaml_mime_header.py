"""Utility for removing YAML MIME headers from files."""

YAML_MIME_PREFIX = "### YamlMime:"


def strip_yaml_mime_header(text: str) -> str:
    """Remove the DocFX YAML MIME header from the content."""
    lines = text.splitlines()
    if lines and lines[0].startswith(YAML_MIME_PREFIX):
        return "\n".join(lines[1:]).lstrip("\n")
    return text
