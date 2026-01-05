"""Convert DocFX YAML metadata to Wiki.js compatible Markdown.

This module processes DocFX ManagedReference YAML files and generates a static site
structure suitable for Wiki.js, including type pages, namespace indexes, and a
home page.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from collections.abc import Iterable

# -----------------------------
# Utilities
# -----------------------------

YAML_MIME_PREFIX = "### YamlMime:"
XREF_TAG_RE = re.compile(r"<xref:([^?>#>]+)(?:\?[^>#>]*)?(?:#[^>]*)?>")
XREF_MD_LINK_RE = re.compile(
    r"\((xref:([^)?#]+)(?:\?[^)#]*)?(?:#[^)]+)?)\)",
)  # (xref:UID?...)

# Conservative: keep letters, digits, underscore, dash. Dots are replaced with hyphens.
DOT_SAFE_RE = re.compile(r"[^A-Za-z0-9_-]+")


def strip_yaml_mime_header(text: str) -> str:
    """Remove the DocFX YAML MIME header from the content."""
    lines = text.splitlines()
    if lines and lines[0].startswith(YAML_MIME_PREFIX):
        return "\n".join(lines[1:]).lstrip("\n")
    return text


def as_text(v: object) -> str:
    """Convert a value to a string, handling lists and None."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        return "\n".join(as_text(x) for x in v if as_text(x))
    return str(v).strip()


def dot_safe(name: str) -> str:
    """Make a stable filename-ish token.

    Replaces dots with hyphens for Wiki.js compatibility. Also normalize nested types
    and generics markers.
    """
    name = name.replace("+", "-")  # nested types Outer+Inner -> Outer-Inner
    name = name.replace("`", "")  # generics Foo`1 -> Foo1-ish
    name = name.replace(".", "-")  # dots -> hyphens for Wiki.js compatibility
    name = DOT_SAFE_RE.sub("-", name).strip("-")
    # Avoid pathological emptiness
    return name or "Unknown"


def header_slug(s: str) -> str:
    """Generate a GitHub-ish anchor slug: lower, hyphenate non-alnum."""
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "section"


def md_codeblock(lang: str, code: str) -> str:
    """Generate a Markdown code block."""
    return f"```{lang}\n{code.rstrip()}\n```"


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    """Generate a Markdown table."""
    if not rows:
        return ""
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    out.extend("| " + " | ".join(r) + " |" for r in rows)
    return "\n".join(out)


# -----------------------------
# Data model
# -----------------------------


@dataclass
class ItemInfo:
    """Represents a documented item (class, method, etc.)."""

    uid: str
    kind: str  # Namespace/Class/Method/Property/etc.
    name: str
    full_name: str
    parent: str | None
    namespace: str | None
    summary: str
    file: Path
    raw: dict[str, Any]  # original parsed item


@dataclass(frozen=True)
class LinkTarget:
    """Represents a link target for an XRef."""

    title: str
    page_path: str  # Wiki path, e.g. /api/Foo.Bar


# -----------------------------
# Parsing and indexing
# -----------------------------


def load_managed_reference(path: Path) -> dict[str, Any]:
    """Load and parse a DocFX ManagedReference YAML file."""
    raw = strip_yaml_mime_header(path.read_text(encoding="utf-8"))
    # Fix unquoted equals sign in VB names which confuses PyYAML
    # Matches: "  name.vb: =" -> "  name.vb: '='
    raw = re.sub(r"^(\s*[\w\.]+\.vb:\s+)(=$)", r"\1'='", raw, flags=re.MULTILINE)
    doc = yaml.safe_load(raw)
    return doc or {}


