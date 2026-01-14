"""Utility for generating Markdown code blocks."""


def md_codeblock(lang: str, code: str) -> str:
    """Generate a Markdown code block."""
    return f"""```{lang}
{code.rstrip()}
```"""
