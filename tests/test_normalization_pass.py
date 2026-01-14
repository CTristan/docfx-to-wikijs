"""Unit tests for the NormalizationPass logic."""

import re
from pathlib import Path

from src.item_info import ItemInfo
from src.normalization_pass import NormalizationPass


class MockSanitizer:
    """Mock sanitizer for testing."""

    def normalize(self, text: str) -> str:
        """Normalize text by removing underscores and spaces."""
        return text.replace("_", "").replace(" ", "")


class MockTokenizer:
    """Mock tokenizer for testing."""

    def tokenize(self, text: str) -> list[str]:
        """Tokenize by splitting on CamelCase and numbers."""
        # Simplified TitleCase split for tests
        return re.findall(r"[A-Z][a-z0-9]+|[A-Z]{2,}(?![a-z])|[0-9]+", text)


def test_normalization_merge_invariants() -> None:
    """Verify merge invariants like pinned root precedence."""
    config = {
        "thresholds": {
            "min_cluster_size": 3,
            "top_k": 20,
            "max_top_level_folders": 40,
        },
        "rules": {
            "pinned_roots": ["PinnedRoot"],
            "pinned_allow_singleton": True,
        },
    }

    pass_obj = NormalizationPass(config, MockSanitizer(), MockTokenizer())

    # 1. Pinned root representative invariant
    pass_obj.union_find = {"PinnedRoot": "PinnedRoot", "Other": "Other"}
    pass_obj.pinned_roots = {"PinnedRoot"}
    pass_obj._union("PinnedRoot", "Other")  # noqa: SLF001
    assert pass_obj._find("Other") == "PinnedRoot"  # noqa: SLF001

    # 2. Pinned-pinned union disallowed
    pass_obj.union_find = {"P1": "P1", "P2": "P2"}
    pass_obj.pinned_roots = {"P1", "P2"}
    pass_obj._union("P1", "P2")  # noqa: SLF001
    assert pass_obj._find("P1") == "P1"  # noqa: SLF001
    assert pass_obj._find("P2") == "P2"  # noqa: SLF001

    # 3. Lexicographical winner
    pass_obj.union_find = {"A": "A", "B": "B"}
    pass_obj.pinned_roots = set()
    pass_obj._union("A", "B")  # noqa: SLF001
    assert pass_obj._find("B") == "A"  # noqa: SLF001


def test_normalization_full_flow() -> None:
    """Verify the full normalization flow with rerouting."""
    config = {
        "thresholds": {
            "min_cluster_size": 2,
            "top_k": 2,
            "max_top_level_folders": 2,
        },
        "rules": {
            "pinned_roots": ["Pinned"],
            "pinned_allow_singleton": True,
            "stop_tokens": [],
        },
    }

    pass_obj = NormalizationPass(config, MockSanitizer(), MockTokenizer())

    # Items:
    # Pinned: 1 item (should stay because pinned_allow_singleton)
    # BigCluster: 3 items (should stay)
    # SmallCluster: 1 item (should be rerouted or misc)

    items = [
        ItemInfo(
            "p1",
            "Class",
            "PinnedObj",
            "PinnedObj",
            None,
            None,
            "",
            [],
            [],
            Path("p1.yml"),
            {},
        ),
        ItemInfo(
            "b1", "Class", "Big1", "Big1", None, None, "", [], [], Path("b1.yml"), {}
        ),
        ItemInfo(
            "b2", "Class", "Big2", "Big2", None, None, "", [], [], Path("b2.yml"), {}
        ),
        ItemInfo(
            "b3", "Class", "Big3", "Big3", None, None, "", [], [], Path("b3.yml"), {}
        ),
        ItemInfo(
            "s1",
            "Class",
            "Small1",
            "Small1",
            None,
            None,
            "",
            [],
            [],
            Path("s1.yml"),
            {},
        ),
    ]

    items_by_uid = {it.uid: it for it in items}
    initial_assignments = {
        "p1": ("manual", "Pinned"),
        "b1": ("prefix", "Big"),
        "b2": ("prefix", "Big"),
        "b3": ("prefix", "Big"),
        "s1": ("prefix", "Small"),
    }

    # original_signals for rerouting
    # s1 also matches Big as strong_prefix
    original_signals = {
        "p1": [("manual", "Pinned", 1.0)],
        "b1": [("prefix", "Big", 0.8)],
        "b2": [("prefix", "Big", 0.8)],
        "b3": [("prefix", "Big", 0.8)],
        "s1": [("prefix", "Small", 0.8), ("strong_prefix", "Big", 0.7)],
    }

    final = pass_obj.run(initial_assignments, items_by_uid, original_signals)

    assert final["p1"] == "Pinned"
    assert final["b1"] == "Big"
    assert final["b2"] == "Big"
    assert final["b3"] == "Big"
    assert final["s1"] == "Big"  # Rerouted from Small to Big because Big is kept!

    print("test_normalization_full_flow passed!")


if __name__ == "__main__":
    test_normalization_merge_invariants()
    test_normalization_full_flow()
