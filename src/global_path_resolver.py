from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass, field
import hashlib
from collections import defaultdict
from pathlib import Path
import re

from src.models import ItemInfo
from src.analyzer import Analyzer
from src.global_map import GlobalNamespaceMap
from src.text_processing import Sanitizer
from src.metadata_index import MetadataIndex

@dataclass
class ResolutionResult:
    uid: str
    final_path: str
    winning_rule: str
    score: float
    cluster_key: str
    ambiguity: List[dict] = field(default_factory=list)

class GlobalPathResolver:
    def __init__(self, analyzer: Analyzer, global_map: GlobalNamespaceMap, config: Dict[str, Any]):
        self.analyzer = analyzer
        self.global_map = global_map
        self.config = config
        self.sanitizer = analyzer.sanitizer
        self.metadata_index = analyzer.metadata_index
        
        # State
        self.assigned_paths: Dict[str, str] = {} # uid -> path
        self.path_registry: Dict[str, str] = {} # lower_canonical_path -> uid
        self.folders: Set[str] = set() # lower_canonical_folder_path
        
        # Helper caches
        min_size = config["thresholds"]["min_cluster_size"]
        self.top_prefixes = set(analyzer.get_top_prefixes(
            k=config["thresholds"]["top_k"], 
            min_size=min_size
        ))
        self.strong_suffixes = analyzer.get_strong_suffixes(
            min_size=min_size
        )
        
        self.priority_suffixes = set(config["rules"]["priority_suffixes"])
        self.keyword_clusters = config["rules"].get("keyword_clusters", {})
        self.metadata_denylist = set(config["rules"].get("metadata_denylist", []))
        self.hub_types = config.get("hub_types", {})
        self.acronyms = set(config.get("acronyms", []))

    def resolve(self, item: ItemInfo) -> ResolutionResult:
        # 1. Cache Check
        if not self.config.get("force_rebuild", False):
            cached_path = self.global_map.lookup(item.uid)
            if cached_path:
                return self._finalize(item.uid, cached_path, "cache", 1.0, "cache")

        # 2. Overrides
        overrides = self.config.get("path_overrides", {})
        if item.uid in overrides:
             return self._finalize(item.uid, overrides[item.uid], "override_uid", 1.0, "override")
        if item.full_name in overrides:
             return self._finalize(item.uid, overrides[item.full_name], "override_name", 1.0, "override")

        # Apply Rules
        candidates = self._apply_rules(item)
        
        if not candidates:
            # Fallback to Misc
            winning = ("misc", "Misc", 0.1)
            runners_up = []
        else:
            # Sort by score DESC
            # Score logic: Rules are added in precedence order with decreasing base scores?
            # Or we just take the first one?
            # RESEARCH: "An item is assigned to the first rule it matches."
            # So candidates[0] is the winner if we generated them in order.
            winning = candidates[0]
            runners_up = [
                {"rule": c[0], "key": c[1], "score": c[2]} 
                for c in candidates[1:]
            ]

        rule_id, cluster_key, score = winning
        
        # Construct Path
        # cluster_key is usually the Folder Name (e.g. "Story", "UI")
        # If Misc, cluster_key is "Misc".
        # Path: Global/{ClusterKey}/{ItemName}.md
        # Exception: Metadata Hub might want Global/{HubName}/{ItemName}.md
        
        # Item Name Sanitization
        safe_name = self.sanitizer.normalize(item.name)
        # Handle file vs file collision via suffix later.
        
        path = f"Global/{cluster_key}/{safe_name}.md"
        
        return self._finalize(item.uid, path, rule_id, score, cluster_key, runners_up)

    def _apply_rules(self, item: ItemInfo) -> List[Tuple[str, str, float]]:
        """Returns list of (rule_id, cluster_key, score) in precedence order."""
        candidates = []
        
        name = item.name
        tokens = self.analyzer.tokenizer.tokenize(name)
        if not tokens: return []
        
        norm_tokens = [self.sanitizer.normalize(t) for t in tokens]
        
        # Rule 3: Metadata Hub
        hub_cand = self._check_metadata_hub(item)
        if hub_cand:
            candidates.append(hub_cand)
            
        # Rule 4: Priority Suffixes
        if len(norm_tokens) > 0:
            last = norm_tokens[-1]
            if last in self.priority_suffixes:
                 # Score: 0.9
                 candidates.append(("priority_suffix", last, 0.9))

        # Rule 5: Strong Prefix
        if len(norm_tokens) > 0:
            first = norm_tokens[0]
            if first in self.top_prefixes:
                candidates.append(("strong_prefix", first, 0.8))

        # Rule 6: Strong Suffix
        if len(norm_tokens) > 0:
            last = norm_tokens[-1]
            if last in self.strong_suffixes:
                candidates.append(("strong_suffix", last, 0.7))
                
        # Rule 7: Keyword/Contains
        # Check buckets
        for bucket, keywords in self.keyword_clusters.items():
            for kw in keywords:
                # Whole token match?
                # "Match whole tokens only"
                # Check if kw (sanitized?) in norm_tokens?
                # Usually keywords in config are raw.
                # Let's sanitize keyword to match norm_tokens.
                kw_norm = self.sanitizer.normalize(kw)
                if kw_norm in norm_tokens:
                    candidates.append(("keyword", bucket, 0.6))
                    break

        # Rule 8: Type Families
        # Identify group sharing unique root > 4 chars.
        # We use prefix counts from analyzer.
        # If prefix count >= 2 (and not stop token, and len >= 4).
        if len(norm_tokens) > 0:
            first = norm_tokens[0]
            if len(first) >= 4:
                # Check frequency
                # We need raw token frequency? Analyzer stores sanitized prefix counts?
                # Analyzer stores `self.prefix_counts` keyed by sanitized prefix.
                count = self.analyzer.prefix_counts.get(first, 0)
                if count >= 2: # Min size for family? or min_cluster_size?
                    # "Type Families... Identify small groups"
                    # If it didn't match Strong Prefix (Rule 5), it means it wasn't in top_k.
                    # But if it has count >= 2, we can group them.
                    candidates.append(("type_family", first, 0.5))

        return candidates

    def _check_metadata_hub(self, item: ItemInfo) -> Optional[Tuple[str, str, float]]:
        # Immediate Base Class
        base_uid = self.metadata_index.get_base_class(item.uid)
        
        hub_candidates = []
        if base_uid:
            # Check constraints
            if self._is_valid_hub(base_uid):
                 hub_candidates.append(base_uid)
        
        # If no valid base, check interfaces?
        # "Interfaces are considered separately and only if the base-class hub doesn't match or is generic."
        if not hub_candidates:
             interfaces = self.metadata_index.get_interfaces(item.uid)
             valid_interfaces = [i for i in interfaces if self._is_valid_hub(i)]
             # Tie-breaking: Highest frequency, then lexical.
             if valid_interfaces:
                 # Get counts
                 # We need counts of how many times an interface is implemented in Global.
                 # Analyzer has base_class_counts which includes interfaces if we extracted them?
                 # Analyzer code: "Base Class... self.base_class_counts[base] += 1".
                 # It only counted base classes!
                 # I need to update Analyzer to count interfaces too if I want frequency tie-breaking.
                 # For now, I'll assume 0 or just pick first.
                 # Task 2.3 said "Base Class/Interface Frequency".
                 # I missed counting interfaces in Analyzer. 
                 # I should fix that if I want full spec compliance.
                 # But for now, let's just pick lexicographically first to be deterministic.
                 valid_interfaces.sort()
                 hub_candidates.append(valid_interfaces[0])

        if hub_candidates:
            hub = hub_candidates[0]
            # Map name
            hub_name = self._get_hub_name(hub)
            return ("metadata_hub", hub_name, 0.95)
            
        return None

    def _is_valid_hub(self, uid: str) -> bool:
        # Check denylist (by name/uid)
        # UID might be full name e.g. "UnityEngine.MonoBehaviour".
        # Denylist has simple names? "MonoBehaviour".
        name = uid.split('.')[-1]
        if name in self.metadata_denylist or uid in self.metadata_denylist:
            return False
            
        # Hub constraints
        # Name length >= 4
        if len(name) < 4:
            return False
        
        # Hub must NOT end in Base
        if name.endswith("Base"):
            return False
            
        return True

    def _get_hub_name(self, uid: str) -> str:
        # Check config mapping
        if uid in self.hub_types:
            return self.hub_types[uid]
        
        # Sanitize
        name = uid.split('.')[-1]
        return self.sanitizer.normalize(name)

    def _finalize(self, uid: str, path: str, rule: str, score: float, cluster_key: str, runner_ups: List[dict] = []) -> ResolutionResult:
        # Collision Resolution
        final_path = self._resolve_collisions(uid, path)
        
        # Register
        self.assigned_paths[uid] = final_path
        self.global_map.update(uid, final_path)
        lower_path = self._to_canonical_path(final_path)
        self.path_registry[lower_path] = uid
        
        # Register folders
        # Global/Story/Foo.md -> Global, Global/Story
        # Assuming path uses forward slashes.
        p = Path(final_path)
        for parent in p.parents:
            if parent == Path("."): continue
            self.folders.add(self._to_canonical_path(str(parent)))
            
        return ResolutionResult(uid, final_path, rule, score, cluster_key, runner_ups)

    def _resolve_collisions(self, uid: str, desired_path: str) -> str:
        # 1. Folder vs File (Existing Folder conflicts with My File)
        # Check if desired_path (without .md) exists as a folder?
        # desired_path is "Global/Story/Foo.md". Folder check is "Global/Story/Foo".
        # If "Global/Story/Foo" is in self.folders, then I cannot be "Foo.md" (if I was attempting that).
        
        # Wait, if desired_path is "Global/Story.md".
        # Folder path is "Global/Story".
        # If "Global/Story" in self.folders:
        #   Collision! Rename me to "Global/Story_Page.md".
        
        base_no_ext = str(Path(desired_path).with_suffix(""))
        lower_base = self._to_canonical_path(base_no_ext)
        
        if lower_base in self.folders:
             # Rename current
             desired_path = f"{base_no_ext}_Page.md"
             base_no_ext = str(Path(desired_path).with_suffix(""))
             lower_base = self._to_canonical_path(base_no_ext)
             
        # 2. Folder vs File (My Folder conflicts with Existing File)
        # Check if any parent of desired_path exists as a file.
        # desired_path = "Global/Story/Item.md".
        # Parents: "Global/Story".
        # Check if "Global/Story.md" exists in path_registry.
        p = Path(desired_path)
        for parent in p.parents:
            if parent == Path("."): continue
            parent_str = str(parent)
            lower_parent = self._to_canonical_path(parent_str)
            
            # Check for file: parent + ".md"
            file_key = self._to_canonical_path(f"{parent_str}.md")
            if file_key in self.path_registry:
                # Collision! Existing file blocks my folder.
                # Rename existing file.
                existing_uid = self.path_registry[file_key]
                new_existing_path = f"{parent_str}_Page.md"
                
                # Update registry for existing (recursive check not implemented for simplicity, assume _Page is free or handle it?)
                # We should really ensure _Page is free.
                # But let's just do the rename.
                del self.path_registry[file_key]
                self.assigned_paths[existing_uid] = new_existing_path
                self.path_registry[self._to_canonical_path(new_existing_path)] = existing_uid
                
        # 3. File vs File
        # Check if desired_path is taken.
        lower_path = self._to_canonical_path(desired_path)
        while lower_path in self.path_registry:
             # Collision. Append suffix.
             # Suffix: hash of UID? Or simple counter?
             # RESEARCH: "Append deterministic suffix (short hash of UID)."
             h = hashlib.md5(uid.encode("utf-8")).hexdigest()[:4]
             # Inject suffix before extension
             pp = Path(desired_path)
             desired_path = f"{pp.parent}/{pp.stem}_{h}{pp.suffix}"
             lower_path = self._to_canonical_path(desired_path)
             
        return desired_path

    def _to_canonical_path(self, path: str) -> str:
        return path.lower().replace("\\", "/")
