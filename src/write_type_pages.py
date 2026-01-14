"""Logic for writing type pages to disk."""

import argparse
from pathlib import Path

from src.is_type_kind import is_type_kind
from src.item_info import ItemInfo
from src.link_target import LinkTarget
from src.output_file_for_page import output_file_for_page
from src.page_path_for_fullname import page_path_for_fullname
from src.render_type_page import render_type_page
from src.should_use_global_dir import should_use_global_dir


def write_type_pages(
    uid_to_item: dict[str, ItemInfo],
    uid_targets: dict[str, LinkTarget],
    args: argparse.Namespace,
    out_root: Path,
) -> int:
    """Write all type pages to disk."""
    written = 0
    type_items = [it for it in uid_to_item.values() if is_type_kind(it.kind)]
    total_types = len(type_items)
    print(f"Writing {total_types} type pages...")
    for it in type_items:
        target = uid_targets.get(it.uid)
        if not target:
            use_global = should_use_global_dir(it.namespace)
            page_path = page_path_for_fullname(
                args.api_root,
                it.full_name,
                use_global_dir=use_global,
            )
        else:
            page_path = target.page_path

        md = render_type_page(
            it,
            uid_to_item=uid_to_item,
            uid_targets=uid_targets,
            include_member_details=args.include_member_details,
            canonical_path=page_path,
        )
        out_file = output_file_for_page(out_root, page_path)
        out_file.write_text(md, encoding="utf-8")
        written += 1
        if written % 50 == 0:
            print(f"  ... wrote {written}/{total_types} types")
    return written
