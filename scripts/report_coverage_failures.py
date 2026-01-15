"""Report per-file coverage below a threshold using coverage.py JSON output.

Usage:
    python report_coverage_failures.py --file /path/to/coverage.json --threshold 80
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

RED = "\033[31m"
RESET = "\033[0m"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the coverage reporter."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        required=True,
        type=pathlib.Path,
        help="Path to coverage.json produced by coverage.py",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=80.0,
        help="Minimum percentage required for lines and branches",
    )
    return parser.parse_args()


def load_coverage(path: pathlib.Path) -> dict[str, Any]:
    """Load coverage JSON from the given path."""
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - diagnostic path
        print(f"  (could not read {path}: {exc})")
        return {}


def percent(numerator: float | None, denominator: float | None) -> float | None:
    """Compute a percentage safely."""
    if numerator is None or not denominator:
        return None
    return (numerator / denominator) * 100


def format_metric(label: str, pct: float | None, *, failed: bool) -> str:
    """Format a metric label/value, coloring failures red."""
    if pct is None:
        return f"{label} n/a"

    value = f"{pct:.1f}%"
    if failed:
        value = f"{RED}{value}{RESET}"
    return f"{label} {value}"


def path_is_covered(norm_path: str) -> bool:
    """Return True if the normalized path should be included in reporting."""
    # Only consider application code under app packages (allow prefixes like
    # apps/hemograce/hemograce/... or hemograce/...).
    if not (
        "/hemograce/" in norm_path
        or "/hemogate/" in norm_path
        or "/hemobot/" in norm_path
        or norm_path.startswith(("hemograce/", "hemogate/", "hemobot/"))
    ):
        return False

    # Skip entrypoints/tooling regardless of prefix.
    base = norm_path.rsplit("/", maxsplit=1)[-1]
    if base in {"main.py"}:
        return False

    # Skip tests and fixtures.
    return not ("/tests/" in norm_path or norm_path.startswith("tests/"))


def main() -> None:
    """Report files below the coverage threshold; exit 1 if any fail."""
    args = parse_args()
    data = load_coverage(args.file)

    files = data.get("files", {})
    if not files:
        print("  (no per-file data found)")
        return

    failing: list[tuple[str, float | None, float | None, bool, bool]] = []
    checked = 0
    for path, info in files.items():
        summary = info.get("summary", {})

        norm_path = path.replace("\\", "/")
        if not path_is_covered(norm_path):
            continue

        checked += 1

        line_pct = percent(summary.get("covered_lines"), summary.get("num_statements"))
        branch_pct = percent(
            summary.get("covered_branches"), summary.get("num_branches")
        )

        line_fail = line_pct is not None and line_pct < args.threshold
        branch_fail = branch_pct is not None and branch_pct < args.threshold

        if line_fail or branch_fail:
            failing.append((path, line_pct, branch_pct, line_fail, branch_fail))

    if failing:
        for path, line_pct, branch_pct, line_fail, branch_fail in sorted(failing):
            parts = []
            if line_pct is not None:
                parts.append(format_metric("lines", line_pct, failed=line_fail))
            if branch_pct is not None:
                parts.append(format_metric("branches", branch_pct, failed=branch_fail))
            metrics = ", ".join(parts) if parts else "no metrics"
            print(f"  - {path}: {metrics}")
        sys.exit(1)

    print(f"  (none; checked {checked} app files)")
    sys.exit(0)


if __name__ == "__main__":
    main()
