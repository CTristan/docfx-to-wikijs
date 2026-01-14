# Research: Refining Global Namespace Clustering for Human Navigability

## Objective

Refine the existing Global Namespace clustering algorithm (implemented in `src/global_path_resolver.py` and friends) to prioritize **human readability** and **navigability** over pure algorithmic correctness. The current implementation produces too many fragmented folders and undesirable numeric taxonomies.

## Implementation Architecture

To ensure stability and predictability, all refinement rules (suppression, merging, caps) are applied as **post-clustering normalization steps**.

### 1. Initial Clustering

Assign items to clusters based on the existing precedence chain (Explicit Overrides → Metadata Hub → Priority Suffix → Strong Prefix → Strong Suffix → Keyword → Type Family → Fallback).

### 2. Normalization Pass (Concept Preservation)

1.  **Merge Micro-Variants:** Combine related small clusters to increase density.
    - **String Strategy:** All prefix-length comparisons and bucketing for merging use the **normalized root string** (canonical casing applied, pre-sanitization). Sanitization is applied only for folder naming and token-boundary indexing.
    - **Heuristic:** Merge two roots if they share a common prefix of **≥ 5 characters** in their normalized root strings.
    - **Candidate Scope:** Only consider merges among roots that share the same first tokenizer token. The scope token is derived from the root’s cluster-key tokenization, not from the sanitized string.
    - **Optimized Pair Generation:** Within each scope_token, group roots by their first 5 characters of the normalized root string and only compare pairs within the same group to maintain performance.
    - **Common Prefix (Normalized):** Longest shared prefix of the normalized root string (case-sensitive), measured in characters.
      - Let `common_prefix_len_norm` be this length.
      - Because token-boundary indices live in the **sanitized** root string, compute a per-root mapped length `common_prefix_len_san(root)` by projecting the first `common_prefix_len_norm` characters of the normalized root through the same normalized→sanitized char map used for boundary projection (removed characters do not advance the sanitized index).
      - Use `common_prefix_len_san(a)` when testing `boundaries(a)` and `common_prefix_len_san(b)` when testing `boundaries(b)`.
    - **"False Friends" Guard:** To avoid merging unrelated roots, the guard passes if `common_prefix_len_san(a)` ∈ `boundaries(a)` OR `common_prefix_len_san(b)` ∈ `boundaries(b)` OR the similarity ratio `common_prefix_len_norm / min(len(norm_a), len(norm_b))` is **≥ 0.7**.
      - **Token Boundary:** A set of **between-character offsets** in the sanitized root string (0..len). Offset `k` means the boundary occurs **between** `sanitized[k-1]` and `sanitized[k]` (with `k=0` meaning "before the first character" and `k=len` meaning "after the last character"). Each root tracks `token_boundaries` computed before sanitization and projected onto the sanitized string.
      - **Projection Method:** Building a char-level mapping from the canonical-cased, pre-sanitized root to the sanitized root; removed characters are skipped, preserved characters advance both indices.
      - **Projection Escape Hatch:** If char-level projection fails, fall back to token-list boundary detection. Use the item token list **only when the root token list is identical for all items in the root**; otherwise treat boundary as unknown (fail closed; boundary checks may not be used and only the similarity-ratio path can pass).
      - **Fail-Closed Consequence:** If boundaries are unknown, the False-Friends guard can only pass via the similarity ratio path.
    - **Merge Winner:** Choose the **lexicographically smaller root** as the surviving root name.
      - **Pinned Winner Precedence:** If one root is pinned and the other is not, the **pinned root must win**. If both are pinned, the lexicographically smaller pinned root wins.
      - **Stable Union-Find Representative:** The surviving root name for a union (representative) is the minimum of member roots under ordering: `(is_pinned DESC, root ASC)`.
    - **Merge Evaluation Order:** Consider candidate pairs in deterministic order: `(scope_token ASC, common_prefix_len DESC, merged_size DESC, winner_root ASC, loser_root ASC)`; apply merges using **union-find**.
      - **`merged_size`**: Computed as `size(root_a) + size(root_b)` using **pre-merge cluster sizes** (computed once before any merges).
      - **Optimization:** Skip any pair whose roots are already in the same union-find set.
    - **ID Normalization:** Apply union-find normalization **immediately after merging** so all downstream steps operate on canonical root IDs.
    - **Anchor Policy:** Pinned roots may be merge targets but are **never merged away** (they cannot be a merge source). **Pinned↔pinned merges are disallowed.**
    - **Utility Guard:** Only merge if the smaller root is below `min_cluster_size` OR the merge reduces top-level root count under **Cap Pressure**.
      - **Cap Pressure:** `cap_pressure = (num_candidate_roots_after_density_and_pins > max_top_level_folders)`.
      - **Timing:** Cap pressure is computed **once**, at the start of the merge phase.
      - **Candidate Pool (Cap Pressure):** `(roots with size ≥ min_cluster_size) ∪ (pinned roots with size ≥ 1)`.
      - **Kept Candidate (merge phase):** A root in the candidate pool above (i.e., `size ≥ min_cluster_size` OR `is_pinned && size ≥ 1`).
      - **Refined Utility Guard:** Under cap pressure, only allow merges if both roots are below a "large cluster" threshold (e.g., 20 members) OR if `common_prefix_len` ≥ 7.
    - **Constraint:** Only merge if the combined size meets `min_cluster_size` OR if the larger cluster is already a **Kept Candidate (merge phase)**.
