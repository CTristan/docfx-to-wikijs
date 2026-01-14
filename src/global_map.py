import json
import logging
from typing import Dict, Optional, Any, Set
from pathlib import Path

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1

class GlobalNamespaceMap:
    def __init__(self, path: str, current_config_hash: str):
        self.path = Path(path)
        self.current_config_hash = current_config_hash
        self.mapping: Dict[str, Dict[str, Any]] = {}  # uid -> {path, last_seen}
        self.meta: Dict[str, Any] = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "config_hash": current_config_hash,
            "run_id": 0
        }
        self.accessed_uids: Set[str] = set()
        self.dirty = False

    def load(self, accept_legacy: bool = False):
        if not self.path.exists():
            return

        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            schema_ver = data.get("meta", {}).get("schema_version", 0)
            
            if schema_ver != CURRENT_SCHEMA_VERSION:
                if not accept_legacy:
                    logger.warning(f"Schema version mismatch ({schema_ver} != {CURRENT_SCHEMA_VERSION}). Ignoring cache.")
                    return
                else:
                    logger.info("Accepting legacy cache. Will be migrated.")
            
            self.meta = data.get("meta", {})
            # Ensure meta has run_id
            if "run_id" not in self.meta:
                self.meta["run_id"] = 0
                
            raw_mapping = data.get("mapping", {})
            
            # Migrate mapping: string -> dict
            for uid, val in raw_mapping.items():
                if isinstance(val, str):
                    self.mapping[uid] = {"path": val, "last_seen": self.meta["run_id"]}
                else:
                    self.mapping[uid] = val
            
        except Exception as e:
            logger.error(f"Error loading cache: {e}")

    def lookup(self, uid: str) -> Optional[str]:
        entry = self.mapping.get(uid)
        if entry:
            self.accessed_uids.add(uid)
            return entry.get("path")
        return None

    def update(self, uid: str, path: str):
        # We don't verify if path changed here to set dirty? 
        # Actually we should.
        entry = self.mapping.get(uid)
        if not entry:
            self.mapping[uid] = {"path": path, "last_seen": 0} # Placeholder
            self.dirty = True
        elif entry.get("path") != path:
            entry["path"] = path
            self.dirty = True
        
        self.accessed_uids.add(uid)

    def save(self, prune_stale_threshold: int = 0):
        """
        Save the cache to disk.
        Updates run_id and last_seen for accessed items.
        Prunes items not seen for > prune_stale_threshold runs.
        """
        # Increment run ID
        current_run_id = self.meta.get("run_id", 0) + 1
        self.meta["run_id"] = current_run_id
        self.meta["config_hash"] = self.current_config_hash
        self.meta["schema_version"] = CURRENT_SCHEMA_VERSION
        
        # Update last_seen for accessed items
        for uid in self.accessed_uids:
            if uid in self.mapping:
                self.mapping[uid]["last_seen"] = current_run_id

        # Prune
        if prune_stale_threshold > 0:
            to_remove = []
            for uid, entry in self.mapping.items():
                last_seen = entry.get("last_seen", 0)
                # If current_run_id is 10, and last_seen is 5. Age is 5.
                # If threshold is 5, we keep it.
                # If last_seen is 4. Age is 6. We prune.
                if (current_run_id - last_seen) > prune_stale_threshold:
                    to_remove.append(uid)
            
            for uid in to_remove:
                del self.mapping[uid]
                self.dirty = True
                logger.info(f"Pruned stale UID: {uid}")
        
        # Create directory if needed
        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({
                "meta": self.meta,
                "mapping": self.mapping
            }, f, indent=2, sort_keys=True)
