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
        """Split a CamelCase string into parts, following human-navigability precedence.

        Algorithm Precedence:
        1. Extract acronym runs (A-Z length ≥ 2) first; absorb trailing digits.
        2. Split TitleCase boundaries; absorb trailing digits unless followed by
           uppercase.
        3. Handle leading digit+letter combos as a single token if digits are
           immediately followed by letters, stopping before TitleCase boundaries.
        """
        tokens = []
        i = 0
        n = len(text)
        while i < n:
            # 1. Acronyms (2+ caps) with optional trailing digits
            # We use (?![a-z]) to avoid consuming the start of a TitleCase word
            match = re.match(r"([A-Z]{2,}[0-9]*)(?![a-z])", text[i:])
            if match:
                tokens.append(match.group(1))
                i += match.end()
                continue

            # 2. TitleCase words with optional trailing digits
            match = re.match(r"([A-Z][a-z]+)", text[i:])
            if match:
                word = match.group(0)
                next_pos = i + len(word)
                # Match optional digits
                digit_match = re.match(r"([0-9]+)", text[next_pos:])
                if digit_match:
                    digits = digit_match.group(0)
                    # Check if digits are followed by an uppercase letter
                    if (
                        next_pos + len(digits) < n
                        and text[next_pos + len(digits)].isupper()
                    ):
                        # Digits belong to next token (e.g. Item2D)
                        tokens.append(word)
                        i += len(word)
                    else:
                        # Consume digits
                        tokens.append(word + digits)
                        i += len(word) + len(digits)
                else:
                    tokens.append(word)
                    i += len(word)
                continue

            # 3. Leading digits followed by letters
            # Try digits + uppercase acronym style (e.g. 2D)
            match = re.match(r"([0-9]+[A-Z]+)(?![a-z])", text[i:])
            if match:
                tokens.append(match.group(1))
                i += match.end()
                continue

            # Try digits + mixed letters (e.g. 2dxFX), stopping before TitleCase
            # boundary
            match = re.match(r"([0-9]+[a-zA-Z]+?)(?=[A-Z][a-z]|$)", text[i:])
            if match:
                tokens.append(match.group(1))
                i += match.end()
                continue

            # 4. Standalone digits or other remaining uppercase runs
            match = re.match(r"([A-Z0-9]+)", text[i:])
            if match:
                tokens.append(match.group(1))
                i += match.end()
                continue

            # 5. Standalone lowercase runs (e.g. 'm' in m_Score)
            match = re.match(r"([a-z]+)", text[i:])
            if match:
                tokens.append(match.group(1))
                i += match.end()
                continue

            # Fallback for unexpected characters
            i += 1
        return tokens