2.  **Determine "Kept" Clusters:**
    - **Final Kept Set = pinned_roots_kept ∪ top_k(high_density_clusters)**, where `high_density_clusters` excludes pinned roots.
    - **Kept Clusters** refers strictly to **top-level roots** under `Global/` (excluding `Misc/`).
    - **Pinned Roots:** Manually configured folders (e.g., `Worker`, `Script`, `UI`) that are preserved as navigational anchors.
      - **Density Policy:** Pinned roots still respect `min_cluster_size` unless explicitly configured with `pinned_allow_singleton: true` (default: `false`).
      - If a pinned root has 0 items in a run, it is not created.
    - **High-Density Clusters:** Clusters with size ≥ `min_cluster_size` (default: 3).
    - **Top-K Selection:** If total top-level folders exceed `max_top_level_folders` (default: 40), keep only the top K by size.
      - **Sort Key:** Sort candidates by `(size DESC, root ASC)` to ensure determinism.
      - **Hub Interaction:** Pinned Roots are added back after this ranking and do not count against the cap.
3.  **Reroute & Suppress:**
    - Items in suppressed or overflow clusters are **rerouted** to the best matching **Kept Cluster** using the original precedence signals.
    - **Stability Mode:** In stability mode, if an item's cached path top-level root is still in Kept Clusters, **skip reroute evaluation entirely**.
    - **Reroute targets are top-level kept roots only**; density-safety-valve subfolders are applied **after** reroute.
    - **Reroute Exclusion:** Fallback/Misc is never considered a reroute candidate; it is only used as a final sink.
    - **Candidate Canonicalization:** Before testing a candidate root against the Kept Cluster set, map it through the merge union-find representative (`candidate = find(candidate)`).
    - **Signal Locking:** Candidate roots are derived from the item’s **pre-normalization** cluster signals, then tested against the **post-normalization** Kept Cluster set.
    - **Deterministic Candidates:** Each item produces at most one candidate per tier; tiers that generate multiple candidates must select deterministically (lexicographically).
      - **Metadata Hub Tier:** If multiple interfaces are candidates, pick the lexicographically smallest eligible hub root.
      - **Keyword Tier:** If multiple keyword buckets match, pick the lexicographically smallest bucket name.
    - **No Synthesis:** Reroute candidates must be exactly one of the item’s originally computed candidate roots; do not synthesize new candidate roots during reroute.
    - **Reroute Precedence:** Metadata Hub → Priority Suffix → Strong Suffix → Strong Prefix → Keyword. (Note: Type Family is not used for rerouting).
    - **Reroute Tie-Breaker:** Choose the first matching Kept Cluster in the reroute precedence order; if multiple match at the same tier, pick the lexicographically first root.
    - Items that cannot be rerouted to a Kept Cluster are sent to the final fallback: `Global/Misc/`.
