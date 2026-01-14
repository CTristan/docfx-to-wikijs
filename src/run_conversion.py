"""Orchestration logic for converting DocFX YAML to Wiki.js Markdown."""

import argparse
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.analyzer import Analyzer
from src.build_index import build_index
from src.build_link_targets import build_link_targets
from src.build_ns_graph import build_ns_graph
from src.cluster_report import ClusterReport
from src.compute_config_hash import compute_config_hash
from src.global_namespace_map import CURRENT_SCHEMA_VERSION, GlobalNamespaceMap
from src.global_path_resolver import GlobalPathResolver
from src.is_type_kind import is_type_kind
from src.load_config import load_config
from src.metadata_index import MetadataIndex
from src.namespace_of import namespace_of
from src.output_file_for_page import output_file_for_page
from src.page_path_for_fullname import page_path_for_fullname
from src.render_namespace_page import render_namespace_page
from src.sanitizer import Sanitizer
from src.should_use_global_dir import should_use_global_dir
from src.stub_generator import StubGenerator
from src.tokenizer import Tokenizer
from src.write_type_pages import write_type_pages

if TYPE_CHECKING:
    from src.item_info import ItemInfo
    from src.resolution_result import ResolutionResult


def run_conversion(args: argparse.Namespace) -> int:
    """Execute the full conversion pipeline."""
    yml_files = sorted(args.yml_dir.rglob("*.yml"))
    if not yml_files:
        msg = f"No .yml files found under: {args.yml_dir}"
        raise SystemExit(msg)

    config, global_map = _init_infra(args)
    uid_to_item, uid_to_ref = build_index(yml_files)

    analyzer = _analyze_metadata(uid_to_item, config)
    global_resolved = _resolve_global_paths(
        uid_to_item, analyzer, global_map, config, args
    )

    uid_targets = build_link_targets(
        uid_to_item, uid_to_ref, args.api_root, global_resolved
    )

    if args.dry_run:
        return 0

    threshold = (
        config["thresholds"].get("stale_prune_after_runs", 0) if args.prune_stale else 0
    )
    global_map.save(prune_stale_threshold=threshold)

    out_root = args.out_dir.resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    written = _render_all_pages(uid_to_item, uid_targets, out_root, args)

    if args.home_page:
        _write_home_page(out_root, args.api_root)

    print(f"Generated {written} Markdown pages into: {out_root}")
    return 0


def _init_infra(args: argparse.Namespace) -> tuple[dict[str, Any], GlobalNamespaceMap]:
    """Initialize configuration and the persistent global namespace map."""
    config = load_config(args.config)
    if args.force_rebuild:
        config["force_rebuild"] = True

    config_hash = compute_config_hash(config)
    map_path = args.out_dir / "global_namespace_map.json"
    global_map = GlobalNamespaceMap(str(map_path), config_hash)
    global_map.load(accept_legacy=args.accept_legacy_cache)

    return config, global_map


def _analyze_metadata(
    uid_to_item: dict[str, "ItemInfo"], config: dict[str, Any]
) -> Analyzer:
    """Run frequency analysis on the metadata items."""
    tokenizer = Tokenizer(config.get("acronyms"))
    sanitizer = Sanitizer(config.get("acronyms"))
    metadata_index = MetadataIndex(uid_to_item)
    analyzer = Analyzer(tokenizer, sanitizer, metadata_index, config)
    analyzer.analyze(list(uid_to_item.values()))
    return analyzer


def _resolve_global_paths(
    uid_to_item: dict[str, "ItemInfo"],
    analyzer: Analyzer,
    global_map: GlobalNamespaceMap,
    config: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, "ResolutionResult"]:
    """Resolve target paths for items in the global namespace."""
    resolver = GlobalPathResolver(analyzer, global_map, config)
    report = ClusterReport(compute_config_hash(config), CURRENT_SCHEMA_VERSION)
    global_resolved: dict[str, ResolutionResult] = {}

    stub_root = args.out_dir / args.api_root.lstrip("/")
    stub_gen = StubGenerator(str(stub_root))

    for uid, item in uid_to_item.items():
        if is_type_kind(item.kind) and should_use_global_dir(item.namespace):
            old_path = global_map.lookup(uid)
            res = resolver.resolve(item)
            global_resolved[uid] = res
            report.add_result(res)

            if not args.dry_run and old_path and old_path != res.final_path:
                stub_gen.generate_stub(old_path, res.final_path, uid)

    if args.dry_run:
        report.generate_report("cluster_report.json")
        print("Dry run complete. Report generated at cluster_report.json")

    return global_resolved


def _render_all_pages(
    uid_to_item: dict[str, "ItemInfo"],
    uid_targets: dict[str, Any],
    out_root: Path,
    args: argparse.Namespace,
) -> int:
    """Render all type and namespace pages to disk."""
    ns_to_types: dict[str, list[ItemInfo]] = {}
    for it in uid_to_item.values():
        if is_type_kind(it.kind):
            ns = namespace_of(it)
            ns_to_types.setdefault(ns, []).append(it)

    ns_children = build_ns_graph(ns_to_types)
    written = write_type_pages(uid_to_item, uid_targets, args, out_root)

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

    return written


def _write_home_page(out_root: Path, api_root: str) -> None:
    """Generate a simple home page for the Wiki."""
    home = [
        "# Home",
        "",
        ("This wiki was initially generated from DocFX metadata and is now editable."),
        "",
        f"- Browse the API under `{api_root}`",
        "",
    ]
    (out_root / "home.md").write_text("\n".join(home), encoding="utf-8")
