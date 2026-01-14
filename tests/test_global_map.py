"""Tests for the global namespace persistence map."""

import json
from pathlib import Path

from src.global_namespace_map import GlobalNamespaceMap


def test_load_save_roundtrip(tmp_path: Path) -> None:
    """Verify that the map can be saved and loaded without data loss."""
    cache_file = tmp_path / "map.json"
    cache = GlobalNamespaceMap(str(cache_file), "hash123")
    cache.update("uid1", "path/1")
    cache.save()

    cache2 = GlobalNamespaceMap(str(cache_file), "hash123")
    cache2.load()
    assert cache2.lookup("uid1") == "path/1"


def test_prune_stale(tmp_path: Path) -> None:
    """Verify that stale entries are pruned based on run count."""
    cache_file = tmp_path / "map.json"
    cache = GlobalNamespaceMap(str(cache_file), "hash1")
    cache.update("keep_me", "path/keep")
    cache.update("prune_me", "path/prune")
    cache.save()

    # Second run. keep_me is accessed.
    cache2 = GlobalNamespaceMap(str(cache_file), "hash1")
    cache2.load()
    cache2.lookup("keep_me")
    cache2.save()

    # Third run. Threshold is 1. prune_me (last seen run 1) should be pruned.
    cache3 = GlobalNamespaceMap(str(cache_file), "hash1")
    cache3.load()
    cache3.save(prune_stale_threshold=1)

    data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert "keep_me" in data["mapping"]
    assert "prune_me" not in data["mapping"]
    val_3 = 3
    assert data["meta"]["run_id"] == val_3


def test_legacy_migration(tmp_path: Path) -> None:
    """Verify that legacy string-only mappings are migrated to dicts."""
    cache_file = tmp_path / "legacy.json"
    legacy_data = {"meta": {"schema_version": 0}, "mapping": {"uid1": "path/old"}}
    cache_file.write_text(json.dumps(legacy_data), encoding="utf-8")

    cache = GlobalNamespaceMap(str(cache_file), "hash1")
    cache.load(accept_legacy=True)
    assert cache.lookup("uid1") == "path/old"

    # Save and verify it's now dict
    cache.save()

    data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert isinstance(data["mapping"]["uid1"], dict)
    assert data["mapping"]["uid1"]["path"] == "path/old"


def test_ignore_schema_mismatch(tmp_path: Path) -> None:
    """Verify that cache is ignored if schema version doesn't match."""
    cache_file = tmp_path / "bad_schema.json"
    data = {"meta": {"schema_version": 999}, "mapping": {"uid1": "path/1"}}
    cache_file.write_text(json.dumps(data), encoding="utf-8")

    cache = GlobalNamespaceMap(str(cache_file), "hash1")
    cache.load(accept_legacy=False)
    assert cache.lookup("uid1") is None