4.  **Density Safety Valve:**
    - If a kept cluster exceeds `max_folder_size` (default: 250), allow a single-level split using the following deterministic recipe:
      - Choose the **next token** after the root token (for prefix clusters) or the **suffix token** (for suffix clusters).
      - **Split Token Source:** The split token must be computed from the item’s **token list**, not from substrings of the name.
      - **Selection Tie-Breaker:** If multiple split keys are available, always choose the first eligible key in tokenizer order.
      - **Subfolder Measurement:** Subfolder count is computed as the number of **distinct split keys actually observed** among items in the cluster.
      - **Fallback:** If the chosen split token is missing, is a stop-token, or would create > 50 subfolders, fall back immediately to **first-letter bucketing**.
      - **Stop-token check** uses the same global `stop_tokens` list as tokenizer filtering.
      - Apply standard folder sanitization/casing.
      - **Strictly one level deep** (no recursion).

## Findings & Issues

### 1. Numeric Taxonomy "Crimes"

- **Issue:** The tokenizer currently splits leading numbers into their own tokens.
- **Solution:**
  - **Leading Digits:** Treat leading digit runs as part of the token if followed by letters.
  - **Trailing Digits:** Treat trailing numeric tokens as suffixes glued to the previous token.
- **Examples:**
  - `2DVector` → `["2D", "Vector"]` (not `["2", "D", "Vector"]`)
  - `Blue1` → `["Blue1"]` (not `["Blue", "1"]`)
  - `Version2` → `["Version2"]` (always glued)
- **Goal:** Eliminate pure numeric top-level folders.

### 2. Concept-First Fallback (The "Reroute" Strategy)

- **Issue:** ~40% of generated directories contain only a single file. Exiling them to a massive "Misc" bucket loses semantic context.
- **Solution:** Instead of a generic index, absorb "dust bunnies" into their nearest meaningful district.
- **Heuristic:** If a cluster root (e.g., `Sakura`) is suppressed, check if its items match a _kept_ root (e.g., `Tree` or `Plant`) via metadata or other lexical rules.
- **Final Catch-all:** `Global/Misc/` is the only "I give up" bucket.

### 3. Top-Level Directory Sprawl

- **Definition:** **Top-level folder count** = number of immediate children under `Global/` excluding `Misc/`.
- **Constraint:** `max_top_level_folders` (default: 40).

### 4. Preservation of Semantic "Hubs"

- **Terminology:** **Hubs** are semantic categories discovered via rules (e.g., Metadata Hub). **Pinned Roots** are explicit configuration entries.
- **Policy:**
  - Pinned Roots are navigational anchors and follow the density policy defined in Step 2 above.
  - Unpinned Hubs are treated like any other cluster for `min_cluster_size` and `max_top_level_folders` enforcement.

### 5. Micro-Variant Merging

- **Definition:** **Root** = The sanitized folder name produced by the cluster key.
- This step runs **before** reroute/suppression to save viable clusters.

## Configuration

- `overflow_strategy`: `reroute_to_best_kept` (default) | `misc_only`.
- `reroute_bias`: `stability` (default) | `semantic`. In stability mode, if an item's cached path is a valid Kept Cluster, it is used even if a better semantic match exists.
- `pinned_roots`: List of cluster roots to always preserve (if not empty).
- `min_family_size`: Threshold for the Type Family rule (default: 3) to prevent micro-fragmentation.
- `max_folder_size`: Threshold for triggering the density safety valve (default: 250).

## Stability & Link Integrity

- **Non-Negotiable:** These refinements must **NOT** move items already mapped in `global_namespace_map.json` unless the `--force-rebuild` flag is used.
- If items move, redirect stubs must be generated.

## Success Metrics

- **Singleton Rate:** < 10–15% of folders have only 1 file.
- **Top-Level Count:** < 40 folders (excluding `Misc/`).
- **Misc Share:** `Global/Misc/` contains ≤ 15% of total Global namespace pages.
- **Navigational Friction:** Median files per top-level folder ≥ 5.
- **Fragmentation Control:** % of top-level folders with < 3 items ≤ 15%.
- **Reroute Share:** ≤ 25% of items rerouted from their initial cluster. Measured only for items NOT already mapped in `global_namespace_map.json` or during `--force-rebuild` runs.
- **No Numeric Roots:** Zero top-level folders named `0-9`.
- **Click Depth:** 95% of pages reachable within ≤ 2 folder levels under `Global/`.
- **Density Control:** 95th percentile files per folder < 100.
- **Capacity Constraint:** Largest folder size ≤ `max_folder_size` after safety valve.
- **Churn Rate:** ~0% of items move without `--force-rebuild`.
- **Root Churn:** % of roots created/removed per run (without `--force-rebuild`) ≤ 1%.
