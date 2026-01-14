"""Logic for generating reports on global namespace resolution."""

import json
import time
from pathlib import Path
from typing import Any

from src.resolution_result import ResolutionResult


class ClusterReport:
    """Collects and summarizes the results of global namespace path resolution."""

    def __init__(self, config_hash: str, schema_version: int) -> None:
        """Initialize the report with metadata."""
        self.config_hash = config_hash
        self.schema_version = schema_version
        self.results: list[ResolutionResult] = []
        self.start_time = time.time()

    def add_result(self, result: ResolutionResult) -> None:
        """Add a single resolution result to the report."""
        self.results.append(result)

    def generate_report(self, path: str, max_folder_size: int = 250) -> None:
        """Write the summary report to a JSON file."""
        report = {
            "meta": {
                "timestamp": time.time(),
                "duration": time.time() - self.start_time,
                "config_hash": self.config_hash,
                "schema_version": self.schema_version,
                "total_items": len(self.results),
            },
            "results": [
                {
                    "uid": r.uid,
                    "path": r.final_path,
                    "winning_rule": r.winning_rule,
                    "score": r.score,
                    "cluster_key": r.cluster_key,
                    "initial_root": r.initial_root,
                    "ambiguity": r.ambiguity,
                }
                for r in self.results
            ],
            "stats": self._compute_stats(max_folder_size),
        }

        Path(path).write_text(json.dumps(report, indent=2), encoding="utf-8")

    def _compute_stats(self, max_folder_size: int) -> dict[str, Any]:
        rule_counts: dict[str, int] = {}
        folder_counts: dict[str, int] = {}

        rerouted_count = 0
        unmapped_count = 0

        for r in self.results:
            rule_counts[r.winning_rule] = rule_counts.get(r.winning_rule, 0) + 1

            # Extract top-level root
            parts = r.final_path.split("/")
            if len(parts) > 1:
                root = parts[1]
                folder_counts[root] = folder_counts.get(root, 0) + 1

            # Reroute stats (unmapped only)
            if r.winning_rule not in {"cache", "override"}:
                unmapped_count += 1
                # If final top-level root differs from initial
                initial_root = r.initial_root
                final_root = parts[1] if len(parts) > 1 else ""
                if initial_root and final_root and initial_root != final_root:
                    rerouted_count += 1

        total_items = len(self.results)
        num_folders = len(folder_counts)
        singleton_folders = [f for f, c in folder_counts.items() if c == 1]

        misc_share = (
            (folder_counts.get("Misc", 0) / total_items) if total_items > 0 else 0
        )
        singleton_rate = (
            (len(singleton_folders) / num_folders) if num_folders > 0 else 0
        )
        reroute_share = (rerouted_count / unmapped_count) if unmapped_count > 0 else 0

        # Fragmentation: % of folders with < 3 items
        fragmentation_threshold = 3
        small_folders = [
            f
            for f, c in folder_counts.items()
            if c < fragmentation_threshold and f != "Misc"
        ]
        fragmentation = (
            (len(small_folders) / (num_folders - (1 if "Misc" in folder_counts else 0)))
            if (num_folders > (1 if "Misc" in folder_counts else 0))
            else 0
        )

        # Nav Friction: Median files per top-level folder
        sorted_counts = sorted(folder_counts.values())
        median_files: float = 0.0
        if sorted_counts:
            mid = len(sorted_counts) // 2
            if len(sorted_counts) % 2 == 0:
                median_files = (sorted_counts[mid - 1] + sorted_counts[mid]) / 2
            else:
                median_files = sorted_counts[mid]

        capacity_constraint_ok = all(
            c <= max_folder_size for f, c in folder_counts.items() if f != "Misc"
        )

        return {
            "rule_counts": rule_counts,
            "folder_counts": folder_counts,
            "metrics": {
                "total_folders": num_folders,
                "singleton_rate": singleton_rate,
                "misc_share": misc_share,
                "reroute_share": reroute_share,
                "fragmentation": fragmentation,
                "median_files_per_folder": median_files,
                "capacity_constraint_ok": capacity_constraint_ok,
                "largest_folder_size": max(folder_counts.values())
                if folder_counts
                else 0,
            },
        }
