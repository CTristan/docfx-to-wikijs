"""Logic for mapping UIDs to target URLs or file paths."""

from typing import Any

from src.header_slug import header_slug
from src.is_member_kind import is_member_kind
from src.is_namespace_kind import is_namespace_kind
from src.is_type_kind import is_type_kind
from src.item_info import ItemInfo
from src.link_target import LinkTarget
from src.page_path_for_fullname import page_path_for_fullname
from src.resolution_result import ResolutionResult
from src.should_use_global_dir import should_use_global_dir


def build_link_targets(
    uid_to_item: dict[str, ItemInfo],
    uid_to_ref: dict[str, dict[str, Any]],
    api_root: str,
    global_resolved: dict[str, ResolutionResult] | None = None,
) -> dict[str, LinkTarget]:
    """Build a map of UIDs to link targets."""
    targets: dict[str, LinkTarget] = {}
    _add_internal_page_targets(targets, uid_to_item, api_root, global_resolved or {})
    _add_member_anchor_targets(targets, uid_to_item)
    _add_reference_targets(targets, uid_to_ref)
    return targets


def _add_internal_page_targets(
    targets: dict[str, LinkTarget],
    uid_to_item: dict[str, ItemInfo],
    api_root: str,
    global_resolved: dict[str, ResolutionResult],
) -> None:
    """Add targets for internal types and namespaces (pages)."""
    for uid, item in uid_to_item.items():
        if is_namespace_kind(item.kind) or is_type_kind(item.kind):
            use_global = is_type_kind(item.kind) and should_use_global_dir(
                item.namespace
            )

            # Check resolved global map first
            if use_global and global_resolved and uid in global_resolved:
                final_path = global_resolved[uid].final_path
                # final_path is relative to api root (e.g. Global/Story/Item.md)
                # Wiki path: /api/Global/Story/Item
                rel = final_path.replace(".md", "")
                page = f"{api_root}/{rel}"
            else:
                page = page_path_for_fullname(
                    api_root,
                    item.full_name,
                    use_global_dir=use_global,
                )

            title = item.name or item.full_name or uid
            targets[uid] = LinkTarget(title=title, page_path=page)


def _add_member_anchor_targets(
    targets: dict[str, LinkTarget],
    uid_to_item: dict[str, ItemInfo],
) -> None:
    """Add targets for members (anchors on internal pages)."""
    for uid, item in uid_to_item.items():
        if is_member_kind(item.kind) and item.parent:
            parent_target = targets.get(item.parent)
            if parent_target:
                anchor = header_slug(item.name or item.full_name)
                page_with_anchor = f"{parent_target.page_path}#{anchor}"
                title = item.name or item.full_name or uid
                targets[uid] = LinkTarget(title=title, page_path=page_with_anchor)


def _add_reference_targets(
    targets: dict[str, LinkTarget],
    uid_to_ref: dict[str, dict[str, Any]],
) -> None:
    """Add targets from external or internal references."""
    # Pass 1: Direct hrefs and initial population
    for uid, ref in uid_to_ref.items():
        if uid in targets:
            continue
        href = ref.get("href")
        title = ref.get("name") or ref.get("fullName") or uid
        if href:
            targets[uid] = LinkTarget(title=str(title), page_path=str(href))
        else:
            targets[uid] = LinkTarget(title=str(title), page_path="#")

    # Pass 2: Resolve via definition for those still without a real page_path (i.e. "#")
    for uid, ref in uid_to_ref.items():
        if targets[uid].page_path == "#":
            definition = ref.get("definition")
            if definition and str(definition) in targets:
                d_target = targets[str(definition)]
                if d_target.page_path != "#":
                    # Use definition's title if our title is just the UID
                    title = targets[uid].title
                    if title == uid:
                        title = d_target.title
                    targets[uid] = LinkTarget(title=title, page_path=d_target.page_path)
