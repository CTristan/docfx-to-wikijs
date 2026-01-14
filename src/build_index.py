"""Logic for building an index of UIDs from YAML files."""

from pathlib import Path
from typing import Any

from src.as_text import as_text
from src.item_info import ItemInfo
from src.iter_main_items import iter_main_items
from src.load_managed_reference import load_managed_reference


def build_index(
    yml_files: list[Path],
) -> tuple[dict[str, ItemInfo], dict[str, dict[str, Any]]]:
    """Index all DocFX YAML files to build a map of UIDs to items and references."""
    uid_to_item: dict[str, ItemInfo] = {}
    uid_to_ref: dict[str, dict[str, Any]] = {}
    for f in yml_files:
        doc = load_managed_reference(f)
        for it in iter_main_items(doc):
            uid = str(it.get("uid"))
            kind = str(it.get("type") or "").strip() or "Unknown"
            name = it.get("name") or it.get("fullName") or uid
            full_name = it.get("fullName") or it.get("name") or uid
            parent = it.get("parent")
            ns = it.get("namespace")
            summary = as_text(it.get("summary"))

            inheritance = [
                str(x.get("uid") if isinstance(x, dict) else x)
                for x in (it.get("inheritance") or [])
            ]
            implements = [
                str(x.get("uid") if isinstance(x, dict) else x)
                for x in (it.get("implements") or [])
            ]

            uid_to_item[uid] = ItemInfo(
                uid=uid,
                kind=kind,
                name=str(name),
                full_name=str(full_name),
                parent=str(parent) if parent else None,
                namespace=str(ns) if ns else None,
                summary=summary,
                inheritance=inheritance,
                implements=implements,
                file=f,
                raw=it,
            )
        for ref in doc.get("references") or []:
            if isinstance(ref, dict) and ref.get("uid"):
                uid_to_ref[str(ref["uid"])] = ref
    return uid_to_item, uid_to_ref
