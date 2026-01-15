"""Logic for generating markdown stubs for moved or renamed pages."""

from pathlib import Path


class StubGenerator:
    """Generates redirection stubs to maintain link integrity after refactoring."""

    def __init__(self, base_output_dir: str) -> None:
        """Initialize with the base directory for generated files."""
        self.base_dir = Path(base_output_dir)

    def generate_stub(
        self, old_path_str: str, new_path_str: str, uid: str
    ) -> str | None:
        """Generate a markdown stub at old_path_str pointing to new_path_str.

        Returns the content if generated, or None if skipped (already exists).
        """
        old_path = self.base_dir / old_path_str

        # Security check: ensure we are writing inside base_dir
        try:
            target = (self.base_dir / old_path_str).resolve()
            base = self.base_dir.resolve()
            if not str(target).startswith(str(base)):
                target.relative_to(base)
        except (ValueError, RuntimeError):
            return None

        if old_path.exists():
            return None  # Immutable: never overwrite stubs or existing files

        content = self._create_stub_content(old_path_str, new_path_str, uid)

        # Ensure parent dir exists
        old_path.parent.mkdir(parents=True, exist_ok=True)
        old_path.write_text(content, encoding="utf-8")

        return content

    def _create_stub_content(self, old_path: str, new_path: str, uid: str) -> str:
        """Create the markdown content for the redirection stub."""
        title = Path(old_path).stem

        return f"""---
uid: {uid}
obsolete: true
old_path: {old_path}
new_path: {new_path}
---

# {title}

This page has moved. Please verify your reference.

[Go to new location]({new_path})
"""
