import pytest
from unittest.mock import MagicMock
from pathlib import Path
from src.global_path_resolver import GlobalPathResolver
from src.models import ItemInfo
from src.global_config import deep_merge, DEFAULT_CONFIG

@pytest.fixture
def resolver_deps():
    analyzer = MagicMock()
    global_map = MagicMock()
    config = deep_merge(DEFAULT_CONFIG, {
        "rules": {
            "priority_suffixes": ["UI"],
            "keyword_clusters": {"Bosses": ["Boss"]},
            "metadata_denylist": ["Object"]
        },
        "thresholds": {"top_k": 5, "min_cluster_size": 2}
    })
    
    # Mock analyzer behavior
    # IMPORTANT: Use side_effect=None to allow return_value to work in tests
    analyzer.tokenizer.tokenize.side_effect = None
    analyzer.tokenizer.tokenize.return_value = ["Item"]
    
    analyzer.sanitizer.normalize.side_effect = lambda x: x # No-op sanitizer
    analyzer.get_top_prefixes.return_value = ["Story"]
    analyzer.get_strong_suffixes.return_value = ["Manager"]
    analyzer.metadata_index.get_base_class.return_value = None
    analyzer.metadata_index.get_interfaces.return_value = []
    analyzer.prefix_counts = {}
    
    global_map.lookup.return_value = None
    
    return analyzer, global_map, config

def create_item(uid, name, **kwargs):
    return ItemInfo(
        uid=uid, kind="Class", name=name, full_name=name,
        parent=None, namespace=None, summary="",
        inheritance=kwargs.get("inheritance", []),
        implements=kwargs.get("implements", []),
        file=Path(), raw={}
    )

def test_cache_hit(resolver_deps):
    analyzer, global_map, config = resolver_deps
    global_map.lookup.return_value = "Global/Cached/Item.md"
    
    resolver = GlobalPathResolver(analyzer, global_map, config)
    item = create_item("uid1", "Item")
    
    res = resolver.resolve(item)
    assert res.final_path == "Global/Cached/Item.md"
    assert res.winning_rule == "cache"

def test_priority_suffix_wins(resolver_deps):
    analyzer, global_map, config = resolver_deps
    analyzer.tokenizer.tokenize.return_value = ["Inventory", "UI"]
    
    resolver = GlobalPathResolver(analyzer, global_map, config)
    item = create_item("uid1", "InventoryUI")
    
    res = resolver.resolve(item)
    assert "UI" in res.final_path
    assert res.winning_rule == "priority_suffix"

def test_strong_prefix(resolver_deps):
    analyzer, global_map, config = resolver_deps
    analyzer.tokenizer.tokenize.return_value = ["Story", "Event"]
    # Story is in top_prefixes (mocked)
    
    resolver = GlobalPathResolver(analyzer, global_map, config)
    item = create_item("uid1", "StoryEvent")
    
    res = resolver.resolve(item)
    assert "Story" in res.final_path
    assert res.winning_rule == "strong_prefix"

def test_collision_file_vs_file(resolver_deps):
    analyzer, global_map, config = resolver_deps
    resolver = GlobalPathResolver(analyzer, global_map, config)
    
    # First item
    item1 = create_item("uid1", "MyItem")
    analyzer.tokenizer.tokenize.return_value = ["MyItem"]
    res1 = resolver.resolve(item1)
    
    # Second item same name
    item2 = create_item("uid2", "MyItem")
    res2 = resolver.resolve(item2)
    
    assert res1.final_path != res2.final_path
    assert "MyItem" in res2.final_path
    assert "_" in res2.final_path # Suffix

def test_collision_folder_vs_file(resolver_deps):
    analyzer, global_map, config = resolver_deps
    
    # Force override for Story -> Global/Story.md
    config["path_overrides"] = {
        "uid2": "Global/Story.md"
    }
    
    resolver = GlobalPathResolver(analyzer, global_map, config)
    
    # 1. Process item that creates a folder "Global/Story"
    analyzer.tokenizer.tokenize.return_value = ["Story", "Event"] 
    # -> Global/Story/StoryEvent.md
    item1 = create_item("uid1", "StoryEvent")
    resolver.resolve(item1)
    
    # 2. Process item "Story" with override to Global/Story.md
    # This should conflict with folder Global/Story created by item1
    item2 = create_item("uid2", "Story")
    
    res2 = resolver.resolve(item2)
    
    # Expect rename to Story_Page.md
    assert "Story_Page.md" in res2.final_path
    # And it should be in Global/
    assert res2.final_path == "Global/Story_Page.md"