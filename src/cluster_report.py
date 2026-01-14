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

    def generate_report(self, path: str) -> None:
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
                    "ambiguity": r.ambiguity,
                }
                for r in self.results
            ],
            "stats": self._compute_stats(),
        }

        Path(path).write_text(json.dumps(report, indent=2), encoding="utf-8")

    def _compute_stats(self) -> dict[str, Any]:
        rule_counts: dict[str, int] = {}
        for r in self.results:
            rule_counts[r.winning_rule] = rule_counts.get(r.winning_rule, 0) + 1
        return {"rule_counts": rule_counts}
