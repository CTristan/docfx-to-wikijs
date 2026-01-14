import os
from pathlib import Path
from typing import Optional

class StubGenerator:
    def __init__(self, base_output_dir: str):
        self.base_dir = Path(base_output_dir)

    def generate_stub(self, old_path_str: str, new_path_str: str, uid: str) -> Optional[str]:
        """
        Generates a markdown stub at old_path_str pointing to new_path_str.
        Returns the content if generated, or None if skipped (exists).
        """
        old_path = self.base_dir / old_path_str
        
        # Security check: ensure we are writing inside base_dir
        # Only if strict security is needed. For CLI tool, just checking if valid path is usually enough.
        # But let's be safe.
        try:
            # Check if resolved path is relative to base
            # Note: this might fail if old_path_str is absolute or goes up ..
            # We assume old_path_str is relative to output dir.
            target = (self.base_dir / old_path_str).resolve()
            base = self.base_dir.resolve()
            if not str(target).startswith(str(base)):
                 # This simple string check is sometimes safer than relative_to which raises ValueError
                 # but relative_to is more robust against symlinks.
                 target.relative_to(base)
        except (ValueError, RuntimeError):
            return None

        if old_path.exists():
            return None  # Immutable: never overwrite stubs or existing files with stubs

        content = self._create_stub_content(old_path_str, new_path_str, uid)
        
        # Ensure parent dir exists
        old_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(old_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return content

    def _create_stub_content(self, old_path: str, new_path: str, uid: str) -> str:
        title = Path(old_path).stem
        
        # Construct a link. We assume paths are relative to the site root or Wiki root.
        # Ideally, we make it a relative link from old file to new file if we want it to work in file view.
        # But for Wiki.js, absolute path from root is usually safer if we know the root.
        # We'll just use the provided new_path string.
        
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
