# TODO: Refine Global Namespace Clustering for Human Navigability

## Phase 1: Tokenizer & Sanitizer Refinement `[core]`

- [x] **Task 1.1: Tokenizer Digit Gluing** `[core]`
  - [x] Update `Tokenizer.tokenize()` regex to glue leading digits to the following word.
  - [x] Update `Tokenizer.tokenize()` regex to glue trailing digits to the previous word.
  - [x] Define tokenization precedence for ACRONYM + digits + TitleCase (e.g., `HTTP2Server`, `XML2JSONParser`) and lock it with tests.
  - [x] **Algorithm Precedence:** Extract acronym runs (A–Z length ≥ 2) first; absorb trailing digits into the same token; split remaining TitleCase boundaries; then handle leading digit+letter combos as a single token if digits are immediately followed by letters.
  - [x] Ensure all-caps runs of length ≥ 2 remain atomic tokens (acronym invariant).
  - [x] **Test:** Create unit tests for:
    - Basic gluing: `2DVector` → `["2D", "Vector"]`, `Blue1` → `["Blue1"]`, `Version2` → `["Version2"]`.
    - Complex precedence: `HTTP2Server` → `["HTTP2", "Server"]`, `XML2JSONParser` → `["XML2", "JSON", "Parser"]`.
    - Short weird cases: `X2Y` → `["X2Y"]`, `A1B2C` → `["A1B2C"]`, `V2` → `["V2"]`. `[test]`

## Phase 2: Normalization Infrastructure `[core]`

- [x] **Task 2.1: NormalizationRoot Class** `[core]`
  - [x] Implement `NormalizationRoot` to track `normalized_name`, `sanitized_name`, `token_boundaries`, `source_cluster_key`, and member items.
- [x] **Task 2.2: Token Boundary Projection** `[core]`
  - [x] Implement character-level mapping from `normalized` to `sanitized` string.
  - [x] Implement `boundaries` calculation as between-character offsets (0..len).
  - [x] Ensure boundaries always include 0 and `len(sanitized_name)`.
  - [x] **Required Indices:** All boundary offsets from the root token list and `common_prefix_len_norm` values evaluated during pair scoring.
  - [x] Implement the **Projection Escape Hatch** with token-list boundary detection.
  - [x] Implement the **Fail-Closed Rule** for the escape hatch.
  - [x] **Failure Definition:** Projection fails if any required index is out of range, unmappable, or non-monotonic.
  - [x] **Test:** Verify boundary projection correctness with sanitization edge cases (e.g., removing spaces/underscores). `[test]`
- [x] **Task 2.3: Canonical Casing Logic** `[core]`
  - [x] Implement `canonicalize_root_name(tokens: list[str])` to produce `normalized_name`.
  - [x] **Policy:** Preserve acronyms (len ≥ 2), apply TitleCase to other tokens, join with empty string.
  - [x] **Test:** Verify `["XML", "Parser"]` → `XMLParser`, `["xml", "parser"]` → `XmlParser`, `["2D", "Vector"]` → `2DVector`. `[test]`

## Phase 3: The Normalization Pass `[core]`

- [x] **Task 3.1: Step 1 - Micro-Variant Merging** `[core]`
  - [x] Implement **Union-Find** with representative ordering `(is_pinned DESC, root ASC)`.
  - [x] Implement **Pinned Policy**: Disallow pinned↔pinned merges; pinned root always wins if exactly one is pinned.
  - [x] Implement **Scope Token Derivation** from cluster-key token list.
  - [x] Implement **Pair Generation** grouped by `normalized_name[:5]` within `scope_token`.
    - [x] **Short Roots:** Use full `normalized_name` if `len < 5` (no padding).
    - [x] **Stable List:** Sort roots by `root ASC` within each bucket before generating pairs.
  - [x] Implement **Coordinate System Alignment**: Project `common_prefix_len_norm` to `common_prefix_len_san`.
    - [x] **Invariant:** `common_prefix_len_san` must be monotonic in `common_prefix_len_norm` and ≤ `len(sanitized_name)`.
  - [x] Implement **False Friends Guard** using projection and similarity ratio (≥ 0.7).
    - [x] **Similarity Evidence:** If boundaries are unknown, require `common_prefix_len_norm ≥ 7` for similarity merges.
  - [x] Implement **Fail-Closed Consequence** for unknown boundaries.
  - [x] Implement **Utility Guard** with `cap_pressure` logic.
    - [x] Define candidate pool: `(size ≥ min_cluster_size) ∪ (pinned with size ≥ 1)`.
    - [x] Compute `cap_pressure` once at the start of the merge phase.
    - [x] **Refined Guard:** Under cap pressure, permit merge only if both roots have pre-merge `size < 20`, unless `common_prefix_len_norm ≥ 7`.
  - [x] Implement **Deterministic Evaluation Order** for pairs.
    - [x] **Sort Key:** `(scope_token ASC, common_prefix_len_norm DESC, merged_size DESC, winner ASC, loser ASC)`.
  - [x] Apply union-find normalization immediately after merging for canonical IDs.
