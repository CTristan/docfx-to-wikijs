import pytest
from src.metadata_index import MetadataIndex
from dataclasses import dataclass, field
from typing import List

@dataclass
class MockItem:
    inheritance: List[str] = field(default_factory=list)
    implements: List[str] = field(default_factory=list)

def test_get_base_class():
    items = {
        "Derived": MockItem(inheritance=["Object", "Base"]),
        "Root": MockItem(inheritance=[]),
    }
    idx = MetadataIndex(items)
    
    assert idx.get_base_class("Derived") == "Base"
    assert idx.get_base_class("Root") is None
    assert idx.get_base_class("Missing") is None

def test_get_interfaces():
    items = {
        "Impl": MockItem(implements=["ISome", "IOther"]),
        "None": MockItem(),
    }
    idx = MetadataIndex(items)
    
    assert idx.get_interfaces("Impl") == ["ISome", "IOther"]
    assert idx.get_interfaces("None") == []
