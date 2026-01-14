"""Logic for sanitizing and normalizing string tokens for use in file paths."""

import re


class Sanitizer:
    """Sanitizes and normalizes tokens to be safe for filenames and URLs."""

    def __init__(self, acronyms: list[str] | None = None) -> None:
        """Initialize the sanitizer with optional acronyms to preserve casing."""
        self.acronyms = {s.upper() for s in (acronyms or [])}
        self.reserved = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }

    def normalize(self, token: str) -> str:
        """Normalize a token by removing illegal characters and handling casing."""
        # 1. Sanitize chars (Keep A-Z, a-z, 0-9, -)
        clean = re.sub(r"[^A-Za-z0-9-]", "", token)

        if not clean:
            return f"_{hash(token) & 0xFFFFFFFF:x}"

        # 2. Casing
        upper_clean = clean.upper()
        if upper_clean in self.acronyms:
            final = upper_clean
        elif clean == upper_clean and len(clean) > 1:
            # If original was all caps (and >1 char), treat as acronym/preserved
            final = clean
        # Capitalize first letter, preserve the rest
        elif len(clean) > 0:
            final = clean[0].upper() + clean[1:]
        else:
            final = clean

        # 3. Windows Cleanup
        final = final.rstrip(". ")

        # 4. Reserved check
        if final.upper() in self.reserved or not final:
            return f"_{hash(token) & 0xFFFFFFFF:x}"

        return final
