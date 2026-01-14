# Global Namespace Reorganization Research

## Objective

Determine rule-based heuristics to subdivide the massive `Global` namespace (currently ~1500+ files) into meaningful subdirectories to improve documentation navigability in a generic, assembly-agnostic way, while ensuring stability and minimizing link rot.

## Findings

### Current State

- The `Global` namespace contains a flat list of types.
- `src/docfx_yml_to_wikijs.py` currently places all items with `namespace: Global` (or no namespace) into `wikijs_out/api/Global/`.
- There are distinct clusters of files sharing common prefixes or functional themes, but these vary by project.

### Analysis of File Clusters (Lobotomy Corp Example)

Counts of key prefixes/themes in the current `api/` to be used as test cases for the dynamic algorithm:

- **Camera/Graphics**: ~300 files (`CameraFilterPack_*`, `Camera*`)
- **Story**: ~100 files (`Story*`)
- **UI**: ~75 files (`UI*` or ending in `*UI`)
- **Bosses**: ~73 files (Contains `Boss`)
- **Agents**: ~65 files (`Agent*`)
- **Sefira**: ~49 files (`Sefira*`)

## Dynamic Cluster Discovery

To ensure the tool remains generic and works with any assembly, we will implement a **Dynamic Cluster Discovery** phase that runs at the start of the conversion process.

### 1. Stability & Link Rot Prevention

Documentation paths must remain stable across runs to prevent broken links (link rot).

- **Persistent Mapping Cache:** The tool will generate and maintain a `global_namespace_map.json` file.
  - **Metadata:** Include `schema_version` and `config_hash` to track _why_ clustering decisions changed.
  - **Schema Versioning:** Bump `schema_version` when the mapping file format or interpretation changes; a bump invalidates old cache unless `--accept-legacy-cache` is provided.
  - **Legacy Migration:** When accepting a legacy cache, the tool will read legacy entries and rewrite them to the current schema on save.
  - **Hash Calculation:** The `config_hash` must be computed from a **canonical JSON serialization** (sorted keys) of the **final, merged configuration** (built-in defaults + user overrides) to prevent false positives from file reordering.
  - **Read:** On startup, load existing UID -> Path mappings.
  - **Write:** After processing, save new mappings.
  - **Policy:** If a UID exists in the cache, **use the cached path** (unless `--force-rebuild` is set). This locks "legacy" assignments while allowing new types to be clustered.
  - **Merge Semantics:** Defaults are deep-merged with user config; scalars override; arrays replace unless explicitly documented as additive (e.g., `acronyms` merges as a set).
- **Identity (UID):** The cache is keyed on the DocFX `uid`. If an item lacks a `uid` (rare):
  - A synthetic ID is derived from `fullName` + `kind` and marked as "weak identity."
  - **Kind Definition:** `kind` is the DocFX item type (e.g., `Class`, `Struct`, `Enum`, `Interface`, `Delegate`, `Namespace`).
  - **Collision:** If synthetic IDs collide, append short hash of the YAML source file path.
- **Redirect Stubs:** If a path _must_ change (e.g., during a forced rebuild), generate a small Markdown file at the old location linking to the new one.
  - **Stub Format:** Title, Canonical Link, and metadata (Old UID/fullName) for audit.
  - **Retention:** Keep stubs indefinitely to preserve external links.
  - **Filename Stability:** Stub filenames are never rewritten once created to prevent thrashing during rebuilds.
- **UID Stability & Collisions:**
  - **Deterministic Hashing:** Short hash = first 8 chars of SHA-1 over the UID (or over the canonical folder path string for folder collisions).
  - **Disappearing UIDs:** Keep mapping in cache but mark as stale. Cleanup only via explicit `--prune-stale` flag or after items have been missing for > N runs (defined by `stale_prune_after_runs` in config).
  - **Reappearing UIDs:** Prefer UID as canonical identity even if fullName changes.
  - **Collisions:**
    - **File vs File:** Append deterministic suffix (short hash of UID).
    - **Folder vs File:** Prefer **Folder**. Rename the colliding file to `{Name}_Page.md` (e.g., `Story` folder wins over `Story.md`).
    - **Collision Suffix Rules:** If `{Name}_Page.md` also exists, apply the standard file-vs-file collision suffix rule.
    - **Folder vs Folder:** If two clusters resolve to the same folder path (due to sanitization), keep the lexicographically first cluster (based on the canonical folder path string) as-is and suffix the other with a short hash of its **Cluster Key**.
    - **Cluster Key:** `(rule_id, value)` serialized as `{rule_id}:{normalized_value}` (e.g., `metadata_hub:CreatureBase`), where `normalized_value` uses the same sanitization and casing rules as folder names.
    - **Case-Insensitivity:** Normalize all paths to a **canonical form** to handle `UI` vs `Ui` collisions on case-insensitive filesystems (macOS/Windows).
    - **Canonical Form:** The canonical form is the sanitized, cased token output (acronyms preserved, else TitleCase). Comparisons for collision detection are performed on a lower-cased copy of this path.
    - **Canonical Folder Path String:** A path that is sanitized + cased + forward slashes (`/`) + no trailing slash. Used for hashing/sorting.

