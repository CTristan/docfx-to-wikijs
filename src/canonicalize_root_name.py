"""Utility for producing a canonical root name from a list of tokens."""

MIN_ACRONYM_LEN = 2


def canonicalize_root_name(tokens: list[str]) -> str:
    """Produce a canonical root name from a list of tokens.

    Policy:
    - Preserve acronyms (all-caps runs of length >= 2).
    - Apply TitleCase to other tokens.
    - Join with empty string.
    """
    canonical_tokens = []
    for token in tokens:
        # Check if it's an acronym (already all caps and length >= 2)
        if len(token) >= MIN_ACRONYM_LEN and token.isupper():
            canonical_tokens.append(token)
        # TitleCase: first letter upper, rest lower
        elif token:
            canonical_tokens.append(token[0].upper() + token[1:].lower())
        else:
            canonical_tokens.append("")

    return "".join(canonical_tokens)
