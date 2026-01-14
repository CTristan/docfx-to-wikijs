# Plan: Refine Global Namespace Clustering for Human Navigability

## Objective

Implement refined post-clustering normalization heuristics to eliminate numeric taxonomies, suppress singleton folders, cap top-level directory sprawl, and reroute orphaned items based on semantic concepts.

## Guiding Principles

- **Determinism:** Every step must have a clear tie-breaker and fixed evaluation order.
- **Concept-First:** Prioritize semantic grouping over alphabetical indexing.
- **Stability:** Respect the `global_namespace_map.json` cache and minimize link churn.

---

## Phase 1: Tokenizer & Sanitizer Refinement

_Goal: Fix "Numeric Taxonomy Crimes" at the source._

- [ ] **Task 1.1: Tokenizer Digit Gluing**
  - Update `Tokenizer.tokenize()` regex to:
    - Glue leading digits to the following word (e.g., `2dxFX` → `["2DxFX"]`).
    - Glue trailing digits to the previous word (e.g., `Blue1` → `["Blue1"]`, `Version2` → `["Version2"]`).
  - **Invariant:** All-caps runs of length ≥ 2 remain all-caps tokens (e.g., `HTTPRequest` → `["HTTP", "Request"]`).
  - **Test:** Verify:
    - `2DVector` → `["2D", "Vector"]`
    - `Blue1` → `["Blue1"]`
    - `XML2Json` → `["XML2", "Json"]`
    - `Version2` → `["Version2"]`
    - `2dxFX` → `["2DxFX"]`
    - `X2Y` → `["X2Y"]`
    - `A1B2C` → `["A1B2C"]`
    - `V2` → `["V2"]`

---

## Phase 2: Normalization Infrastructure

_Goal: Prepare the data structures for the post-pass._

- [ ] **Task 2.1: NormalizationRoot Class**
  - Track: `normalized_name` (canonical casing, pre-sanitization), `sanitized_name`, `token_boundaries` (set of offsets), `source_cluster_key`, and member `items`.
- [ ] **Task 2.2: Token Boundary Projection**
  - Implement char-level mapping: `normalized` → `sanitized`.
  - Removed characters skip indices; preserved characters advance both.
  - Compute `boundaries` as between-character offsets (0..len).
    - **Definition:** Boundaries always include 0 and `len(sanitized_name)`.
  - Implement the **Projection Escape Hatch**: Fall back to token-list boundary detection if projection fails.
    - **Fail-Closed Rule:** Escape hatch only allowed if all items in a root share the same root-token list; otherwise, boundaries are "unknown."

---

## Phase 3: The Normalization Pass

_Goal: Implement the core Concept Preservation logic._

- [ ] **Task 3.1: Step 1 - Micro-Variant Merging**
  - **Union-Find:** Implement with representative rule: `(is_pinned DESC, name ASC)`.
    - **Pinned Policy:** Pinned roots may absorb non-pinned roots only; pinned↔pinned merges are disallowed.
    - **Winner Precedence:** If exactly one root is pinned, it must be the union representative. If both are pinned, the lexicographically smaller pinned root wins.
    - **Surviving Name:** Minimum of member roots under ordering `(is_pinned DESC, root ASC)`.
  - **Scope Token Derivation:** `scope_token = first token of the root's cluster-key token list`. (Treat empty list as a unique scope).
  - **Pair Generation:** Group by `normalized_name[:5]` within each `scope_token`.
  - **Coordinate System Alignment:**
    - Compute `common_prefix_len_norm` on normalized strings.
    - Project that length into sanitized-space to get `common_prefix_len_san(root)`.
      - **Rule:** `common_prefix_len_san(root)` = number of sanitized chars whose source normalized index < `common_prefix_len_norm`.
  - **False Friends Guard:** Implement the Boolean test using `common_prefix_len_san` ∈ `boundaries` and similarity ratio (≥ 0.7).
    - **Fail-Closed Consequence:** If boundaries are unknown for both roots, the guard may pass ONLY via similarity ratio (≥ 0.7).
  - **Utility Guard:** Compute `cap_pressure` once at the start of merging.
    - **Pool Definition:** `candidate_pool = (size ≥ min_cluster_size) ∪ (pinned with size ≥ 1)`.
    - **Pressure Rule:** `cap_pressure = len(candidate_pool) > max_top_level_folders`.
    - Apply refined guard (size < 20 OR prefix ≥ 7) under pressure.
  - **Evaluation Order:** Sort pairs by `(scope_token ASC, common_prefix_len_norm DESC, merged_size DESC, winner ASC, loser ASC)`.
    - **`merged_size`**: `size(root_a) + size(root_b)` using **pre-merge** sizes (computed once).
    - **Optimization:** Skip any pair whose roots are already in the same union-find set.
