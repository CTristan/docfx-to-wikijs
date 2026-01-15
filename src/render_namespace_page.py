"""Logic for rendering namespace overview pages."""

from src.item_info import ItemInfo
from src.link_target import LinkTarget
from src.page_path_for_fullname import page_path_for_fullname
from src.rewrite_xrefs import rewrite_xrefs
from src.should_use_global_dir import should_use_global_dir


def render_namespace_page(
    ns_fullname: str,
    types_in_ns: list[ItemInfo],
    child_namespaces: list[str],
    uid_targets: dict[str, LinkTarget],
    api_root: str,
) -> str:
    """Render a namespace landing page in Markdown."""
    parts: list[str] = [f"# Namespace {ns_fullname}", ""]

    if child_namespaces:
        parts += ["## Namespaces", ""]
        for child in sorted(child_namespaces):
            parts.append(f"- [{child}]({page_path_for_fullname(api_root, child)})")
        parts.append("")

    # Group types by kind
    kinds = ["Class", "Struct", "Interface", "Enum", "Delegate"]
    for k in kinds:
        matches = [t for t in types_in_ns if t.kind.lower() == k.lower()]
        if matches:
            plural = k + (
                "es"
                if any(
                    k.lower().endswith(suffix)
                    for suffix in ("s", "ss", "x", "z", "ch", "sh")
                )
                else "s"
            )
            parts += [f"## {plural}", ""]
            for t in sorted(matches, key=lambda x: x.name.lower()):
                # Resolved path
                t_target = uid_targets.get(t.uid)
                if t_target:
                    page = t_target.page_path
                else:
                    page = page_path_for_fullname(
                        api_root,
                        t.full_name,
                        use_global_dir=should_use_global_dir(t.namespace),
                    )

                summ = rewrite_xrefs(t.summary, uid_targets).replace("\n", " ").strip()
                if summ:
                    parts.append(f"### [{t.name}]({page})")
                    parts.append(summ)
                    parts.append("")
                else:
                    parts.append(f"### [{t.name}]({page})")
                    parts.append("")
            parts.append("")

    return "\n".join(parts).rstrip() + "\n"
