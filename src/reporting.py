import json
import time
from typing import List, Dict, Any
from src.global_path_resolver import ResolutionResult

class ClusterReport:
    def __init__(self, config_hash: str, schema_version: int):
        self.config_hash = config_hash
        self.schema_version = schema_version
        self.results: List[ResolutionResult] = []
        self.start_time = time.time()

    def add_result(self, result: ResolutionResult):
        self.results.append(result)

    def generate_report(self, path: str):
        report = {
            "meta": {
                "timestamp": time.time(),
                "duration": time.time() - self.start_time,
                "config_hash": self.config_hash,
                "schema_version": self.schema_version,
                "total_items": len(self.results)
            },
            "results": [
                {
                    "uid": r.uid,
                    "path": r.final_path,
                    "winning_rule": r.winning_rule,
                    "score": r.score,
                    "cluster_key": r.cluster_key,
                    "ambiguity": r.ambiguity
                }
                for r in self.results
            ],
            "stats": self._compute_stats()
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    def _compute_stats(self) -> Dict[str, Any]:
        rule_counts: Dict[str, int] = {}
        for r in self.results:
            rule_counts[r.winning_rule] = rule_counts.get(r.winning_rule, 0) + 1
        return {"rule_counts": rule_counts}
