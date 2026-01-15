"""Logic for rewriting DocFX cross-references to Wiki.js links."""

import re

from src.link_target import LinkTarget

XREF_TAG_RE = re.compile(r"<xref:([^?>#]+)(?:\?[^>#]*)?(?:#[^>]*)?>")
XREF_MD_LINK_RE = re.compile(
    r"\((xref:([^)?#]+)(?:\?[^)#]*)?(?:#[^)]+)?)\)",
)  # (xref:UID?...)


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
