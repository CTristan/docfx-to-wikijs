import pytest
from src.text_processing import Tokenizer, Sanitizer

def test_tokenizer_basic():
    t = Tokenizer()
    assert t.tokenize("CamelCase") == ["Camel", "Case"]
    assert t.tokenize("simple") == ["simple"]
    assert t.tokenize("XMLParser") == ["XML", "Parser"]
    assert t.tokenize("UIManager") == ["UI", "Manager"]

def test_tokenizer_numbers():
    t = Tokenizer()
    assert t.tokenize("Vector3") == ["Vector3"]
    assert t.tokenize("Item2D") == ["Item", "2D"]
    assert t.tokenize("Section2B") == ["Section", "2B"] # 2 matches [0-9]+ in fallback? or B matches?
    # "Section" (Rule 2). 
    # Remaining "2B". 
    # "2" matches [A-Z0-9]+ (Rule 3). 
    # "B" matches [A-Z0-9]+ (Rule 3).
    # Wait, re.findall finds non-overlapping.
    # If "2B" matches [A-Z0-9]+ entirely? Yes.
    assert t.tokenize("Section2B") == ["Section", "2B"]

def test_tokenizer_nested():
    t = Tokenizer()
    assert t.tokenize("Outer+Inner") == ["Outer", "Inner"]
    assert t.tokenize("MyClass`1") == ["My", "Class"]

def test_tokenizer_underscore():
    t = Tokenizer()
    assert t.tokenize("m_Score") == ["m", "Score"]
    assert t.tokenize("SOME_CONSTANT") == ["SOME", "CONSTANT"]

def test_sanitizer_casing():
    s = Sanitizer(acronyms=["UI", "XML"])
    assert s.normalize("ui") == "UI"
    assert s.normalize("xml") == "XML"
    assert s.normalize("XML") == "XML"
    assert s.normalize("story") == "Story"
    assert s.normalize("Story") == "Story"
    assert s.normalize("camel") == "Camel"

def test_sanitizer_reserved():
    s = Sanitizer()
    assert s.normalize("CON") != "CON"
    assert s.normalize("con") != "Con" # Case insensitive check
    assert s.normalize("valid") == "Valid"

def test_sanitizer_chars():
    s = Sanitizer()
    assert s.normalize("File.Name") == "FileName"
    assert s.normalize("Bad/Char") == "BadChar"
