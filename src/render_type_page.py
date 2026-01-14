"""Logic for rendering type detail pages."""

from typing import Any

from src.as_text import as_text
from src.is_member_kind import is_member_kind
from src.item_info import ItemInfo
from src.link_target import LinkTarget
from src.md_codeblock import md_codeblock
from src.md_table import md_table
from src.namespace_of import namespace_of
from src.rewrite_xrefs import rewrite_xrefs


def render_type_page(
    item: ItemInfo,
    uid_to_item: dict[str, ItemInfo],
    uid_targets: dict[str, LinkTarget],
    *,
    include_member_details: bool = True,
    canonical_path: str | None = None,
) -> str:
    """Render a type page (class, struct, etc.) in Markdown."""
    parts = []
    if canonical_path or item.uid:
        parts.append("---")
        parts.append(f"uid: {item.uid}")
        if canonical_path:
            parts.append(f"canonical_path: {canonical_path}")
        parts.append("---")
        parts.append("")

    raw = item.raw
    kind_label = item.kind.capitalize()
    parts += [f"# {kind_label} {item.name}", ""]

    parts.extend(_render_type_metadata(item, uid_targets))
    parts.extend(_render_type_attributes(item, uid_targets))

    summary = rewrite_xrefs(as_text(raw.get("summary")), uid_targets)
    if summary:
        parts += [summary, ""]

    syntax = raw.get("syntax") or {}
    sig = as_text(syntax.get("content"))
    if sig:
        parts += [md_codeblock("csharp", sig), ""]

    parts.extend(_render_type_inheritance(item, uid_targets))
    parts.extend(_render_type_derived(item, uid_targets))
    parts.extend(_render_type_implements(item, uid_targets))
    parts.extend(_render_type_inherited_members(item, uid_targets))
    parts.extend(_render_type_extension_methods(item, uid_targets))

    remarks = rewrite_xrefs(as_text(raw.get("remarks")), uid_targets)
    if remarks:
        parts += ["## Remarks", remarks, ""]

    example = rewrite_xrefs(as_text(raw.get("example")), uid_targets)
    if example:
        parts += ["## Examples", example, ""]

    if include_member_details:
        parts.extend(_render_type_members(item, uid_to_item, uid_targets))

    parts.extend(_render_type_seealso(item, uid_targets))

    return "\n".join(parts).rstrip() + "\n"


def _render_type_metadata(
    item: ItemInfo,
    uid_targets: dict[str, LinkTarget],
) -> list[str]:
    """Render type metadata (namespace, assembly)."""
    parts = []
    ns = namespace_of(item)
    if ns:
        ns_parts = ns.split(".")
        ns_links = []
        curr = ""
        for p in ns_parts:
            if curr:
                curr += "."
            curr += p
            t = uid_targets.get(curr)
            ns_links.append(f"[{p}]({t.page_path})" if t else p)
        parts.append(f"**Namespace:** {' . '.join(ns_links)}")

    assemblies = item.raw.get("assemblies")
    if assemblies:
        formatted_assemblies = [
            a if str(a).lower().endswith(".dll") else f"{a}.dll" for a in assemblies
        ]
        parts.append(f"**Assembly:** {', '.join(formatted_assemblies)}")
    if parts:
        parts.append("")
    return parts


def _render_type_attributes(
    item: ItemInfo,
    uid_targets: dict[str, LinkTarget],
) -> list[str]:
    """Render type attributes."""
    parts = []
    attrs = item.raw.get("attributes")
    if attrs:
        for a in attrs:
            atype = a.get("type")
            at = uid_targets.get(atype)
            parts.append(
                f"[`[{at.title if at else atype}]`]({at.page_path if at else '#'})",
            )
        parts.append("")
    return parts


def _render_type_inheritance(
    item: ItemInfo,
    uid_targets: dict[str, LinkTarget],
) -> list[str]:
    """Render inheritance chain."""
    parts = []
    inheritance = item.raw.get("inheritance") or []
    if inheritance:
        parts.append("## Inheritance")
        chain = []
        for u in inheritance:
            uid = str(u.get("uid")) if isinstance(u, dict) else str(u)
            t = uid_targets.get(uid)
            chain.append(f"[{t.title}]({t.page_path})" if t else f"`{uid}`")
        chain.append(item.name)
        parts.append(" → ".join(chain))
        parts.append("")
    return parts


def _render_type_inherited_members(
    item: ItemInfo,
    uid_targets: dict[str, LinkTarget],
) -> list[str]:
    """Render inherited members list."""
    parts = []
    inherited = item.raw.get("inheritedMembers") or []
    if inherited:
        parts.append("## Inherited Members")
        links = []
        for uid in inherited:
            t = uid_targets.get(uid)
            if t:
                links.append(f"[{t.title}]({t.page_path})")
            else:
                name = uid.split(".")[-1]
                links.append(f"`{name}`")
        parts.append(", ".join(links))
        parts.append("")
    return parts


def _render_member_params(
    syntax: dict[str, Any],
    uid_targets: dict[str, LinkTarget],
) -> list[str]:
    """Render member parameters table."""
    parts = []
    params = syntax.get("parameters") or []
    if params:
        parts.append("#### Parameters")
        parts.append("")
        rows: list[list[str]] = []
        for p in params:
            pname = str(p.get("id") or p.get("name") or "")
            ptype = rewrite_xrefs(as_text(p.get("type")), uid_targets)
            pdesc = rewrite_xrefs(as_text(p.get("description")), uid_targets)
            rows.append([f"`{pname}`", f"`{ptype}`" if ptype else "", pdesc])
        parts.append(md_table(["Name", "Type", "Description"], rows))
        parts.append("")
    return parts


