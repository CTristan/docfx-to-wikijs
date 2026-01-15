# Global Namespace Subfolder Generation Rules

This document describes the concrete ordering and criteria currently used to assign items in the `Global` namespace to subfolders. It is based on the implementation in `src/global_path_resolver.py`, `src/normalization_pass.py`, and `src/load_config.py`.

## Inputs and Terms

- **Item**: A `Global` namespace type or member represented by `ItemInfo`.
- **Tokens**: The type name is tokenized by the analyzer, then normalized (sanitized) for rule evaluation.
- **Cluster key**: The subfolder name under `Global/` before final normalization (for example, `UI`).
- **Normalized root**: Canonical casing for a cluster key (via `canonicalize_root_name`).

## Rule Ordering (Initial Clustering)

Initial clustering is applied in strict precedence order. The first matching rule wins, but all candidates are recorded for later rerouting.

1. **Cache**
   - If `force_rebuild` is false and `global_namespace_map.json` has a path for the UID, that path is used as-is.

2. **Overrides**
   - `path_overrides` entry for the UID.
   - `path_overrides` entry for the fully-qualified name.

3. **Rule chain (in order)**
   - **Metadata hub** (score 0.95)
     - Uses base class or interface from metadata if it is a valid hub.
     - A hub is valid if its name length is >= 4, does not end with `Base`, and is not in `metadata_denylist`.
     - If multiple interfaces are valid, the lexicographically smallest is chosen.
   - **Priority suffix** (score 0.9)
     - If the last normalized token is in `rules.priority_suffixes`.
   - **Strong prefix** (score 0.8)
     - If the first normalized token is in the analyzer's `top_prefixes` (top-K prefixes by frequency, filtered by `thresholds.min_cluster_size`).
   - **Strong suffix** (score 0.7)
     - If the last normalized token is in the analyzer's `strong_suffixes` (based on frequency, filtered by `thresholds.min_cluster_size`).
   - **Keyword/contains** (score 0.6)
     - If any token matches a configured keyword in `rules.keyword_clusters`.
   - **Type family** (score 0.5)
     - If the first token length >= 4 and its prefix count >= `thresholds.min_family_size`.

4. **Fallback**
   - If no candidates match, the item is assigned to `Misc`.

## Normalization Pass (Post-Processing)

After initial clustering, the normalization pass runs in four steps to reduce noise and enforce top-level limits.

### Step 1: Micro-Variant Merging

- Roots are grouped by `(scope_token, prefix5)` and candidate pairs are generated.
- Candidate pairs are sorted deterministically by:
  1) scope token
  2) prefix length (desc)
  3) merged size (desc)
  4) winner (asc)
  5) loser (asc)
- A merge is allowed when:
  - The roots are not both pinned.
  - The common prefix length is >= 5.
  - The "false friends" guard passes (token boundary or similarity ratio >= 0.7; if boundaries unknown, require prefix length >= 7).
  - The "utility" guard passes:
    - If both roots are under 20 items, or
    - If prefix length >= 7.
- The union representative is deterministic: pinned roots win, otherwise lexicographically smallest root wins.

### Step 2: Determine the Kept Set

- A root is a candidate if its final size >= `thresholds.min_cluster_size`.
- Candidates are sorted by size (desc), name (asc), and the top `thresholds.max_top_level_folders` are kept.
- Pinned roots are added back if they have items and either:
  - Their size >= `thresholds.min_cluster_size`, or
  - `rules.pinned_allow_singleton` is true.

### Step 3: Reroute Orphans

If an item’s root is not in the kept set, it is rerouted by precedence (first match wins):

1. `metadata_hub`
2. `priority_suffix`
3. `strong_suffix`
4. `strong_prefix`
5. `keyword`

Within a tier, the lexicographically smallest kept root wins. If nothing matches, the item falls back to `Misc`.

### Step 4: Density Safety Valve (Oversized Roots)

If any root exceeds `thresholds.max_folder_size` (default 250), it is subdivided.

- **Token split**: Prefer splitting by the first token in the item name that is not the root itself and not in `rules.stop_tokens`.
- If the token strategy yields more than 50 subfolders, fallback to **letter split** (A-Z, `_` for non-letters).

## Path Construction and Collisions

- Final path: `Global/<cluster_key>/<SanitizedTypeName>.md`.
- Collision handling:
  - If a folder path would collide with a file path, the file is suffixed with `_Page`.
  - If a file path collides with an existing file, a 4-char hash suffix is added.
- All paths are compared in a case-insensitive, slash-normalized registry to keep results deterministic.

## Default Configuration (Current)

From `src/load_config.py` (defaults as of 2026-01-15):

- `thresholds.min_cluster_size = 3`
- `thresholds.top_k = 20`
- `thresholds.max_top_level_folders = 40`
- `thresholds.max_folder_size = 250`
- `thresholds.min_family_size = 3`
- `rules.priority_suffixes = ["UI", "Editor"]`
- `rules.stop_tokens = ["Manager", "Controller", "System", "Data", "Helper", "Util", "Base", "Common"]`
- `rules.metadata_denylist = ["MonoBehaviour", "ScriptableObject", "Component", "Object", "Exception", "IEnumerator", "ValueType", "Enum", "Attribute"]`
- `rules.pinned_allow_singleton = false`
- `rules.pinned_roots = []`

If you change these defaults or add config keys, update this document so it stays authoritative.
