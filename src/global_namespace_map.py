"""Logic for managing a persistent mapping of global UIDs to file paths."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1


class GlobalNamespaceMap:
    """Manages a persistent cache of UID to file path mappings for global items."""

    def __init__(self, path: str, current_config_hash: str) -> None:
        """Initialize the map with a storage path and current configuration hash."""
        self.path = Path(path)
        self.current_config_hash = current_config_hash
        self.mapping: dict[str, dict[str, Any]] = {}  # uid -> {path, last_seen}
        self.meta: dict[str, Any] = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "config_hash": current_config_hash,
            "run_id": 0,
        }
        self.accessed_uids: set[str] = set()
        self.dirty = False

    def load(self, *, accept_legacy: bool = False) -> None:
        """Load the mapping from disk."""
        if not self.path.exists():
            return

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))

            schema_ver = data.get("meta", {}).get("schema_version", 0)

            if schema_ver != CURRENT_SCHEMA_VERSION:
                if not accept_legacy:
                    logger.warning(
                        "Schema version mismatch (%s != %s). Ignoring cache.",
                        schema_ver,
                        CURRENT_SCHEMA_VERSION,
                    )
                    return
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

        except Exception:
            logger.exception("Error loading cache")

    def lookup(self, uid: str) -> str | None:
        """Return the cached path for a UID, marking it as accessed."""
        entry = self.mapping.get(uid)
        if entry:
            self.accessed_uids.add(uid)
            return entry.get("path")
        return None

    def update(self, uid: str, path: str) -> None:
        """Update or add a mapping for a UID."""
        # We don't verify if path changed here to set dirty?
        # Actually we should.
        entry = self.mapping.get(uid)
        if not entry:
            self.mapping[uid] = {"path": path, "last_seen": 0}  # Placeholder
            self.dirty = True
        elif entry.get("path") != path:
            entry["path"] = path
            self.dirty = True

        self.accessed_uids.add(uid)

    def save(self, prune_stale_threshold: int = 0) -> None:
        """Save the cache to disk.

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
                logger.info("Pruned stale UID: %s", uid)

        # Create directory if needed
        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)

        self.path.write_text(
            json.dumps(
                {"meta": self.meta, "mapping": self.mapping},
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
