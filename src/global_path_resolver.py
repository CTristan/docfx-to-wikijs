"""Logic for resolving global namespace items into clustered file paths."""

import hashlib
from pathlib import Path
from typing import Any

from src.analyzer import Analyzer
from src.global_namespace_map import GlobalNamespaceMap
from src.item_info import ItemInfo
from src.normalization_pass import NormalizationPass
from src.resolution_result import ResolutionResult


class GlobalPathResolver:
    """Resolves UIDs to target file paths based on naming patterns and hierarchy."""

    def __init__(
        self, analyzer: Analyzer, global_map: GlobalNamespaceMap, config: dict[str, Any]
    ) -> None:
        """Initialize the resolver with analyzer, cache map, and configuration."""
        self.analyzer = analyzer
        self.global_map = global_map
        self.config = config
        self.sanitizer = analyzer.sanitizer
        self.metadata_index = analyzer.metadata_index

        # State
        self.assigned_paths: dict[str, str] = {}  # uid -> path
        self.path_registry: dict[str, str] = {}  # lower_canonical_path -> uid
        self.folders: set[str] = set()  # lower_canonical_folder_path

        # Helper caches
        min_size = config["thresholds"]["min_cluster_size"]
        self.top_prefixes = set(
            analyzer.get_top_prefixes(
                k=config["thresholds"]["top_k"], min_size=min_size
            )
        )
        self.strong_suffixes = analyzer.get_strong_suffixes(min_size=min_size)

        self.priority_suffixes = set(config["rules"]["priority_suffixes"])
        self.keyword_clusters = config["rules"].get("keyword_clusters", {})
        self.metadata_denylist = set(config["rules"].get("metadata_denylist", []))
        self.hub_types = config.get("hub_types", {})
        self.acronyms = set(config.get("acronyms", []))

    def resolve_all(self, items: list[ItemInfo]) -> dict[str, ResolutionResult]:
        """Resolve all items at once, applying normalization pass."""
        # 1. Initial clustering
        items_by_uid = {it.uid: it for it in items}
        initial_assignments, original_signals, cached_results = (
            self._apply_initial_clustering(items)
        )

        # 2. Normalization Pass
        norm_pass = NormalizationPass(
            self.config, self.sanitizer, self.analyzer.tokenizer
        )
        to_normalize = initial_assignments  # Only contains items needing normalization

        final_keys = norm_pass.run(to_normalize, items_by_uid, original_signals)

        # 3. Finalize
        return self._finalize_results(
            final_keys,
            items_by_uid,
            original_signals,
            initial_assignments,
            cached_results,
        )

    def _apply_initial_clustering(
        self, items: list[ItemInfo]
    ) -> tuple[
        dict[str, tuple[str, str]],
        dict[str, list[tuple[str, str, float]]],
        dict[str, ResolutionResult],
    ]:
        """Run initial rule application and separate cached items."""
        initial_assignments: dict[str, tuple[str, str]] = {}
        original_signals: dict[str, list[tuple[str, str, float]]] = {}
        cached_results: dict[str, ResolutionResult] = {}

        for item in items:
            # 1.1 Cache Check
            if not self.config.get("force_rebuild", False):
                cached_path = self.global_map.lookup(item.uid)
                if cached_path:
                    cached_root = ""
                    parts = cached_path.split("/")
                    if len(parts) > 1:
                        cached_root = parts[1]

                    cached_results[item.uid] = self._finalize_resolution(
                        item.uid, cached_path, ("cache", 1.0, "cache"), [], cached_root
                    )
                    continue

            # 1.2 Overrides
            overrides = self.config.get("path_overrides", {})
            if item.uid in overrides:
                cached_results[item.uid] = self._finalize_resolution(
                    item.uid,
                    overrides[item.uid],
                    ("override_uid", 1.0, "override"),
                    [],
                    "",
                )
                continue
            if item.full_name in overrides:
                cached_results[item.uid] = self._finalize_resolution(
                    item.uid,
                    overrides[item.full_name],
                    ("override_name", 1.0, "override"),
                    [],
                    "",
                )
                continue

            # 1.3 Apply Rules
            candidates = self._apply_rules(item)
            original_signals[item.uid] = candidates

            if not candidates:
                initial_assignments[item.uid] = ("misc", "Misc")
            else:
                winning = candidates[0]
                initial_assignments[item.uid] = (winning[0], winning[1])

        return initial_assignments, original_signals, cached_results

    def _finalize_results(
        self,
        final_keys: dict[str, str],
        items_by_uid: dict[str, ItemInfo],
        original_signals: dict[str, list[tuple[str, str, float]]],
        initial_assignments: dict[str, tuple[str, str]],
        cached_results: dict[str, ResolutionResult],
    ) -> dict[str, ResolutionResult]:
        """Combine cached results with normalized results."""
        results = cached_results.copy()

        for uid, cluster_key in final_keys.items():
            item = items_by_uid[uid]
            rule_id = "normalized"
            score = 0.5

            # Find the original rule that matched this cluster_key if possible
            for r_id, k, s in original_signals.get(uid, []):
                if k == cluster_key:
                    rule_id = r_id
                    score = s
                    break

            # Construct Path
            safe_name = self.sanitizer.normalize(item.name)
            path = f"Global/{cluster_key}/{safe_name}.md"

            # Initial root for metrics
            _initial_rule_id, initial_cluster_key = initial_assignments[uid]

            results[uid] = self._finalize_resolution(
                uid, path, (rule_id, score, cluster_key), [], initial_cluster_key
            )

        return results

    def resolve(self, item: ItemInfo) -> ResolutionResult:
        """Resolve a single item. (Legacy compatibility, use resolve_all)."""
        return self.resolve_all([item])[item.uid]

    def _apply_rules(self, item: ItemInfo) -> list[tuple[str, str, float]]:
        """Return list of (rule_id, cluster_key, score) in precedence order."""
        candidates = []

        tokens = self.analyzer.tokenizer.tokenize(item.name)
        if not tokens:
            return []

        norm_tokens = [self.sanitizer.normalize(t) for t in tokens]

        # Rule 3: Metadata Hub (Score 0.95)
        hub_cand = self._check_metadata_hub(item)
        if hub_cand:
            candidates.append(hub_cand)

        # Rule 4: Priority Suffixes (Score 0.9)
        if norm_tokens:
            last = norm_tokens[-1]
            if last in self.priority_suffixes:
                candidates.append(("priority_suffix", last, 0.9))

        # Rule 5: Strong Prefix (Score 0.8)
        if norm_tokens:
            first = norm_tokens[0]
            if first in self.top_prefixes:
                candidates.append(("strong_prefix", first, 0.8))

        # Rule 6: Strong Suffix (Score 0.7)
        if norm_tokens:
            last = norm_tokens[-1]
            if last in self.strong_suffixes:
                candidates.append(("strong_suffix", last, 0.7))

        # Rule 7: Keyword/Contains (Score 0.6)
        self._apply_keyword_rules(norm_tokens, candidates)

        # Rule 8: Type Families (Score 0.5)
        self._apply_family_rules(norm_tokens, candidates)

        return candidates

    def _apply_keyword_rules(
        self, norm_tokens: list[str], candidates: list[tuple[str, str, float]]
    ) -> None:
        """Apply keyword-based clustering rules."""
        for bucket, keywords in self.keyword_clusters.items():
            for kw in keywords:
                kw_norm = self.sanitizer.normalize(kw)
                if kw_norm in norm_tokens:
                    candidates.append(("keyword", bucket, 0.6))
                    break

    def _apply_family_rules(
        self, norm_tokens: list[str], candidates: list[tuple[str, str, float]]
    ) -> None:
        """Apply type family rules based on shared prefixes."""
        min_family_len = 4
        min_family_count = self.config["thresholds"].get("min_family_size", 3)
        if norm_tokens:
            first = norm_tokens[0]
            if len(first) >= min_family_len:
                count = self.analyzer.prefix_counts.get(first, 0)
                if count >= min_family_count:
                    candidates.append(("type_family", first, 0.5))

    def _check_metadata_hub(self, item: ItemInfo) -> tuple[str, str, float] | None:
        """Check if item belongs to a metadata hub (base class or interface)."""
        base_uid = self.metadata_index.get_base_class(item.uid)

        hub_candidates = []
        if base_uid and self._is_valid_hub(base_uid):
            hub_candidates.append(base_uid)

        # If no valid base, check interfaces
        if not hub_candidates:
            interfaces = self.metadata_index.get_interfaces(item.uid)
            valid_interfaces = [i for i in interfaces if self._is_valid_hub(i)]
            if valid_interfaces:
                valid_interfaces.sort()
                hub_candidates.append(valid_interfaces[0])

        if hub_candidates:
            hub = hub_candidates[0]
            hub_name = self._get_hub_name(hub)
            return ("metadata_hub", hub_name, 0.95)

        return None

    def _is_valid_hub(self, uid: str) -> bool:
        """Verify if a type UID is a valid candidate for a metadata hub."""
        name = uid.split(".")[-1]
        if name in self.metadata_denylist or uid in self.metadata_denylist:
            return False

        min_hub_len = 4
        if len(name) < min_hub_len:
            return False

        return not name.endswith("Base")

    def _get_hub_name(self, uid: str) -> str:
        """Get the display name for a metadata hub."""
        if uid in self.hub_types:
            return self.hub_types[uid]

        name = uid.split(".")[-1]
        return self.sanitizer.normalize(name)

    def _finalize_resolution(
        self,
        uid: str,
        path: str,
        result_info: tuple[str, float, str],
        runner_ups: list[dict] | None = None,
        initial_root: str = "",
    ) -> ResolutionResult:
        """Finalize the resolution result and update registries."""
        rule, score, cluster_key = result_info
        if runner_ups is None:
            runner_ups = []
        final_path = self._resolve_collisions(uid, path)

        # Register
        self.assigned_paths[uid] = final_path
        self.global_map.update(uid, final_path)
        lower_path = self._to_canonical_path(final_path)
        self.path_registry[lower_path] = uid

        # Register folders
        p = Path(final_path)
        for parent in p.parents:
            if parent == Path():
                continue
            self.folders.add(self._to_canonical_path(str(parent)))

        return ResolutionResult(
            uid, final_path, rule, score, cluster_key, runner_ups, initial_root
        )

    def _resolve_collisions(self, uid: str, desired_path: str) -> str:
        """Resolve path collisions between files and folders."""
        base_no_ext = str(Path(desired_path).with_suffix(""))
        lower_base = self._to_canonical_path(base_no_ext)

        if lower_base in self.folders:
            desired_path = f"{base_no_ext}_Page.md"
            base_no_ext = str(Path(desired_path).with_suffix(""))
            lower_base = self._to_canonical_path(base_no_ext)

        p = Path(desired_path)
        for parent in p.parents:
            if parent == Path():
                continue
            parent_str = str(parent)
            file_key = self._to_canonical_path(f"{parent_str}.md")
            if file_key in self.path_registry:
                existing_uid = self.path_registry[file_key]
                new_existing_path = f"{parent_str}_Page.md"
                del self.path_registry[file_key]
                self.assigned_paths[existing_uid] = new_existing_path
                self.path_registry[self._to_canonical_path(new_existing_path)] = (
                    existing_uid
                )

        lower_path = self._to_canonical_path(desired_path)
        while lower_path in self.path_registry:
            h = hashlib.sha256(uid.encode("utf-8")).hexdigest()[:4]
            pp = Path(desired_path)
            desired_path = f"{pp.parent}/{pp.stem}_{h}{pp.suffix}"
            lower_path = self._to_canonical_path(desired_path)

        return desired_path

    def _to_canonical_path(self, path: str) -> str:
        """Normalize a path for comparison."""
        return path.lower().replace("\\", "/")
