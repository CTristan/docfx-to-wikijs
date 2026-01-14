"""Logic for splitting identifiers into semantic tokens."""

import re


class Tokenizer:
    """Splits CamelCase, underscored, and generic identifiers into tokens."""

    def __init__(self, acronyms: list[str] | None = None) -> None:
        """Initialize the tokenizer with optional known acronyms."""
        self.acronyms = set(acronyms or [])

    def tokenize(self, text: str) -> list[str]:
        """Split a full identifier string into a list of tokens."""
        # Strip generic arity `1
        text = re.sub(r"`\d+", "", text)

        tokens = []
        # Split by nested type '+' and underscore '_'
        parts = re.split(r"[+_]", text)
        for part in parts:
            if part:
                tokens.extend(self._split_camel_case(part))
        return tokens

    def _split_camel_case(self, text: str) -> list[str]:
        """Split a CamelCase string into parts, preserving acronyms and numbers."""
        # Regex parts:
        # 1. Acronym before a word (XML in XMLParser)
        # 2. Word with optional suffix nums (Vector3 vs Item2D)
        # 3. Acronym/Numbers at end or standalone (UI, 2D)

        pattern = (
            r"([A-Z]+(?=[A-Z][a-z0-9])|"
            r"[A-Z]?[a-z]+(?:[0-9]+(?![A-Z]))?|"
            r"[A-Z0-9]+)"
        )
        return re.findall(pattern, text)
