import pytest
from src.global_config import deep_merge, compute_config_hash, load_config, DEFAULT_CONFIG
import yaml
import json

def test_deep_merge_scalars():
    base = {"a": 1, "b": 2}
    update = {"b": 3, "c": 4}
    result = deep_merge(base, update)
    assert result == {"a": 1, "b": 3, "c": 4}

def test_deep_merge_nested():
    base = {"nested": {"x": 1, "y": 2}}
    update = {"nested": {"y": 3, "z": 4}}
    result = deep_merge(base, update)
    assert result == {"nested": {"x": 1, "y": 3, "z": 4}}

def test_deep_merge_arrays_replace():
    base = {"arr": [1, 2]}
    update = {"arr": [3, 4]}
    result = deep_merge(base, update)
    assert result == {"arr": [3, 4]}

def test_deep_merge_acronyms_additive():
    base = {"acronyms": ["A", "B"]}
    update = {"acronyms": ["B", "C"]}
    result = deep_merge(base, update)
    # Deduplicated and sorted
    assert result["acronyms"] == ["A", "B", "C"]

def test_compute_config_hash_stability():
    config1 = {"b": 2, "a": 1, "nested": {"y": 2, "x": 1}}
    config2 = {"a": 1, "b": 2, "nested": {"x": 1, "y": 2}}
    assert compute_config_hash(config1) == compute_config_hash(config2)

def test_load_config_defaults():
    config = load_config(None)
    # Deep compare against DEFAULT_CONFIG copy
    assert config["thresholds"] == DEFAULT_CONFIG["thresholds"]

def test_load_config_with_file(tmp_path):
    config_file = tmp_path / "config.yml"
    config_data = {
        "thresholds": {"min_cluster_size": 999},
        "acronyms": ["TEST"]
    }
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")
    
    loaded = load_config(str(config_file))
    assert loaded["thresholds"]["min_cluster_size"] == 999
    assert "UI" in loaded["acronyms"] # Default
    assert "TEST" in loaded["acronyms"] # Added
