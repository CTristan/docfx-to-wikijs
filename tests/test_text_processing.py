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
    assert t.tokenize("HTTPRequest") == ["HTTP", "Request"]


def test_tokenizer_digit_gluing() -> None:
    """Verify digit gluing and human-navigability precedence."""
    t = Tokenizer()
    # Basic gluing
    assert t.tokenize("2DVector") == ["2D", "Vector"]
    assert t.tokenize("Blue1") == ["Blue1"]
    assert t.tokenize("Version2") == ["Version2"]
    assert t.tokenize("2dxFX") == ["2dxFX"]

    # Complex precedence
    assert t.tokenize("HTTP2Server") == ["HTTP2", "Server"]
    assert t.tokenize("XML2JSONParser") == ["XML2", "JSON", "Parser"]
    assert t.tokenize("XML2Json") == ["XML2", "Json"]

    # Short weird cases
    assert t.tokenize("X2Y") == ["X2Y"]
    assert t.tokenize("A1B2C") == ["A1B2C"]
    assert t.tokenize("V2") == ["V2"]


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
