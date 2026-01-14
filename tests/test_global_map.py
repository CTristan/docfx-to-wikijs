import pytest
import json
from src.global_map import GlobalNamespaceMap, CURRENT_SCHEMA_VERSION

def test_load_save_roundtrip(tmp_path):
    cache_file = tmp_path / "map.json"
    cache = GlobalNamespaceMap(str(cache_file), "hash123")
    cache.update("uid1", "path/to/1")
    cache.save()
    
    # Reload
    cache2 = GlobalNamespaceMap(str(cache_file), "hash123")
    cache2.load()
    assert cache2.lookup("uid1") == "path/to/1"
    assert cache2.meta["config_hash"] == "hash123"
    assert cache2.meta["run_id"] == 1

def test_prune_stale(tmp_path):
    cache_file = tmp_path / "map.json"
    cache = GlobalNamespaceMap(str(cache_file), "hash1")
    
    # Run 1: Add item
    cache.update("keep_me", "path/1")
    cache.update("prune_me", "path/2")
    cache.save() # run_id -> 1
    
    # Run 2: Access keep_me only
    cache2 = GlobalNamespaceMap(str(cache_file), "hash1")
    cache2.load()
    cache2.lookup("keep_me") # Accessed
    # prune_me NOT accessed
    cache2.save() # run_id -> 2
    
    # Simulate skipping a lot of runs or verify threshold
    # last_seen for keep_me is 2.
    # last_seen for prune_me is 1.
    
    # Run 3: Prune with threshold 1
    # Current run will become 3.
    # keep_me age: 3 - 2 = 1. (<= 1, keep)
    # prune_me age: 3 - 1 = 2. (> 1, prune)
    
    cache3 = GlobalNamespaceMap(str(cache_file), "hash1")
    cache3.load()
    cache3.save(prune_stale_threshold=1)
    
    with open(cache_file) as f:
        data = json.load(f)
    
    assert "keep_me" in data["mapping"]
    assert "prune_me" not in data["mapping"]
    assert data["meta"]["run_id"] == 3

def test_legacy_migration(tmp_path):
    cache_file = tmp_path / "legacy.json"
    legacy_data = {
        "meta": {"schema_version": 0},
        "mapping": {
            "uid1": "path/old"
        }
    }
    with open(cache_file, "w") as f:
        json.dump(legacy_data, f)
        
    cache = GlobalNamespaceMap(str(cache_file), "newhash")
    cache.load(accept_legacy=True)
    
    assert cache.lookup("uid1") == "path/old"
    
    cache.save()
    
    with open(cache_file) as f:
        data = json.load(f)
        
    assert data["meta"]["schema_version"] == CURRENT_SCHEMA_VERSION
    assert isinstance(data["mapping"]["uid1"], dict)
    assert data["mapping"]["uid1"]["path"] == "path/old"

def test_ignore_schema_mismatch(tmp_path):
    cache_file = tmp_path / "bad_schema.json"
    data = {
        "meta": {"schema_version": 999},
        "mapping": {"uid1": "path/1"}
    }
    with open(cache_file, "w") as f:
        json.dump(data, f)
        
    cache = GlobalNamespaceMap(str(cache_file), "h")
    cache.load(accept_legacy=False)
    
    # Should be empty because ignored
    assert cache.lookup("uid1") is None
