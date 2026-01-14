import re
from typing import List, Set

class Tokenizer:
    def __init__(self, acronyms: List[str] = None):
        self.acronyms = set(acronyms or [])

    def tokenize(self, text: str) -> List[str]:
        # Strip generic arity `1
        text = re.sub(r"`\d+", "", text)
        
        tokens = []
        # Split by nested type '+' and underscore '_'
        parts = re.split(r'[+_]', text)
        for part in parts:
            if part:
                tokens.extend(self._split_camel_case(part))
        return tokens

    def _split_camel_case(self, text: str) -> List[str]:
        # Regex:
        # 1. [A-Z]+(?=[A-Z][a-z0-9]) : Acronym before a word (XML in XMLParser)
        # 2. [A-Z]?[a-z]+(?:[0-9]+(?![A-Z]))? : Word (Title or lower) with optional suffix nums, 
        #                                       only if nums NOT followed by Upper (Vector3 vs Item2D).
        # 3. [A-Z0-9]+              : Acronym/Numbers at end or standalone (UI, 2D)
        
        pattern = r"([A-Z]+(?=[A-Z][a-z0-9])|[A-Z]?[a-z]+(?:[0-9]+(?![A-Z]))?|[A-Z0-9]+)"
        matches = re.findall(pattern, text)
        return matches

class Sanitizer:
    def __init__(self, acronyms: List[str] = None):
        # Acronyms for casing preservation
        self.acronyms = set(s.upper() for s in (acronyms or []))
        self.reserved = {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", 
                         "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", 
                         "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}

    def normalize(self, token: str) -> str:
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
        else:
            # Capitalize first letter, preserve the rest
            if len(clean) > 0:
                final = clean[0].upper() + clean[1:]
            else:
                final = clean
            
        # 3. Windows Cleanup
        final = final.rstrip(". ")
        
        # 4. Reserved check
        if final.upper() in self.reserved or not final:
            return f"_{hash(token) & 0xFFFFFFFF:x}"
            
        return final
