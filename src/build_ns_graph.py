"""Logic for building a namespace hierarchy graph."""

from src.item_info import ItemInfo


def build_ns_graph(ns_to_types: dict[str, list[ItemInfo]]) -> dict[str, set[str]]:
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
        ns_children.setdefault(parts[0], ns_children.get(parts[0], set()))
    return ns_children
