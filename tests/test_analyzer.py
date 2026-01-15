"""Tests for the analyzer module."""

from dataclasses import dataclass, field

from src.analyzer import Analyzer
from src.metadata_index import MetadataIndex
from src.sanitizer import Sanitizer
from src.tokenizer import Tokenizer


@dataclass
class MockItem:
    """Mock item for testing the analyzer."""

    uid: str
    name: str
    namespace: str | None = None
    inheritance: list[str] = field(default_factory=list)


def test_analyzer_counts() -> None:
    """Verify that analyzer correctly counts prefixes, suffixes and base classes."""
    tokenizer = Tokenizer()
    sanitizer = Sanitizer()
    # Mock index
    items = {
        "A1": MockItem("A1", "StoryManager", inheritance=["Obj", "Base"]),
        "A2": MockItem("A2", "StoryPlayer", inheritance=["Obj", "Base"]),
        "B1": MockItem("B1", "UIManager", inheritance=["Obj"]),
        "C1": MockItem("C1", "Helper", inheritance=["Obj"]),
    }
    idx = MetadataIndex(items)

    config = {"rules": {"stop_tokens": ["Manager", "Helper"]}}

    analyzer = Analyzer(tokenizer, sanitizer, idx, config)
    analyzer.analyze(list(items.values()))  # type: ignore[arg-type]

    # Expected counts
    story_count = 2
    one = 1
    base_count = 2
    obj_count = 2

    assert analyzer.prefix_counts["Story"] == story_count
    assert analyzer.prefix_counts["UI"] == one
    assert analyzer.prefix_counts["Helper"] == one

    assert analyzer.suffix_counts["Manager"] == story_count
    assert analyzer.suffix_counts["Player"] == one

    assert analyzer.base_class_counts["Base"] == base_count
    assert analyzer.base_class_counts["Obj"] == obj_count


def test_analyzer_top_k() -> None:
    """Verify top-k prefix extraction logic."""
    tokenizer = Tokenizer()
    sanitizer = Sanitizer()
    config = {"rules": {"stop_tokens": ["Stop"]}}

    analyzer = Analyzer(tokenizer, sanitizer, MetadataIndex({}), config)
    analyzer.prefix_counts["A"] = 10
    analyzer.prefix_counts["B"] = 5
    analyzer.prefix_counts["Stop"] = 20

    top = analyzer.get_top_prefixes(k=2, min_size=6)
    assert "A" in top
    assert "B" not in top
    assert "Stop" not in top

    top_all = analyzer.get_top_prefixes(k=5, min_size=1)
    assert top_all == ["A", "B"]


def test_analyzer_suffixes() -> None:
    """Verify strong suffix identification logic."""
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