def iter_main_items(doc: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """Iterate over the main items in a DocFX YAML document."""
    items = doc.get("items") or []
    for it in items:
        if isinstance(it, dict) and it.get("uid"):
            yield it


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
            uid_to_item[uid] = ItemInfo(
                uid=uid,
                kind=kind,
                name=str(name),
                full_name=str(full_name),
                parent=str(parent) if parent else None,
                namespace=str(ns) if ns else None,
                summary=summary,
                file=f,
                raw=it,
            )
        for ref in doc.get("references") or []:
            if isinstance(ref, dict) and ref.get("uid"):
                uid_to_ref[str(ref["uid"])] = ref
    return uid_to_item, uid_to_ref


def namespace_of(item: ItemInfo) -> str:
    """Determine the namespace of an item."""
    # Prefer explicit namespace field.
    if item.namespace:
        return item.namespace
    # Try derive from full_name if it looks dotted.
    parts = item.full_name.split(".")
    if len(parts) > 1:
        return ".".join(parts[:-1])
    return ""


def is_type_kind(kind: str) -> bool:
    """Check if the kind represents a type (class, struct, etc.)."""
    k = kind.lower()
    return k in {"class", "struct", "interface", "enum", "delegate"}


def is_namespace_kind(kind: str) -> bool:
    """Check if the kind represents a namespace."""
    return kind.lower() == "namespace"


def is_member_kind(kind: str) -> bool:
    """Check if the kind represents a member (method, property, etc.)."""
    k = kind.lower()
    return k in {"method", "property", "field", "event", "operator", "constructor"}


def page_path_for_fullname(api_root: str, full_name: str) -> str:
    """Generate the Wiki.js page path for a given full name."""
    # Flattened hyphenated filenames: Foo.Bar.Baz -> /api/Foo-Bar-Baz
    return f"{api_root}/{dot_safe(full_name)}"


def output_file_for_page(out_root: Path, page_path: str) -> Path:
    """Determine the output file path for a given Wiki.js page path."""
    # /api/Foo.Bar -> out_root/api/Foo.Bar.md
    rel = page_path.lstrip("/") + ".md"
    p = out_root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# -----------------------------
# XRef rewriting
# -----------------------------


def build_link_targets(
    uid_to_item: dict[str, ItemInfo],
    uid_to_ref: dict[str, dict[str, Any]],
    api_root: str,
) -> dict[str, LinkTarget]:
    """Build a map of UIDs to link targets."""
    targets: dict[str, LinkTarget] = {}

    # 1. Internal types and namespaces (pages)
    for uid, item in uid_to_item.items():
        if is_namespace_kind(item.kind) or is_type_kind(item.kind):
            page = page_path_for_fullname(api_root, item.full_name)
            title = item.name or item.full_name or uid
            targets[uid] = LinkTarget(title=title, page_path=page)

    # 2. Members (anchors on internal pages)
    for uid, item in uid_to_item.items():
        if is_member_kind(item.kind) and item.parent:
            parent_target = targets.get(item.parent)
            if parent_target:
                anchor = header_slug(item.name or item.full_name)
                page_with_anchor = f"{parent_target.page_path}#{anchor}"
                title = item.name or item.full_name or uid
                targets[uid] = LinkTarget(title=title, page_path=page_with_anchor)

    # 3. References (external or internal)
    for uid, ref in uid_to_ref.items():
        if uid in targets:
            continue
        href = ref.get("href")
        title = ref.get("name") or ref.get("fullName") or uid
        if href:
            targets[uid] = LinkTarget(title=str(title), page_path=str(href))
        else:
            targets[uid] = LinkTarget(title=str(title), page_path="#")

    return targets


def rewrite_xrefs(text: str, uid_targets: dict[str, LinkTarget]) -> str:
    """Rewrite DocFX XRef tags to Markdown links."""
    if not text:
        return ""

    # <xref:UID> -> [Title](/api/...)
    def repl_tag(m: re.Match) -> str:
        uid = m.group(1)
        t = uid_targets.get(uid)
        if not t:
            return f"`{uid}`"
        return f"[{t.title}]({t.page_path})"

    text = XREF_TAG_RE.sub(repl_tag, text)

    # (xref:UID) -> (/api/...)
    def repl_link(m: re.Match) -> str:
        uid = m.group(2)
        t = uid_targets.get(uid)
        if not t:
            return "(#)"
        return f"({t.page_path})"

    return XREF_MD_LINK_RE.sub(repl_link, text)


# -----------------------------
# Rendering: Namespace pages
# -----------------------------


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
                page = page_path_for_fullname(api_root, t.full_name)
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


# -----------------------------
# Rendering: Type pages (DocFX-ish)
# -----------------------------


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


def render_type_page(
    item: ItemInfo,
    uid_to_item: dict[str, ItemInfo],
    uid_targets: dict[str, LinkTarget],
    *,
    include_member_details: bool = True,
) -> str:
    """Render a type page (class, struct, etc.) in Markdown."""
    raw = item.raw
    kind_label = item.kind.capitalize()
    parts: list[str] = [f"# {kind_label} {item.name}", ""]

    parts.extend(_render_type_metadata(item, uid_targets))
    parts.extend(_render_type_attributes(item, uid_targets))

    # Summary
    summary = rewrite_xrefs(as_text(raw.get("summary")), uid_targets)
    if summary:
        parts += [summary, ""]

    # Definition
    syntax = raw.get("syntax") or {}
    sig = as_text(syntax.get("content"))
    if sig:
        parts += [md_codeblock("csharp", sig), ""]

    parts.extend(_render_type_inheritance(item, uid_targets))
    parts.extend(_render_type_inherited_members(item, uid_targets))

    # Remarks / Examples
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

    return "\n".join(parts).rstrip() + "\n"


# -----------------------------
# Main
# -----------------------------


def _build_ns_graph(ns_to_types: dict[str, list[ItemInfo]]) -> dict[str, set[str]]:
    """Build a mapping of namespace to its child namespaces."""
    ns_children: dict[str, set[str]] = {}
    all_namespaces = set(ns_to_types.keys())
    for ns in list(all_namespaces):
        if not ns:
            continue
        parts = ns.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[:i])
            child = ".".join(parts[: i + 1])
            ns_children.setdefault(parent, set()).add(child)
        # Ensure top-level exists
        ns_children.setdefault(parts[0], ns_children.get(parts[0], set()))
    return ns_children


