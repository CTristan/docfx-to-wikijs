# TODO: Global Namespace Refactoring

## Phase 1: Infrastructure & Stability Layer
*Goal: Establish the caching, configuration, and reporting mechanisms.*

- [x] **Task 1.1: Configuration Schema & Loading** `[infra]`
  - [x] Define default configuration dictionary (thresholds, rules, etc.).
  - [x] Implement `load_config(path)` with deep-merge logic (recursive dict update).
  - [x] Implement array replacement logic (unless additive for specific keys like `acronyms`).
  - [x] Implement `compute_config_hash(config)` using canonical JSON serialization.
  - [x] **Test:** Create snapshot tests for config merging and hash stability. `[test]`

- [x] **Task 1.2: Persistent Mapping Cache** `[infra]`
  - [x] Define `GlobalNamespaceMap` class structure.
  - [x] Implement `load(path)`: Read JSON, validate schema version.
  - [x] Implement `save(path)`: Write JSON with current schema version and config hash.
  - [x] Implement `lookup(uid)` and `update(uid, path)` methods.
  - [x] Implement logic to detect stale items vs new items.
  - [x] Add `--prune-stale` logic to remove old entries.
  - [x] **Test:** Verify load/save round-trip, stale handling, and legacy migration. `[test]`

- [x] **Task 1.3: Redirect Stub Generator** `[infra]`
  - [x] Define `StubGenerator` class.
  - [x] Implement `generate_stub(old_path, new_path, uid)`: Create markdown content with frontmatter.
  - [x] Implement file writing logic (check if exists to prevent overwrite if immutable policy requires).
  - [x] **Test:** Verify generated markdown content matches expected format. `[test]`

## Phase 2: Analysis & Discovery Engine
*Goal: Analyze the flat namespace to discover clusters.*

- [x] **Task 2.1: Universal Tokenizer & Sanitizer** `[core]`
  - [x] Implement `Tokenizer` class: Regex for CamelCase, acronyms, nested types (`+`), generic arity (`` ` ``).
  - [x] Implement `Sanitizer` class: Filter characters, handle reserved names (`CON`, `PRN`), trim Windows trails.
  - [x] Implement `normalized_value` function: Token -> Sanitized -> Cased -> Cleaned.
  - [x] **Test:** Unit tests for `XMLParser`, `Vector3`, `2D`, `Outer+Inner`, `Thing`1`. `[test]`

- [x] **Task 2.2: Metadata Extraction** `[core]`
  - [x] Update `docfx_yml_to_wikijs.py` `build_index` to store `inheritance` (base classes).
  - [x] Update `docfx_yml_to_wikijs.py` `build_index` to store `implements` (interfaces).
  - [x] Create `MetadataIndex` helper class to query this data easily.

- [x] **Task 2.3: Frequency Analysis** `[core]`
  - [x] Implement `Analyzer` class.
  - [x] Compute `PrefixFrequency` map (count occurrences of first token).
  - [x] Compute `SuffixFrequency` map (count occurrences of last token).
  - [x] Implement "Top-K" selector for prefixes.
  - [x] Implement `min_cluster_size` filtering for suffixes.
  - [x] **Test:** Run analysis on mock list of items and verify counts/selections. `[test]`

## Phase 3: The Clustering Algorithm
*Goal: Assign categories based on precedence rules.*

- [x] **Task 3.1: GlobalPathResolver Core & Collision** `[core]`
  - [x] Define `GlobalPathResolver` class.
  - [x] Implement `resolve(uid, fullName, metadata)` skeleton.
  - [x] Implement `match_score` calculation helper.
  - [x] Implement **Collision Resolution**:
    - [x] File vs File (suffix hash).
    - [x] Folder vs File (rename file to `_Page.md`).
    - [x] Folder vs Folder (hash suffix on cluster key).
    - [x] Case-insensitivity normalization.
  - [x] **Test:** Unit tests for collision scenarios (e.g., `Story` folder vs `Story.md` file). `[test]`

- [x] **Task 3.2: Rule Implementations** `[core]`
  - [x] **Rule 1:** Cache Lookup (with `--force-rebuild` check).
  - [x] **Rule 2:** Config Overrides (UID > FullName).
  - [x] **Rule 3:** Metadata Hub (Base Class -> Interface).
    - [x] Check denylists (`MonoBehaviour`, etc.).
    - [x] Check hub constraints (size, name length).
  - [x] **Rule 4:** Priority Suffixes (Configurable list).
  - [x] **Rule 5:** Strong Prefix (Top-K lexical).
  - [x] **Rule 6:** Strong Suffix (Lexical > min_size).
  - [x] **Rule 7:** Keyword/Contains (Configurable buckets).
  - [x] **Rule 8:** Type Families (Common root > 4 chars).
  - [x] **Rule 9:** Misc Bucket (Fallback).
  - [x] **Test:** Unit tests verifying precedence order (e.g., Suffix wins over Prefix). `[test]`

## Phase 4: Integration & Reporting
*Goal: Wire it up and run it.*

- [x] **Task 4.1: Reporting** `[cli]`
  - [x] Implement `ClusterReport` class.
  - [x] Record winning rule, cluster key, and score.
  - [x] Record "runner-up" matches (ambiguity).
  - [x] Implement `generate_json_report(path)`.
  - [x] **Test:** Verify report JSON structure. `[test]`

- [x] **Task 4.2: Integration** `[cli]`
  - [x] Update `docfx_yml_to_wikijs.py` main loop.
  - [x] Instantiate `Analyzer` -> `GlobalPathResolver`.
  - [x] Use resolved path for file generation.
  - [x] Inject `canonical_path` and `uid` into Frontmatter.

- [x] **Task 4.3: CLI Flags** `[cli]`
  - [x] Add arguments: `--dry-run`, `--force-rebuild`, `--prune-stale`, `--config`.
  - [x] Wire arguments to logic.
  - [x] Perform end-to-end dry run on real data.

## Phase 5: Documentation
*Goal: Developer & User guides.*

- [x] **Task 5.1: Documentation** `[docs]`
  - [x] Update `README.md` or create `docs/GlobalClustering.md`.
  - [x] Document `config.yml` schema options.
  - [x] Explain the Precedence Chain.
  - [x] Explain "Stale" vs "Active" cache entries.
