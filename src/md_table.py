"""Utility for generating Markdown tables."""


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    """Generate a Markdown table."""
    if not rows:
        return ""
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    out.extend("| " + " | ".join(r) + " |" for r in rows)
    return "\n".join(out)
