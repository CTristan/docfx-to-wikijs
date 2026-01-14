# Plan: Global Namespace Refactoring

## Objective

Implement a robust, rule-based system to subdivide the massive `Global` namespace into meaningful subdirectories while ensuring documentation path stability and minimizing link rot.

## Guiding Principles

- **Stability First:** All paths must be deterministic. Existing paths should be preserved via cache unless explicitly rebuilt.
- **Link Integrity:** Permanent redirects (stubs) must be generated for any path changes.
- **Observability:** Every run must produce a detailed report explaining _why_ an item was placed where it was.
- **Configurability:** The heuristics (prefixes, suffixes, hubs) must be tweakable without code changes.

## Phase 1: Infrastructure & Stability Layer

_Goal: Establish the caching, configuration, and reporting mechanisms before moving files._

- [ ] **Task 1.1: Configuration Schema & Loading**
  - Define the configuration structure (thresholds, stop_tokens, priority_suffixes, etc.).
  - Implement merge rules: deep-merge objects; arrays replace by default; additive sets for `acronyms`.
  - Implement canonical config hashing (for change detection).
  - **Test:** Config merge snapshot tests + config_hash stability tests.
- [ ] **Task 1.2: Persistent Mapping Cache**
  - Implement `GlobalNamespaceMap` class to handle `global_namespace_map.json`.
  - Implement `load()`, `save()`, and `lookup()` methods.
  - Implement schema versioning and legacy migration logic (rewrite on save).
  - **Test:** Verify cache load/save cycles, config hash validation, and stale UID handling + `--prune-stale` behavior.
- [ ] **Task 1.3: Redirect Stub Generator**
  - Implement `StubGenerator` class.
  - Logic to generate Markdown stubs with frontmatter (`uid`, `old_path`, `new_path`).
  - Ensure stub filenames are immutable once created.
  - **Test:** Verify stub content generation and idempotency.

**Phase 1 Exit Criteria:** Config loads and hashes deterministically; cache round-trips correctly; stubs are generated with correct metadata and are idempotent.

## Phase 2: Analysis & Discovery Engine

_Goal: Implement the logic to analyze the flat namespace and discover clusters._

- [ ] **Task 2.1: Universal Tokenizer & Sanitizer**
  - Implement `Tokenizer` class with CamelCase splitting, acronym handling, and stop-token awareness (do not drop tokens; stop-token filtering happens during cluster selection).
  - Implement `Sanitizer` for folder names (casing, reserved chars, Windows cleanup).
  - Define `normalized_value` logic centrally: sanitize + casing + Windows cleanup + fallback rules.
  - **Test:** Unit tests for tokenization edge cases: `XMLParser`, `Vector3`, `2D`, nested types (`Outer+Inner`), and generic arity (`` Thing`1 ``).
- [ ] **Task 2.2: Metadata Extraction**
  - Enhance `docfx_yml_to_wikijs.py` to extract `inheritance` and `implements` from YAML.
  - Build `MetadataIndex` to track base classes and interfaces.
- [ ] **Task 2.3: Frequency Analysis**
  - Implement frequency counting for Prefixes, Suffixes, and Base Classes (Global namespace only).
  - Compute `PrefixFrequency` (Top-K limited) and `SuffixFrequency` (unbounded by Top-K, only `min_cluster_size` applies).
  - Implement identification logic for "Strong Clusters".
  - **Test:** Verify frequency counts and Top-K selection against a mock dataset.

**Phase 2 Exit Criteria:** Discovery phase produces stable candidate clusters and correctly tokenizes all project-specific naming patterns.

## Phase 3: The Clustering Algorithm

_Goal: Implement the precedence rules to assign categories._

- [ ] **Task 3.1: GlobalPathResolver Core**
  - Create `GlobalPathResolver` class.
  - Implement the **Precedence Chain**: Cache → Overrides → Metadata → Priority Suffix → Strong Prefix → Strong Suffix → Keyword → Family → Misc.
  - Note: Keyword rule is skipped if `keyword_clusters` is empty.
  - Implement collision handling (File vs File, Folder vs File, Folder vs Folder, Case-insensitivity) using the documented policies (deterministic hash suffixing; folder-wins with `{Name}_Page.md`; canonical path normalization).
  - Define deterministic `match_score` computation per rule type (e.g., cache/override=1.0; metadata proportional to hub strength; lexical proportional to frequency).
  - **Test:** Verify precedence respected across multiple rules; verify folder-vs-file and case-insensitive collision resolution.
- [ ] **Task 3.2: Metadata Hub Logic**
  - Implement rule: Immediate Base Class -> Interface (Tie-breaking).
  - Apply denylists and non-trivial hub constraints.
- [ ] **Task 3.3: Lexical & Keyword Rules**
  - Implement Priority Suffix, Strong Prefix, Strong Suffix, and Keyword matching.
  - Implement Type Family sub-clustering.
  - **Test:** Unit tests for each rule type to ensure correct category assignment.

**Phase 3 Exit Criteria:** Resolver assigns every item to exactly one deterministic path, respecting the precedence chain and resolving all filesystem collisions.

## Phase 4: Integration & Reporting

_Goal: Wire everything together and provide visibility._

- [ ] **Task 4.1: Dry-Run & Reporting**
  - Implement `--dry-run` flag.
  - Generate `cluster_report.json` with `winning_rule_id`, `cluster_key`, `score`, and `ambiguity` data (including runner-up `rule_id`, `cluster_key`, and `score`).
  - **Test:** Run against the sample dataset and verify report output matches expected snapshots.
- [ ] **Task 4.2: Path Generation Integration**
  - Update `docfx_yml_to_wikijs.py` to use `GlobalPathResolver`.
  - Inject canonical metadata (`uid`, `canonical_path`) into generated Markdown.
- [ ] **Task 4.3: CLI Flags & Polish**
  - Add `--force-rebuild`, `--prune-stale`, `--accept-legacy-cache`, and `--config <path>` (explicit config file path).
  - Final end-to-end verification.

**Phase 4 Exit Criteria:** Dry-run report is accurate and diagnostic; full integration produces a stable, correctly organized directory structure with all metadata.

## Phase 5: Documentation

_Goal: Ensure the system is maintainable._

- [ ] **Task 5.1: Update Developer Docs**
  - Document the new configuration options and merge semantics.
  - Explain the clustering algorithm, precedence rules, and score calculation.
  - Explain how to handle cache invalidation, stubs, and collision resolution.

**Phase 5 Exit Criteria:** Documentation fully describes all new behaviors, policies, and configuration knobs.
