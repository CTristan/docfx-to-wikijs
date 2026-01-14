"""Tests for tokenization and sanitization."""

from src.sanitizer import Sanitizer
from src.tokenizer import Tokenizer


def test_tokenizer_basic() -> None:
    """Verify basic CamelCase tokenization."""
    t = Tokenizer()
    assert t.tokenize("CamelCase") == ["Camel", "Case"]
    assert t.tokenize("Simple") == ["Simple"]


def test_tokenizer_numbers() -> None:
    """Verify handling of numbers in identifiers."""
    t = Tokenizer()
    assert t.tokenize("Vector3") == ["Vector3"]
    assert t.tokenize("Item2D") == ["Item", "2D"]


def test_tokenizer_acronyms() -> None:
    """Verify handling of acronyms in CamelCase."""
    t = Tokenizer()
    assert t.tokenize("XMLParser") == ["XML", "Parser"]
    assert t.tokenize("JSONData") == ["JSON", "Data"]


def test_tokenizer_nested() -> None:
    """Verify handling of nested type separators (+)."""
    t = Tokenizer()
    assert t.tokenize("Outer+Inner") == ["Outer", "Inner"]


def test_tokenizer_underscore() -> None:
    """Verify handling of underscores as separators."""
    t = Tokenizer()
    assert t.tokenize("m_Score") == ["m", "Score"]


def test_sanitizer_casing() -> None:
    """Verify casing preservation for acronyms in sanitizer."""
    s = Sanitizer(acronyms=["UI", "XML"])
    assert s.normalize("ui") == "UI"
    assert s.normalize("Xml") == "XML"


def test_sanitizer_reserved() -> None:
    """Verify that reserved Windows filenames are sanitized."""
    s = Sanitizer()
    assert s.normalize("CON") != "CON"
    assert s.normalize("NUL") != "NUL"


def test_sanitizer_chars() -> None:
    """Verify removal of illegal characters in sanitizer."""
    s = Sanitizer()
    assert s.normalize("File.Name") == "FileName"
    assert s.normalize("My-Name") == "My-Name"
