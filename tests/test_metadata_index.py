"""Tests for the metadata index."""

from dataclasses import dataclass, field

from src.metadata_index import MetadataIndex


@dataclass
class MockItem:
    """Mock item for testing inheritance lookups."""

    inheritance: list[str] = field(default_factory=list)
    implements: list[str] = field(default_factory=list)


def test_get_base_class() -> None:
    """Verify that the immediate base class is correctly identified."""
    items = {
        "Derived": MockItem(inheritance=["Object", "Base"]),
        "Root": MockItem(inheritance=[]),
    }
    idx = MetadataIndex(items)
    assert idx.get_base_class("Derived") == "Base"
    assert idx.get_base_class("Root") is None
    assert idx.get_base_class("Unknown") is None


def test_get_interfaces() -> None:
    """Verify that implemented interfaces are correctly retrieved."""
    items = {
        "Impl": MockItem(implements=["ISome", "IOther"]),
        "None": MockItem(implements=[]),
    }
    idx = MetadataIndex(items)
    assert idx.get_interfaces("Impl") == ["ISome", "IOther"]
    assert idx.get_interfaces("None") == []
