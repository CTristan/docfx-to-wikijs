"""Tests for configuration loading and merging."""

from pathlib import Path

import yaml

from src.compute_config_hash import compute_config_hash
from src.deep_merge import deep_merge
from src.load_config import load_config


def test_deep_merge_scalars() -> None:
    """Verify scalar replacement in deep merge."""
    base = {"a": 1, "b": 2}
    update = {"b": 3, "c": 4}
    merged = deep_merge(base, update)
    assert merged == {"a": 1, "b": 3, "c": 4}


def test_deep_merge_nested() -> None:
    """Verify recursive merging of dictionaries."""
    base = {"nested": {"x": 1, "y": 2}}
    update = {"nested": {"y": 3, "z": 4}}
    merged = deep_merge(base, update)
    assert merged == {"nested": {"x": 1, "y": 3, "z": 4}}


def test_deep_merge_arrays_replace() -> None:
    """Verify that arrays are replaced by default."""
    base = {"arr": [1, 2]}
    update = {"arr": [3, 4]}
    merged = deep_merge(base, update)
    assert merged == {"arr": [3, 4]}


def test_deep_merge_acronyms_additive() -> None:
    """Verify that the acronyms list is merged additively."""
    base = {"acronyms": ["A", "B"]}
    update = {"acronyms": ["B", "C"]}
    merged = deep_merge(base, update)
    assert merged["acronyms"] == ["A", "B", "C"]


def test_compute_config_hash_stability() -> None:
    """Verify that config hash is stable regardless of key order."""
    config1 = {"b": 2, "a": 1, "nested": {"y": 2, "x": 1}}
    config2 = {"a": 1, "b": 2, "nested": {"x": 1, "y": 2}}
    assert compute_config_hash(config1) == compute_config_hash(config2)


def test_load_config_defaults() -> None:
    """Verify that default config is loaded when no path is provided."""
    config = load_config(None)
    assert "thresholds" in config
    assert "rules" in config


def test_load_config_with_file(tmp_path: Path) -> None:
    """Verify that user config correctly overrides defaults."""
    config_file = tmp_path / "config.yml"
    config_data = {"thresholds": {"min_cluster_size": 999}, "acronyms": ["TEST"]}

    config_file.write_text(yaml.dump(config_data))

    loaded = load_config(str(config_file))
    val_999 = 999
    assert loaded["thresholds"]["min_cluster_size"] == val_999
    assert "UI" in loaded["acronyms"]  # Default
    assert "TEST" in loaded["acronyms"]  # Added
