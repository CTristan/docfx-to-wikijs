import pytest
from src.stub_generator import StubGenerator
from pathlib import Path

def test_generate_stub_success(tmp_path):
    generator = StubGenerator(str(tmp_path))
    content = generator.generate_stub("old.md", "new/path/new.md", "uid123")
    
    assert content is not None
    assert "uid: uid123" in content
    assert "new_path: new/path/new.md" in content
    assert "[Go to new location](new/path/new.md)" in content
    
    assert (tmp_path / "old.md").exists()

def test_generate_stub_skips_existing(tmp_path):
    generator = StubGenerator(str(tmp_path))
    (tmp_path / "existing.md").write_text("orig")
    
    content = generator.generate_stub("existing.md", "new.md", "uid1")
    assert content is None
    assert (tmp_path / "existing.md").read_text() == "orig"

def test_generate_stub_nested(tmp_path):
    generator = StubGenerator(str(tmp_path))
    content = generator.generate_stub("folder/old.md", "new.md", "uid1")
    
    assert (tmp_path / "folder/old.md").exists()

def test_security_check(tmp_path):
    generator = StubGenerator(str(tmp_path))
    # Try to write outside
    content = generator.generate_stub("../outside.md", "new.md", "uid1")
    assert content is None
