"""Tests for the stub generator."""

from pathlib import Path

from src.stub_generator import StubGenerator


def test_generate_stub_success(tmp_path: Path) -> None:
    """Verify that a stub is successfully generated when file doesn't exist."""
    generator = StubGenerator(str(tmp_path))
    content = generator.generate_stub("old.md", "new/path/new.md", "uid123")
    assert content is not None
    assert (tmp_path / "old.md").exists()
    assert "uid123" in content
    assert "new/path/new.md" in content


def test_generate_stub_skips_existing(tmp_path: Path) -> None:
    """Verify that stubs never overwrite existing files."""
    generator = StubGenerator(str(tmp_path))
    (tmp_path / "existing.md").write_text("orig")
    content = generator.generate_stub("existing.md", "new.md", "uid1")
    assert content is None
    assert (tmp_path / "existing.md").read_text() == "orig"


def test_generate_stub_nested(tmp_path: Path) -> None:
    """Verify that stubs can be generated in nested subdirectories."""
    generator = StubGenerator(str(tmp_path))
    generator.generate_stub("folder/old.md", "new.md", "uid1")
    assert (tmp_path / "folder" / "old.md").exists()


def test_security_check(tmp_path: Path) -> None:
    """Verify that stubs cannot be written outside the base directory."""
    generator = StubGenerator(str(tmp_path))
    # Try to write outside
    content = generator.generate_stub("../outside.md", "new.md", "uid1")
    assert content is None
    assert not (tmp_path.parent / "outside.md").exists()
