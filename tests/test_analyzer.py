import pytest
from src.analyzer import Analyzer
from src.text_processing import Tokenizer, Sanitizer
from src.metadata_index import MetadataIndex
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class MockItem:
    uid: str
    name: str
    namespace: Optional[str] = None
    inheritance: List[str] = None

def test_analyzer_counts():
    tokenizer = Tokenizer()
    sanitizer = Sanitizer()
    # Mock index
    items = {
        "A1": MockItem("A1", "StoryManager", inheritance=["Obj", "Base"]),
        "A2": MockItem("A2", "StoryPlayer", inheritance=["Obj", "Base"]),
        "B1": MockItem("B1", "UIManager", inheritance=["Obj"]),
        "C1": MockItem("C1", "Helper", inheritance=["Obj"]), # Stop token prefix?
    }
    idx = MetadataIndex(items)
    
    config = {
        "rules": {
            "stop_tokens": ["Manager", "Helper"]
        }
    }
    
    analyzer = Analyzer(tokenizer, sanitizer, idx, config)
    analyzer.analyze(list(items.values()))
    
    # Prefixes: Story (2), UI (1), Helper (1)
    assert analyzer.prefix_counts["Story"] == 2
    assert analyzer.prefix_counts["UI"] == 1
    assert analyzer.prefix_counts["Helper"] == 1
    
    # Suffixes: Manager (2), Player (1), Helper (1)
    assert analyzer.suffix_counts["Manager"] == 2
    assert analyzer.suffix_counts["Player"] == 1
    
    # Base Classes: Base (2), Obj (2)
    assert analyzer.base_class_counts["Base"] == 2
    assert analyzer.base_class_counts["Obj"] == 2

def test_analyzer_top_k():
    tokenizer = Tokenizer()
    sanitizer = Sanitizer()
    # Mock index
    # Prefixes: A(10), B(5), Stop(20)
    # Stop is "Stop"
    config = {"rules": {"stop_tokens": ["Stop"]}}
    
    analyzer = Analyzer(tokenizer, sanitizer, MetadataIndex({}), config)
    analyzer.prefix_counts["A"] = 10
    analyzer.prefix_counts["B"] = 5
    analyzer.prefix_counts["Stop"] = 20
    
    top = analyzer.get_top_prefixes(k=2, min_size=6)
    assert "A" in top
    assert "B" not in top # < 6
    assert "Stop" not in top # Stop token
    
    top_all = analyzer.get_top_prefixes(k=5, min_size=1)
    assert top_all == ["A", "B"]

def test_analyzer_suffixes():
    tokenizer = Tokenizer()
    sanitizer = Sanitizer()
    config = {"rules": {"stop_tokens": ["Stop"]}}
    analyzer = Analyzer(tokenizer, sanitizer, MetadataIndex({}), config)
    
    analyzer.suffix_counts["A"] = 10
    analyzer.suffix_counts["B"] = 5
    analyzer.suffix_counts["Stop"] = 20
    
    strong = analyzer.get_strong_suffixes(min_size=6)
    assert "A" in strong
    assert "B" not in strong
    assert "Stop" not in strong
