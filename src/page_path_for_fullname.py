"""Utility for determining the page path based on a full name."""

from src.dot_safe import dot_safe


def page_path_for_fullname(
    api_root: str,
    full_name: str,
    *,
    use_global_dir: bool = False,
) -> str:
    """Generate the Wiki.js page path for a given full name."""
    # Subfolders: Foo.Bar.Baz -> /api/Foo/Bar/Baz
    parts = full_name.split(".")
    processed = [dot_safe(p) for p in parts]
    if use_global_dir:
        processed.insert(0, "Global")
    path = "/".join(processed)
    return f"{api_root}/{path}"