- [ ] **Task 3.2: Step 2 - Kept Set Selection**
  - Define `Final Kept Set = pinned_roots_kept ∪ top_k(high_density_clusters)`.
    - **Determinism:** `top_k` uses sort key `(size DESC, root ASC)`.
    - **Cap Input Rule:** Top-level cap is evaluated on post-merge roots that meet high-density criteria; pinned roots are appended afterward.
    - **Pinned Policy:** Pinned roots are added back and do not count against the cap.
    - **Zero-Item Guard:** If a pinned root has 0 items, it is not created.
  - Apply `pinned_allow_singleton` check (default: false) and `min_cluster_size` (default: 3).
- [ ] **Task 3.3: Step 3 - Rerouting**
  - **Stability Check:** If `reroute_bias == stability` and cached root is in `Kept Clusters`, use it and skip evaluation.
  - **Candidate Mapping:** Pass original candidate signals through `find()`.
  - **Reroute Precedence:** Metadata Hub → Priority Suffix → Strong Suffix → Strong Prefix → Keyword.
    - **Tie-Breaker:** If multiple candidates exist at a tier, choose lexicographically smallest.
  - **No Synthesis:** Candidates must be exactly one of the item's originally computed roots.
  - **Exclusion:** Never reroute to `Misc` (only final sink).
- [ ] **Task 3.4: Step 4 - Density Safety Valve**
  - Implement single-level split using deterministic recipe:
    - **Trigger:** `cluster_size > max_folder_size` (default 250).
    - **Method:** Choose next token (prefix) or suffix token from item's token list.
    - **Fallback:** If split key missing, stop-token, or > 50 subfolders, fall back to first-letter bucketing.
      - **Letter Bucket Rule:** First-letter buckets use A–Z; non-letters go to `_`.
    - **Strictness:** Strictly one level deep, no recursion.
  - Ensure stop-token check uses global list.

---

## Phase 4: Integration & Observability

_Goal: Wire up the pass and report success metrics._

- [ ] **Task 4.1: GlobalPathResolver Update**
  - Inject normalization pass between initial clustering and final path assignment.
  - Apply union-find normalization immediately after merging so all downstream steps use canonical IDs.
- [ ] **Task 4.2: Success Metrics & Reporting**
  - Add to `ClusterReport`:
    - `singleton_rate`, `top_level_count`, `misc_share` (≤ 15%).
    - `nav_friction` (median ≥ 5), `fragmentation` (folders < 3 ≤ 15%).
    - `reroute_share`: `(final top-level != initial root) / total unmapped items` (≤ 25%).
    - `root_churn` (≤ 1%), `capacity_constraint_ok = max(final_folder_size) <= max_folder_size`.

---

## Phase 5: Verification

- [ ] **Task 5.1: Regression Testing**
  - Run against Lobotomy Corp data and verify `2/` and `1/` folders are gone.
- [ ] **Task 5.2: Invariant Testing**
  - Verify no pinned root becomes a non-representative.
  - Verify no pinned↔pinned unions.
- [ ] **Task 5.3: Deterministic Verification (Golden Corpus)**
  - Create a fixture dataset (50-200 representative names + small map).
  - Verify byte-for-byte identical output twice.
  - Verify `Root Churn` is 0% on consecutive runs without rebuild.