def _render_member_returns(
    m: ItemInfo,
    syntax: dict[str, Any],
    uid_targets: dict[str, LinkTarget],
) -> list[str]:
    """Render member return value section."""
    parts = []
    ret = syntax.get("return") or {}
    rtype = rewrite_xrefs(as_text(ret.get("type")), uid_targets)
    rdesc = rewrite_xrefs(as_text(ret.get("description")), uid_targets)
    if rtype or rdesc:
        label = "Returns"
        if m.kind.lower() == "property":
            label = "Property Value"
        elif m.kind.lower() == "field":
            label = "Field Value"

        parts.append(f"#### {label}")
        parts.append("")
        if rtype:
            parts.append(f"**Type:** {rtype}")
            parts.append("")
        if rdesc:
            parts.append(rdesc)
            parts.append("")
    return parts


def _render_member_exceptions(
    mraw: dict[str, Any],
    uid_targets: dict[str, LinkTarget],
) -> list[str]:
    """Render member exceptions list."""
    parts = []
    exc = mraw.get("exceptions") or []
    if exc:
        parts.append("#### Exceptions")
        parts.append("")
        for e in exc:
            et = rewrite_xrefs(as_text(e.get("type")), uid_targets)
            ed = rewrite_xrefs(as_text(e.get("description")), uid_targets)
            if et and ed:
                parts.append(f"- {et} — {ed}")
            elif et:
                parts.append(f"- {et}")
        parts.append("")
    return parts


def _render_uid_list(
    title: str,
    uids: list[str],
    uid_targets: dict[str, LinkTarget],
    *,
    bulleted: bool = False,
) -> list[str]:
    """Render a list of UIDs as links or backticks."""
    if not uids:
        return []

    parts = [f"## {title}"]
    links = []
    for uid in uids:
        t = uid_targets.get(uid)
        if t:
            link = f"[{t.title}]({t.page_path})"
        else:
            name = uid.split(".")[-1]
            link = f"`{name}`"

        if bulleted:
            parts.append(f"- {link}")
        else:
            links.append(link)

    if not bulleted:
        parts.append(", ".join(links))

    parts.append("")
    return parts


def _render_type_implements(
    item: ItemInfo,
    uid_targets: dict[str, LinkTarget],
) -> list[str]:
    """Render implements list."""
    return _render_uid_list("Implements", item.raw.get("implements") or [], uid_targets)


def _render_type_derived(
    item: ItemInfo,
    uid_targets: dict[str, LinkTarget],
) -> list[str]:
    """Render derived classes list."""
    return _render_uid_list(
        "Derived", item.raw.get("derivedClasses") or [], uid_targets
    )


def _render_type_extension_methods(
    item: ItemInfo,
    uid_targets: dict[str, LinkTarget],
) -> list[str]:
    """Render extension methods list."""
    return _render_uid_list(
        "Extension Methods",
        item.raw.get("extensionMethods") or [],
        uid_targets,
        bulleted=True,
    )


def _render_member(
    m: ItemInfo,
    uid_targets: dict[str, LinkTarget],
) -> list[str]:
    """Render a single member section."""
    parts = [f"### {m.name}", ""]
    mraw = m.raw
    msyn = mraw.get("syntax") or {}
    msig = as_text(msyn.get("content"))
    if msig:
        parts.append(md_codeblock("csharp", msig))
        parts.append("")

    msumm = rewrite_xrefs(as_text(mraw.get("summary")), uid_targets)
    if msumm:
        parts.append(msumm)
        parts.append("")

    parts.extend(_render_member_params(msyn, uid_targets))
    parts.extend(_render_member_returns(m, msyn, uid_targets))
    parts.extend(_render_member_exceptions(mraw, uid_targets))

    return parts


def _render_type_members(
    item: ItemInfo,
    uid_to_item: dict[str, ItemInfo],
    uid_targets: dict[str, LinkTarget],
) -> list[str]:
    """Render type members grouped by kind."""
    members = [
        m
        for m in uid_to_item.values()
        if m.parent == item.uid and is_member_kind(m.kind)
    ]
    if not members:
        return []

    def member_key(m: ItemInfo) -> tuple[str, str]:
        order = {
            "constructor": "0",
            "field": "1",
            "property": "2",
            "method": "3",
            "event": "4",
            "operator": "5",
        }
        k = m.kind.lower()
        return (order.get(k, "9"), m.name.lower())

    parts = []
    members_sorted = sorted(members, key=member_key)
    current_group: str | None = None
    group_plural_map = {
        "Constructor": "Constructors",
        "Field": "Fields",
        "Property": "Properties",
        "Method": "Methods",
        "Event": "Events",
        "Operator": "Operators",
    }

    for m in members_sorted:
        group = m.kind.capitalize()
        group = group_plural_map.get(group, group)
        if group != current_group:
            parts += [f"## {group}", ""]
            current_group = group
        parts.extend(_render_member(m, uid_targets))

    return parts


def _render_type_seealso(
    item: ItemInfo,
    uid_targets: dict[str, LinkTarget],
) -> list[str]:
    """Render see also section."""
    parts = []
    raw = item.raw
    seealso = raw.get("seealso") or raw.get("seeAlso") or []
    if seealso:
        parts += ["## See also"]
        for s in seealso:
            suid = s.get("uid") if isinstance(s, dict) else None
            if suid and str(suid) in uid_targets:
                t = uid_targets[str(suid)]
                parts.append(f"- [{t.title}]({t.page_path})")
            else:
                parts.append(f"- {rewrite_xrefs(as_text(s), uid_targets)}")
        parts.append("")
    return parts