def _write_type_pages(
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
        page_path = page_path_for_fullname(args.api_root, it.full_name)
        md = render_type_page(
            it,
            uid_to_item=uid_to_item,
            uid_targets=uid_targets,
            include_member_details=args.include_member_details,
        )
        out_file = output_file_for_page(out_root, page_path)
        out_file.write_text(md, encoding="utf-8")
        written += 1
        if written % 50 == 0:
            print(f"  ... wrote {written}/{total_types} types")
    return written


def run_conversion(args: argparse.Namespace) -> int:
    """Execute the conversion logic."""
    yml_files = sorted(args.yml_dir.rglob("*.yml"))
    if not yml_files:
        msg = f"No .yml files found under: {args.yml_dir}"
        raise SystemExit(msg)

    uid_to_item, uid_to_ref = build_index(yml_files)
    uid_targets = build_link_targets(uid_to_item, uid_to_ref, args.api_root)

    out_root = args.out_dir.resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    # Collect types by namespace for optional namespace pages
    ns_to_types: dict[str, list[ItemInfo]] = {}
    for it in uid_to_item.values():
        if is_type_kind(it.kind):
            ns = namespace_of(it)
            ns_to_types.setdefault(ns, []).append(it)

    ns_children = _build_ns_graph(ns_to_types)
    written = _write_type_pages(uid_to_item, uid_targets, args, out_root)

    # Namespace pages (optional)
    if args.include_namespace_pages:
        for ns, types in sorted(ns_to_types.items(), key=lambda kv: kv[0].lower()):
            if not ns:
                continue
            page_path = page_path_for_fullname(args.api_root, ns)
            children = sorted(ns_children.get(ns, set()))
            md = render_namespace_page(
                ns_fullname=ns,
                types_in_ns=types,
                child_namespaces=children,
                uid_targets=uid_targets,
                api_root=args.api_root,
            )
            out_file = output_file_for_page(out_root, page_path)
            out_file.write_text(md, encoding="utf-8")
            written += 1

    # Home page (optional)
    if args.home_page:
        home = [
            "# Home",
            "",
            (
                "This wiki was initially generated from DocFX metadata and is now "
                "editable."
            ),
            "",
            f"- Browse the API under `{args.api_root}`",
            "",
        ]
        (out_root / "home.md").write_text("\n".join(home), encoding="utf-8")

    print(f"Generated {written} Markdown pages into: {out_root}")
    return 0


def main() -> int:
    """Run the conversion process."""
    ap = argparse.ArgumentParser(
        description=(
            "Convert DocFX ManagedReference YAML to Wiki.js Markdown (DocFX-ish "
            "layout)."
        ),
    )
    ap.add_argument(
        "yml_dir",
        type=Path,
        help="Directory containing DocFX *.yml (ManagedReference) files",
    )
    ap.add_argument(
        "out_dir",
        type=Path,
        help="Output directory (a git repo root for Wiki.js Git storage)",
    )
    ap.add_argument(
        "--api-root",
        default="/api",
        help="Wiki path root for generated pages (default: /api)",
    )
    ap.add_argument(
        "--include-namespace-pages",
        action="store_true",
        help="Generate foo.md, foo.bar.md namespace landing pages",
    )
    ap.add_argument(
        "--include-member-details",
        action="store_true",
        help="Inline member sections (constructors/methods/etc.) on type pages",
    )
    ap.add_argument(
        "--home-page",
        action="store_true",
        help="Generate a simple Home page (home.md)",
    )
    args = ap.parse_args()
    return run_conversion(args)


if __name__ == "__main__":
    raise SystemExit(main())
