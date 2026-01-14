"""Tests for the global path resolver logic."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.global_path_resolver import GlobalPathResolver
from src.item_info import ItemInfo
from src.tokenizer import Tokenizer


@pytest.fixture
def resolver_deps() -> tuple[MagicMock, MagicMock, dict[str, Any]]:
    """Fixture providing dependencies for the GlobalPathResolver."""
    tokenizer = Tokenizer()
    analyzer = MagicMock()
    analyzer.tokenizer = tokenizer
    global_map = MagicMock()
    config = {
        "thresholds": {"min_cluster_size": 1, "top_k": 5},
        "rules": {
            "priority_suffixes": ["UI"],
            "stop_tokens": [],
            "keyword_clusters": {},
            "metadata_denylist": [],
        },
        "hub_types": {},
        "acronyms": [],
    }
    analyzer.sanitizer.normalize.side_effect = lambda x: x
    analyzer.get_top_prefixes.return_value = ["Story"]
    analyzer.get_strong_suffixes.return_value = set()
    analyzer.prefix_counts = {}
    return analyzer, global_map, config


def create_item(uid: str, name: str, **kwargs: object) -> ItemInfo:
    """Create an ItemInfo object for testing."""
    return ItemInfo(
        uid=uid,
        name=name,
        full_name=name,
        kind="Class",
        parent=None,
        namespace=None,
        summary="",
        inheritance=[],
        implements=[],
        file=MagicMock(),
        raw={},
        **kwargs,
    )


def test_cache_hit(resolver_deps: tuple[MagicMock, MagicMock, dict[str, Any]]) -> None:
    """Verify that cached paths are returned immediately."""
    analyzer, global_map, config = resolver_deps
    global_map.lookup.return_value = "Global/Cached/Item.md"

    resolver = GlobalPathResolver(analyzer, global_map, config)
    item = create_item("uid1", "MyItem")
    res = resolver.resolve(item)

    assert res.final_path == "Global/Cached/Item.md"
    assert res.winning_rule == "cache"


def test_priority_suffix_wins(
    resolver_deps: tuple[MagicMock, MagicMock, dict[str, Any]],
) -> None:
    """Verify that priority suffixes take precedence over other rules."""
    analyzer, global_map, config = resolver_deps
    global_map.lookup.return_value = None

    resolver = GlobalPathResolver(analyzer, global_map, config)
    item = create_item("uid1", "InventoryUI")
    res = resolver.resolve(item)

    assert "UI" in res.final_path
    assert res.winning_rule == "priority_suffix"


def test_strong_prefix(
    resolver_deps: tuple[MagicMock, MagicMock, dict[str, Any]],
) -> None:
    """Verify that strong prefixes result in correct clustering."""
    analyzer, global_map, config = resolver_deps
    global_map.lookup.return_value = None

    resolver = GlobalPathResolver(analyzer, global_map, config)
    item = create_item("uid1", "StoryEvent")
    res = resolver.resolve(item)

    assert "Global/Story" in res.final_path
    assert res.winning_rule == "strong_prefix"


def test_collision_file_vs_file(
    resolver_deps: tuple[MagicMock, MagicMock, dict[str, Any]],
) -> None:
    """Verify that file vs file collisions are resolved via hash suffix."""
    analyzer, global_map, config = resolver_deps
    resolver = GlobalPathResolver(analyzer, global_map, config)

    # First item
    item1 = create_item("uid1", "SameName")
    resolver.resolve(item1)

    # Second item with same name
    item2 = create_item("uid2", "SameName")
    res2 = resolver.resolve(item2)

    assert res2.final_path != resolver.assigned_paths["uid1"]
    assert "_Page" not in res2.final_path  # _Page is for folder collisions


def test_collision_folder_vs_file(
    resolver_deps: tuple[MagicMock, MagicMock, dict[str, Any]],
) -> None:
    """Verify that folder vs file collisions result in a _Page suffix."""
    analyzer, global_map, config = resolver_deps
    global_map.lookup.return_value = None
    # Add an override to force a path that would collide with a folder
    config["path_overrides"] = {"uid2": "Global/Story.md"}
    resolver = GlobalPathResolver(analyzer, global_map, config)

    # Register "Global/Story" as a folder by resolving an item into it
    resolver.resolve(create_item("uid1", "StoryItem"))

    # Now resolve an item forced to "Global/Story.md" via override
    res = resolver.resolve(create_item("uid2", "SomeClass"))

    assert res.final_path == "Global/Story_Page.md"
