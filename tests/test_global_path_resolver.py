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
    global_map.lookup.return_value = None
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


def test_keyword_cluster(
    resolver_deps: tuple[MagicMock, MagicMock, dict[str, Any]],
) -> None:
    """Verify that keyword clusters route items correctly."""
    analyzer, global_map, config = resolver_deps
    config["rules"]["keyword_clusters"] = {"Combat": ["Damage", "Attack"]}
    resolver = GlobalPathResolver(analyzer, global_map, config)

    item = create_item("uid1", "FireDamageBonus")
    res = resolver.resolve(item)

    assert "Global/Combat" in res.final_path
    assert res.winning_rule == "keyword"


def test_metadata_hub_base_class(
    resolver_deps: tuple[MagicMock, MagicMock, dict[str, Any]],
) -> None:
    """Verify that items are clustered by their base class if it acts as a hub."""
    analyzer, global_map, config = resolver_deps
    analyzer.metadata_index.get_base_class.return_value = "Game.Creature"
    resolver = GlobalPathResolver(analyzer, global_map, config)

    item = create_item("uid1", "ZombieCreature")
    res = resolver.resolve(item)

    assert "Global/Creature" in res.final_path
    assert res.winning_rule == "metadata_hub"


def test_metadata_hub_interface(
    resolver_deps: tuple[MagicMock, MagicMock, dict[str, Any]],
) -> None:
    """Verify that items are clustered by their interface if it acts as a hub."""
    analyzer, global_map, config = resolver_deps
    analyzer.metadata_index.get_base_class.return_value = None
    analyzer.metadata_index.get_interfaces.return_value = ["Game.IWorker"]
    config["hub_types"] = {"Game.IWorker": "Worker"}
    resolver = GlobalPathResolver(analyzer, global_map, config)

    item = create_item("uid1", "Cleaner")
    res = resolver.resolve(item)

    assert "Global/Worker" in res.final_path
    assert res.winning_rule == "metadata_hub"


def test_strong_suffix(
    resolver_deps: tuple[MagicMock, MagicMock, dict[str, Any]],
) -> None:
    """Verify that strong suffixes result in correct clustering."""
    analyzer, global_map, config = resolver_deps
    analyzer.get_strong_suffixes.return_value = {"Controller"}
    resolver = GlobalPathResolver(analyzer, global_map, config)

    item = create_item("uid1", "PlayerController")
    res = resolver.resolve(item)

    assert "Global/Controller" in res.final_path
    assert res.winning_rule == "strong_suffix"


def test_type_family(
    resolver_deps: tuple[MagicMock, MagicMock, dict[str, Any]],
) -> None:
    """Verify that type families (shared prefixes) result in correct clustering."""
    analyzer, global_map, config = resolver_deps
    analyzer.prefix_counts = {"Ability": 10}
    config["thresholds"]["min_family_size"] = 3
    resolver = GlobalPathResolver(analyzer, global_map, config)

    item = create_item("uid1", "AbilityJump")
    res = resolver.resolve(item)

    assert "Global/Ability" in res.final_path
    assert res.winning_rule == "type_family"


def test_rule_precedence(
    resolver_deps: tuple[MagicMock, MagicMock, dict[str, Any]],
) -> None:
    """Verify the precedence of rules (Hub > Priority Suffix > Strong Prefix)."""
    analyzer, global_map, config = resolver_deps
    # Setup multiple rules that could match
    analyzer.metadata_index.get_base_class.return_value = "Game.Creature"  # Hub (0.95)
    config["rules"]["priority_suffixes"] = ["UI"]  # Priority Suffix (0.9)
    analyzer.get_top_prefixes.return_value = ["Story"]  # Strong Prefix (0.8)

    resolver = GlobalPathResolver(analyzer, global_map, config)

    # Item matches all: Hub (Creature), Priority Suffix (UI), Strong Prefix (Story)
    item = create_item("uid1", "StoryCreatureUI")
    res = resolver.resolve(item)

    # Hub should win
    assert "Global/Creature" in res.final_path
    assert res.winning_rule == "metadata_hub"

    # Now remove hub, Priority Suffix should win
    analyzer.metadata_index.get_base_class.return_value = None
    analyzer.metadata_index.get_interfaces.return_value = []
    res = resolver.resolve(item)
    assert "Global/UI" in res.final_path
    assert res.winning_rule == "priority_suffix"