- [x] **Task 3.2: Step 2 - Kept Set Selection** `[core]`
  - [x] Implement logic to determine the **Final Kept Set**.
  - [x] Ensure `top_k` uses deterministic sort key `(size DESC, root ASC)`.
  - [x] Apply **Cap Input Rule**: Evaluate cap on post-merge roots, then append pinned roots.
  - [x] Apply **Zero-Item Guard** for pinned roots.
  - [x] Implement `pinned_allow_singleton` and `min_cluster_size` checks.
- [x] **Task 3.3: Step 3 - Rerouting** `[core]`
  - [x] Implement **Stability Check** for `reroute_bias == stability`.
  - [x] Implement **Candidate Mapping** through union-find representative.
  - [x] Implement **Reroute Precedence** (Metadata → Priority Suffix → Strong Suffix → Strong Prefix → Keyword).
    - [x] **Exclude:** Type Family is not considered for rerouting.
  - [x] Implement **Tier Tie-Breaker** (lexicographically smallest).
  - [x] Enforce **No Synthesis** and **Exclusion of Misc** from reroute candidates.
- [x] **Task 3.4: Step 4 - Density Safety Valve** `[core]`
  - [x] Implement trigger check: `cluster_size > max_folder_size`.
  - [x] Implement split key selection (next token / suffix token from item's token list).
  - [x] Implement **Selection Tie-Breaker** (tokenizer order).
  - [x] Implement fallback to **First-letter bucketing** (ASCII A-Z or `_`).
  - [x] Ensure strictly one level deep (no recursion).

## Phase 4: Integration & Observability `[integration]`

- [x] **Task 4.1: GlobalPathResolver Update** `[core]`
  - [x] Inject the normalization pass into `GlobalPathResolver.resolve()`.
  - [x] **Stability Criteria:**
    - [x] Without `--force-rebuild`, if an item has a cached path and its top-level root is a Kept Cluster, final path must remain unchanged.
    - [x] **Move Definition:** A move is any change in the final output path string vs cached path string.
    - [x] Generate redirect stubs for any item moves (force-rebuild or unmapped).
    - [x] **Stub Target:** Redirect stub target must be the final canonical path (post-normalization).
- [x] **Task 4.2: Success Metrics & Reporting** `[integration]`
  - [x] Update `ClusterReport` to calculate all new metrics.
    - [x] **Initial Root Definition:** `initial_root` for `reroute_share` is the pre-normalization assigned root.
  - [x] Implement `capacity_constraint_ok` metric.
  - [x] **Root Churn:** `root_churn = (|roots_added| + |roots_removed|) / |roots_prev_run|` (unforced runs only, excluding `Misc`).
  - [x] **Observability:** Emit merge decision log in debug mode (candidate pair → guards result + failure reasons → applied?).
    - [x] **Failure Reason Codes:** Emit a stable list like `["pinned_pinned", "same_set", "below_min_prefix", "false_friends", "utility_guard", "constraint_min_cluster"]` so tuning is grep-friendly.
  - [x] **Diagnostics:** Include counts: `num_roots_pre_merge`, `num_roots_post_merge`, `num_items_rerouted`, `num_items_to_misc`, `num_merges_attempted`, `num_merges_applied`.

## Phase 5: Verification `[test]`

- [x] **Task 5.1: Regression Testing** `[test]`
  - [x] Run against Lobotomy Corp data; verify removal of `2/` and `1/` folders.
  - [x] Verify `Misc` share ≤ 15%.
- [x] **Task 5.2: Invariant Testing** `[test]`
  - [x] Verify pinned root representative invariants.
  - [x] Verify no pinned↔pinned unions occur.
- [x] **Task 5.3: Deterministic Verification (Golden Corpus)** `[test]`
  - [x] Create golden corpus fixture (50-200 names + map).
    - [x] **Edge Cases:** Include pinned-root merge candidates, unknown boundary cases, and sanitized character removal cases.
    - [x] **Tokenizer Cases:** Include representative edge inputs (digits + acronyms + casing).
  - [x] Verify byte-for-byte identical output on repeated runs.
  - [x] Verify 0% root churn on consecutive runs without force-rebuild.
