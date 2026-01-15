"""Logic for the concept-first normalization pass of global namespace clustering."""

from typing import TYPE_CHECKING, Any

from src.canonicalize_root_name import canonicalize_root_name
from src.item_info import ItemInfo
from src.normalization_root import NormalizationRoot

if TYPE_CHECKING:
    from src.sanitizer import Sanitizer
    from src.tokenizer import Tokenizer

MIN_PREFIX_LEN = 5
SIMILARITY_THRESHOLD = 0.7
HIGH_CONFIDENCE_PREFIX_LEN = 7
SMALL_CLUSTER_SIZE = 20
MAX_SUBFOLDER_TOKENS = 50


class NormalizationPass:
    """Orchestrates merging, rerouting, and capping of cluster roots."""

    def __init__(
        self, config: dict[str, Any], sanitizer: "Sanitizer", tokenizer: "Tokenizer"
    ) -> None:
        """Initialize normalization pass."""
        self.config = config
        self.sanitizer = sanitizer
        self.tokenizer = tokenizer
        self.min_cluster_size = config["thresholds"]["min_cluster_size"]
        self.max_top_level = config["thresholds"].get("max_top_level_folders", 40)
        self.pinned_roots = set(config["rules"].get("pinned_roots", []))
        self.pinned_allow_singleton = config["rules"].get(
            "pinned_allow_singleton", False
        )

        # State
        self.roots: dict[str, NormalizationRoot] = {}  # canonical_root_name -> root
        self.union_find: dict[str, str] = {}  # root_name -> parent_name
        self.root_sizes: dict[str, int] = {}  # pre-merge sizes

    def run(
        self,
        initial_assignments: dict[str, tuple[str, str]],
        items_by_uid: dict[str, ItemInfo],
        original_signals: dict[str, list[tuple[str, str, float]]],
    ) -> dict[str, str]:
        """Execute the normalization pass.

        initial_assignments: uid -> (rule_id, cluster_key)
        items_by_uid: uid -> ItemInfo
        original_signals: uid -> list of (rule_id, cluster_key, score)
        returns: uid -> final_cluster_key
        """
        # 1. Group items into initial NormalizationRoots
        self._initialize_roots(initial_assignments, items_by_uid)

        # 2. Step 1: Micro-Variant Merging
        self._merge_micro_variants()

        # 3. ID Normalization
        # Apply union-find normalization immediately after merging
        final_assignments = self._apply_merges(initial_assignments)

        # 4. Step 2: Determine Kept Set
        kept_roots = self._determine_kept_set()

        # 5. Step 3: Rerouting
        final_assignments = self._reroute_orphans(
            final_assignments, kept_roots, original_signals
        )

        # 6. Step 4: Density Safety Valve
        return self._apply_safety_valve(final_assignments, items_by_uid)

    def _initialize_roots(
        self,
        initial_assignments: dict[str, tuple[str, str]],
        items_by_uid: dict[str, ItemInfo],
    ) -> None:
        """Create initial roots and compute metadata."""
        roots_by_name: dict[str, NormalizationRoot] = {}

        for uid, (_rule_id, cluster_key) in initial_assignments.items():
            item = items_by_uid[uid]
            # Use canonical casing for root names
            tokens = self.tokenizer.tokenize(cluster_key)
            norm_name = canonicalize_root_name(tokens)

            if norm_name not in roots_by_name:
                roots_by_name[norm_name] = NormalizationRoot(
                    normalized_name=norm_name, source_cluster_key=cluster_key, items=[]
                )
                # Scope token for optimization
                if tokens:
                    roots_by_name[norm_name].scope_token = tokens[0]
                else:
                    roots_by_name[norm_name].scope_token = ""

            roots_by_name[norm_name].items.append(item)

        for root in roots_by_name.values():
            root.compute_metadata(self.sanitizer, self.tokenizer)
            self.roots[root.normalized_name] = root
            self.union_find[root.normalized_name] = root.normalized_name
            self.root_sizes[root.normalized_name] = len(root.items)

    def _merge_micro_variants(self) -> None:
        """Step 1: Merge similar small clusters."""
        # 1. Pre-calculate cap pressure
        cap_pressure = self._check_cap_pressure()

        # 2. Generate candidate pairs
        pairs = self._generate_candidate_pairs()

        # 3. Sort pairs deterministically
        pairs.sort(
            key=lambda p: (
                p["scope_token"],
                -p["prefix_len"],
                -p["merged_size"],
                p["winner"],
                p["loser"],
            )
        )

        # 4. Apply merges
        self._execute_merges(pairs, cap_pressure=cap_pressure)

    def _check_cap_pressure(self) -> bool:
        """Check if we are exceeding the max top level folders limit."""
        candidate_pool = []
        for name, root in self.roots.items():
            if len(root.items) >= self.min_cluster_size or (
                name in self.pinned_roots and len(root.items) >= 1
            ):
                candidate_pool.append(name)

        return len(candidate_pool) > self.max_top_level

    def _generate_candidate_pairs(self) -> list[dict[str, Any]]:
        """Generate all valid candidate pairs for merging."""
        # Group by (scope_token, prefix5)
        buckets: dict[tuple[str, str], list[str]] = {}
        for name in self.roots:
            scope = self.roots[name].scope_token
            # Prefix5 on normalized_name
            prefix5 = name[:5]
            key = (scope, prefix5)
            if key not in buckets:
                buckets[key] = []
            buckets[key].append(name)

        pairs = []
        for key, root_list in buckets.items():
            # Stable sort within bucket
            root_list.sort()
            for i in range(len(root_list)):
                for j in range(i + 1, len(root_list)):
                    root_a = root_list[i]
                    root_b = root_list[j]

                    pair_data = self._score_pair(root_a, root_b, key[0])
                    if pair_data:
                        pairs.append(pair_data)
        return pairs

    def _score_pair(
        self, root_a: str, root_b: str, scope_token: str
    ) -> dict[str, Any] | None:
        """Evaluate a pair of roots and return their score data if valid."""
        # Disallow pinned-pinned merges
        if root_a in self.pinned_roots and root_b in self.pinned_roots:
            return None

        # Calculate common prefix (normalized)
        prefix_len = 0
        for c1, c2 in zip(root_a, root_b, strict=False):
            if c1 == c2:
                prefix_len += 1
            else:
                break

        if prefix_len < MIN_PREFIX_LEN:
            return None

        # Score the pair
        # merged_size using pre-merge sizes
        merged_size = self.root_sizes[root_a] + self.root_sizes[root_b]

        # winner/loser for sort key
        # (representative logic handles actual union winner)
        w, loser = (root_a, root_b) if root_a < root_b else (root_b, root_a)

        return {
            "scope_token": scope_token,
            "prefix_len": prefix_len,
            "merged_size": merged_size,
            "root_a": root_a,
            "root_b": root_b,
            "winner": w,
            "loser": loser,
        }

    def _execute_merges(
        self, pairs: list[dict[str, Any]], *, cap_pressure: bool
    ) -> None:
        """Apply valid merges from the sorted pair list."""
        for p in pairs:
            name_a = p["root_a"]
            name_b = p["root_b"]

            # Skip if already merged
            if self._find(name_a) == self._find(name_b):
                continue

            # False Friends Guard
            if not self._check_false_friends(
                self.roots[name_a], self.roots[name_b], p["prefix_len"]
            ):
                continue

            # Utility Guard
            if not self._check_utility(
                self.roots[name_a],
                self.roots[name_b],
                p["prefix_len"],
                cap_pressure=cap_pressure,
            ):
                continue

            # Final constraint: density or kept candidate
            if self._should_merge_density(name_a, name_b):
                self._union(name_a, name_b)

    def _should_merge_density(self, name_a: str, name_b: str) -> bool:
        """Check if merge creates a dense cluster or involves a kept candidate."""
        is_kept_a = (
            self.root_sizes[name_a] >= self.min_cluster_size
            or name_a in self.pinned_roots
        )
        is_kept_b = (
            self.root_sizes[name_b] >= self.min_cluster_size
            or name_b in self.pinned_roots
        )

        return (
            self.root_sizes[name_a] + self.root_sizes[name_b] >= self.min_cluster_size
            or is_kept_a
            or is_kept_b
        )

    def _check_false_friends(
        self, root_a: NormalizationRoot, root_b: NormalizationRoot, prefix_len_norm: int
    ) -> bool:
        """Verify if merge is safe based on token boundaries and similarity."""
        # Project prefix length into sanitized space
        prefix_len_san_a = self._project_length(root_a, prefix_len_norm)
        prefix_len_san_b = self._project_length(root_b, prefix_len_norm)

        # Guard passes if ends at boundary
        has_boundary = False
        if (
            not root_a.boundaries_unknown
            and prefix_len_san_a in root_a.token_boundaries
        ):
            has_boundary = True
        if (
            not root_b.boundaries_unknown
            and prefix_len_san_b in root_b.token_boundaries
        ):
            has_boundary = True

        # Or if similarity is high
        ratio = prefix_len_norm / min(
            len(root_a.normalized_name), len(root_b.normalized_name)
        )

        if root_a.boundaries_unknown and root_b.boundaries_unknown:
            # Similarity only path: require prefix >= 7
            return (
                ratio >= SIMILARITY_THRESHOLD
                and prefix_len_norm >= HIGH_CONFIDENCE_PREFIX_LEN
            )

        if has_boundary:
            return True

        return ratio >= SIMILARITY_THRESHOLD

    def _project_length(self, root: NormalizationRoot, length_norm: int) -> int:
        """Count sanitized chars whose source normalized index < length_norm."""
        # Simple implementation: build the char mapping
        s_idx = 0
        mapping: list[int | None] = []
        for _n_idx, n_char in enumerate(root.normalized_name):
            if (
                s_idx < len(root.sanitized_name)
                and n_char.lower() == root.sanitized_name[s_idx].lower()
            ):
                mapping.append(s_idx)
                s_idx += 1
            else:
                mapping.append(None)

        # Count sanitized chars mapped from norm indices < length_norm
        count = 0
        for i in range(min(length_norm, len(mapping))):
            if mapping[i] is not None:
                count += 1
        return count

    def _check_utility(
        self,
        root_a: NormalizationRoot,
        root_b: NormalizationRoot,
        prefix_len: int,
        *,
        cap_pressure: bool,
    ) -> bool:
        """Check if merge improves navigability or addresses cap pressure."""
        # Permit if both small
        if (
            self.root_sizes[root_a.normalized_name] < SMALL_CLUSTER_SIZE
            and self.root_sizes[root_b.normalized_name] < SMALL_CLUSTER_SIZE
        ):
            return True

        # Permit if high prefix similarity
        if prefix_len >= HIGH_CONFIDENCE_PREFIX_LEN:
            return True

        # Under cap pressure, permit more merges
        if cap_pressure:
            return False  # Strictly follow "both roots < 20 unless prefix >= 7"

        return False

    def _apply_merges(
        self, initial_assignments: dict[str, tuple[str, str]]
    ) -> dict[str, str]:
        """Map all items to their merged representative roots."""
        results = {}
        for uid, (_rule_id, cluster_key) in initial_assignments.items():
            tokens = self.tokenizer.tokenize(cluster_key)
            norm_name = canonicalize_root_name(tokens)
            rep = self._find(norm_name)
            results[uid] = rep
        return results

    def _determine_kept_set(self) -> set[str]:
        """Step 2: Decide which folders survive."""
        # 1. Update root sizes after union-find normalization
        final_root_counts: dict[str, int] = {}
        for name, size in self.root_sizes.items():
            rep = self._find(name)
            final_root_counts[rep] = final_root_counts.get(rep, 0) + size

        # 2. Identify high-density candidates (excluding pinned)
        candidates = []
        for name, count in final_root_counts.items():
            if name in self.pinned_roots:
                continue
            if count >= self.min_cluster_size:
                candidates.append((count, name))

        # 3. Sort deterministically: (size DESC, root ASC)
        candidates.sort(key=lambda x: (-x[0], x[1]))

        # 4. Top-K selection
        kept_non_pinned = {name for size, name in candidates[: self.max_top_level]}

        # 5. Add back pinned roots if they have items
        kept_pinned = set()
        for name in self.pinned_roots:
            if (
                name in final_root_counts
                and final_root_counts[name] > 0
                and (
                    final_root_counts[name] >= self.min_cluster_size
                    or self.pinned_allow_singleton
                )
            ):
                kept_pinned.add(name)

        return kept_non_pinned | kept_pinned

    def _reroute_orphans(
        self,
        assignments: dict[str, str],
        kept_roots: set[str],
        original_signals: dict[str, list[tuple[str, str, float]]],
    ) -> dict[str, str]:
        """Step 3: Move items from suppressed folders to kept folders."""
        final_assignments = {}
        for uid, current_root in assignments.items():
            # If already in a kept root, stay there
            if current_root in kept_roots:
                final_assignments[uid] = current_root
                continue

            # Orphan! Try to reroute
            signals = original_signals.get(uid, [])

            # Map candidates through find() and filter by kept_roots
            candidates_by_tier: dict[str, list[str]] = {
                "metadata_hub": [],
                "priority_suffix": [],
                "strong_suffix": [],
                "strong_prefix": [],
                "keyword": [],
            }

            for rule_id, cluster_key, _score in signals:
                if rule_id not in candidates_by_tier:
                    continue

                # Canonicalize
                tokens = self.tokenizer.tokenize(cluster_key)
                norm_name = canonicalize_root_name(tokens)

                if norm_name not in self.union_find:
                    continue

                rep = self._find(norm_name)

                if rep in kept_roots and rep not in candidates_by_tier[rule_id]:
                    candidates_by_tier[rule_id].append(rep)

            # Select best candidate by precedence
            best_rep = None
            precedence = [
                "metadata_hub",
                "priority_suffix",
                "strong_suffix",
                "strong_prefix",
                "keyword",
            ]
            for tier in precedence:
                tier_cands = candidates_by_tier[tier]
                if tier_cands:
                    # Tier Tie-Breaker: lexicographically smallest
                    tier_cands.sort()
                    best_rep = tier_cands[0]
                    break

            if best_rep:
                final_assignments[uid] = best_rep
            else:
                # Explicit fallback: If we had signals but they all pointed to dropped
                # roots, we default to Misc. This is intended behavior to avoid
                # reviving small/noisy roots.
                final_assignments[uid] = "Misc"

        return final_assignments

    def _apply_safety_valve(
        self,
        assignments: dict[str, str],
        items_by_uid: dict[str, ItemInfo],
    ) -> dict[str, str]:
        """Step 4: Subdivide oversized folders."""
        max_folder_size = self.config.get("max_folder_size", 250)

        # 1. Count items per root
        root_counts: dict[str, int] = {}
        for root in assignments.values():
            root_counts[root] = root_counts.get(root, 0) + 1

        # 2. Identify oversized roots
        oversized = {
            root
            for root, count in root_counts.items()
            if count > max_folder_size and root != "Misc"
        }

        if not oversized:
            return assignments

        # 3. For each oversized root, pre-calculate split keys
        root_split_keys = self._calculate_split_keys(
            oversized, assignments, items_by_uid
        )

        final_assignments = {}
        for uid, root in assignments.items():
            if root not in oversized:
                final_assignments[uid] = root
                continue

            split_key = root_split_keys[root].get(uid)
            if split_key:
                final_assignments[uid] = f"{root}/{split_key}"
            else:
                final_assignments[uid] = f"{root}/_"

        return final_assignments

    def _calculate_split_keys(
        self,
        oversized: set[str],
        assignments: dict[str, str],
        items_by_uid: dict[str, ItemInfo],
    ) -> dict[str, dict[str, str]]:
        """Determine split strategies and keys for all oversized roots."""
        root_split_keys: dict[str, dict[str, str]] = {}

        for root in oversized:
            root_split_keys[root] = self._determine_split_strategy(
                root, assignments, items_by_uid
            )

        return root_split_keys

    def _determine_split_strategy(
        self,
        root: str,
        assignments: dict[str, str],
        items_by_uid: dict[str, ItemInfo],
    ) -> dict[str, str]:
        """Determine whether to split by token or letter for a specific root."""
        stop_tokens = set(self.config.get("stop_tokens", []))
        observed_tokens: set[str] = set()
        uid_to_token: dict[str, str] = {}

        # Pass 1: Try token strategy
        for uid, r in assignments.items():
            if r != root:
                continue

            item = items_by_uid[uid]
            tokens = self.tokenizer.tokenize(item.name)

            split_token = None
            for t in tokens:
                norm_t = self.sanitizer.normalize(t)
                if norm_t != root and norm_t.lower() not in stop_tokens:
                    split_token = norm_t
                    break

            if split_token:
                observed_tokens.add(split_token)
                uid_to_token[uid] = split_token

        # Decide strategy
        if observed_tokens and len(observed_tokens) <= MAX_SUBFOLDER_TOKENS:
            return uid_to_token

        # Fallback to letter
        uid_to_letter: dict[str, str] = {}
        for uid, r in assignments.items():
            if r != root:
                continue
            item = items_by_uid[uid]
            first_char = item.name[0].upper()
            if not ("A" <= first_char <= "Z"):
                first_char = "_"
            uid_to_letter[uid] = first_char
        return uid_to_letter

    def _find(self, name: str) -> str:
        """Union-find find with path compression."""
        if self.union_find[name] == name:
            return name
        self.union_find[name] = self._find(self.union_find[name])
        return self.union_find[name]

    def _union(self, name_a: str, name_b: str) -> None:
        """Union-find union with deterministic representative."""
        root_a = self._find(name_a)
        root_b = self._find(name_b)
        if root_a == root_b:
            return

        # Pinned roots win
        pinned_a = root_a in self.pinned_roots
        pinned_b = root_b in self.pinned_roots

        if pinned_a and pinned_b:
            # Pinned-pinned disallowed!
            return

        if pinned_a:
            self.union_find[root_b] = root_a
        elif pinned_b:
            self.union_find[root_a] = root_b
        # Lexicographical smaller wins
        elif root_a < root_b:
            self.union_find[root_b] = root_a
        else:
            self.union_find[root_a] = root_b