### 2. The Discovery Phase (Analysis)

Before generating any files, the script will analyze the set of all type names and their metadata in the `Global` namespace:

#### A. Metadata Extraction (Static Analysis)

Since the source is precompiled DLLs processed by DocFX, the generated YAMLs already contain static analysis data.

1.  **Inheritance Map:** Track base classes for every type.
2.  **Interface Map:** Track implemented interfaces.

#### B. Tokenization & Normalization

**Universal Rule:** All matching logic (Prefix, Suffix, Contains, Families) uses the **same tokenizer output**.

1.  **Strip Noise:** Remove generic arity (`Creature`1`) and nested type markers (`Outer+Inner`).
2.  **Acronym Handling:** Treat uppercase runs as single tokens (`UIManager` -> `['UI', 'Manager']`, `XMLParser` -> `['XML', 'Parser']`).
    - **Source:** Built-in defaults + Config overrides (case-insensitive).
3.  **Unity/Game Conventions:** Handle `2D`, `3D`, `Vector3` as atomic units, not `['Vector', '3']`.

#### C. Frequency Analysis & Stop-Tokens

1.  **Prefix Frequency Map:** Count occurrences of initial tokens **within the Global namespace only**.
2.  **Suffix Frequency Map:** Count occurrences of final tokens **within the Global namespace only**.
3.  **Base Class/Interface Frequency:** Count types sharing common base classes **within the Global namespace only**.
4.  **Stop-Token Suppression:** Ignore "boring" roots that recreate the global namespace problem.
    - **Ignore List:** `Manager`, `Controller`, `System`, `Data`, `Helper`, `Util`, `Base`, `Common`.
    - **Rule:** Stop-tokens still count toward frequency maps for analysis/reporting, but are filtered out when selecting clusters.
    - **Timing:** Stop-token check runs **after** sanitization/casing (e.g., `Base` and `base` are treated identically).
    - **Configurable:** This list will be in the configuration with defaults.

#### D. Thresholding & Fragmentation

- **Dynamic Threshold:** `min_cluster_size = max(10, ceil(total_global * 0.01))`.
- **Top-K Limit:** Cap the number of top-level categories (e.g., max 20).
  - **Selection Rule:** Sort discovered candidates by `(count DESC, token ASC)` and take the first `top_k`.
- **Stopping Conditions (Recursion):**
  - Depth > 2.
  - Child cluster size < `min_cluster_size`.
  - **Excessive Fragmentation:** Stop if > 50% of child items end up in buckets smaller than `min_cluster_size`.
  - **Config:** Default `fragmentation_limit` = 0.50 (50%).

#### E. Sanitization & Casing

All discovered tokens used as folder names must be sanitized:

- **Definitions:**
  - `normalized_value` = sanitize + casing + Windows cleanup + fallback rules.
- **Casing Rule:** If token is all-caps or in a known acronym list, preserve it (`UI`, `XML`). Else, TitleCase (`story` -> `Story`).
- **Characters:** Only `[A-Za-z0-9_-]`.
- **Reserved Names:** Avoid Windows reserved names (`CON`, `NUL`, `PRN`, etc.).
- **Windows Cleanup:** Trim trailing dots/spaces after sanitization to prevent Windows path collisions.
- **Fallback:** If sanitized name becomes empty or reserved, fallback to `_{hash}`.

### 3. The Clustering Algorithm (Grouping) & Precedence

To ensure determinism, we strictly define the order of operations for assigning a category. An item is assigned to the **first** rule it matches:

1.  **Cache Hit:** (If `--force-rebuild` not set).
2.  **Explicit Overrides:** (From config).
    - **Matching:** Keys are primarily matched against **DocFX UID**. If no match is found, fallback to **fullName** (DocFX `fullName` field, e.g., `Outer.Inner.Type`).
    - **Conflict Rule:** If both `uid` and `fullName` are present in config and disagree, **UID wins**.
3.  **Metadata (Inheritance/Interface) Cluster:**
    - **Candidate Selection:** Use the **immediate base class** as the primary hub candidate. Interfaces are considered separately and only if the base-class hub doesn't match or is generic.
    - **Interface Tie-Breaking:** If multiple interfaces are candidates, select the one with the **highest global frequency count** (within the Global namespace only). If tied, choose the lexicographically first name.
    - **Constraint:** Only allow non-trivial hubs.
      - Hub must NOT be in the **Metadata Denylist** (`MonoBehaviour`, `ScriptableObject`, `Component`, `Object`, `Exception`, `IEnumerator`, etc.).
      - **"Generic" Definition:** A hub is generic if it appears in the Metadata Denylist OR fails the non-trivial hub constraints (e.g., count < `min_cluster_size`).
      - The Metadata Denylist applies to both base classes and interfaces.
      - Hub count >= `min_cluster_size`.
      - Hub Name Length >= 4.
      - Hub Name must NOT end in `Base` (unless explicitly mapped).
    - **Naming:** If hub type appears in config, use mapped name; else sanitized hub type name.
    - Target: `Global/{HubName}/`.
4.  **Priority Suffixes:** Configurable list (e.g., `["UI", "Editor"]`) that trump prefix rules for specific items (e.g., `InventoryUI` goes to `UI`).
5.  **Strong Prefix Cluster:**
    - **Definition:** Token root appears in the top-K prefix frequency map AND count ≥ `min_cluster_size`, excluding stop-tokens.
    - **Target:** `Global/Story/`.
6.  **Strong Suffix Cluster:**
    - **Definition:** Last token appears in the suffix frequency map AND count ≥ `min_cluster_size`, excluding stop-tokens.
    - **Limit:** Suffix clusters are not top-k limited; only `min_cluster_size` applies.
    - **Target:** `Global/UI/`.
7.  **Contains/Keyword Cluster:**
    - **Source:** Config-driven keyword buckets (e.g., `keyword_clusters: {"Bosses": ["Boss"]}`). V1 defaults to empty.
    - **Note:** If `keyword_clusters` is empty (default), this rule is skipped entirely.
    - **Matching:** Match **whole tokens only** (e.g., `Boss` matches `BossBird`, NOT `Embossed`).
    - **Sanitization:** Bucket names are sanitized using folder-name rules; collisions handled by folder-vs-folder logic.
    - **Target:** `Global/{BucketName}/`.
8.  **Type Families (Sub-clustering):**
    - Identify small groups sharing a unique root (e.g., `BigBadWolf`, `BigBadWolfAnim`).
    - **Constraints:** Root must NOT be a stop-token, and Root length >= 4 chars.
    - **Target:** `Global/TypeFamilies/{Root}/`.
9.  **Misc Bucket:** `Global/Misc/`. (Keeps the root `Global/` folder clean).

### 4. Reporting & Observability

Add a `--dry-run` flag that outputs a `cluster_report.json` or Markdown summary including:

- **Run Metadata:** `config_hash`, `schema_version`.
- **Winning Rule Context:**
  - `winning_rule_id`: A stable enum field (e.g., `"metadata_hub"`, `"lexical_prefix"`).
  - `cluster_key`: The normalized cluster key: `{winning_rule_id}:{normalized_value}`.
  - Metadata: Hub type + count.
  - Lexical: Token + cluster size.
  - Cache: Run version/timestamp.
  - Contains: Matched token(s).
- **Resolved Path:** The final output path after collision resolution and cache (`resolved_path`).
- **Ambiguity Scoring:** Runner-up matches when an item matched > 1 rule.
  - Includes `rule_id`, `cluster_key`, and `score` (float [0,1] representing match strength; higher is better).
- **Misc Percentage:** Track how many items remain unclustered.

### 5. Config Knobs (Summary)

The following keys will be available in the configuration:

- `path_overrides`: Explicit `uid` (preferred) or `fullName` -> Path mapping.
- `priority_suffixes`: List of suffix tokens that override prefix clustering (e.g., `["UI", "Editor"]`).
- `keyword_clusters`: Config-driven keyword buckets for rule #7.
- `hub_types`: Explicit Hub -> Folder mapping.
- `threshold_tuning`: `min_cluster_size`, `top_k`, `max_depth`, `fragmentation_limit`.
- `cache_policy`: `stale_prune_after_runs` (defines N).
- `stop_tokens`: Tokens ignored as roots.
- `denylists`:
  - `metadata_denylist`: Denylisted base classes/interfaces.
  - `attribute_denylist`: **Reserved for future use**. (No attribute clustering in V1).
- `acronyms`: Custom tokens to preserve as all-caps (Built-in defaults + Config overrides).

### 6. Canonical Metadata

Generated Markdown files will include a YAML frontmatter block for easier maintenance:

- `uid`: The DocFX UID.
- `canonical_path`: The current Wiki path.

## Implementation Plan

1.  **Enhance `src/docfx_yml_to_wikijs.py`**:
    - Update `build_index` to extract `inheritance` and `implements`.
    - Implement `analyze_global_namespace(items: list[ItemInfo])`.
    - Implement a `GlobalPathResolver` class with caching, sanitization, and precedence logic.
2.  **Implement Tokenization & Sanitization Pipeline**:
    - Add regex-based tokenizer with acronym and numeric suffix support.
    - Implement Casing/Reserved Name logic.
3.  **Implement Stability Layer**:
    - Add logic to load/save `global_namespace_map.json` with versioning/hashing.
    - Add logic to generate stub redirects.
    - Implement collision handling (suffixing + file/folder/folder resolution).
4.  **Reporting**:
    - Implement the dry-run report with config hash, winning contexts, and runner-ups.
5.  **Refactor Path Generation**:
    - Update `page_path_for_fullname` to query the `GlobalPathResolver`.

## Conclusion

By combining lexical name analysis with **constrained metadata static analysis**, the tool becomes a powerful utility for organizing complex flat namespaces in Unity/C# projects. It ensures a clean, semantic Wiki structure while maintaining link stability.
