"""Logic for converting items to plain text representation."""


def as_text(v: object) -> str:
    """Convert a value to a string, handling lists and None."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        return "\n".join(as_text(x) for x in v if as_text(x))
    return str(v).strip()
