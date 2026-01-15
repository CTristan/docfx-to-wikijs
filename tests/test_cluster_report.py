"""Tests for the ClusterReport logic."""

import json
from pathlib import Path

from src.cluster_report import ClusterReport
from src.resolution_result import ResolutionResult


def test_cluster_report_generation(tmp_path: Path) -> None:
    """Verify that the cluster report is generated correctly."""
    report = ClusterReport("hash123", 1)

    # Add some results
    res1 = ResolutionResult(
        uid="uid1",
        final_path="Global/Story/Item.md",
        winning_rule="strong_prefix",
        score=0.8,
        cluster_key="Story",
        ambiguity=[],
        initial_root="Story",
    )
    res2 = ResolutionResult(
        uid="uid2",
        final_path="Global/Misc/Other.md",
        winning_rule="misc",
        score=0.1,
        cluster_key="Misc",
        ambiguity=[],
        initial_root="Misc",
    )
    res3 = ResolutionResult(
        uid="uid3",
        final_path="Global/Story/Item2.md",
        winning_rule="strong_prefix",
        score=0.8,
        cluster_key="Story",
        ambiguity=[],
        initial_root="Story",
    )

    report.add_result(res1)
    report.add_result(res2)
    report.add_result(res3)

    output_file = tmp_path / "report.json"
    report.generate_report(str(output_file))

    assert output_file.exists()
    content = json.loads(output_file.read_text(encoding="utf-8"))

    assert content["meta"]["config_hash"] == "hash123"
    assert content["meta"]["total_items"] == 3  # noqa: PLR2004
    assert len(content["results"]) == 3  # noqa: PLR2004

    stats = content["stats"]
    assert stats["folder_counts"]["Story"] == 2  # noqa: PLR2004
    assert stats["folder_counts"]["Misc"] == 1
    assert stats["rule_counts"]["strong_prefix"] == 2  # noqa: PLR2004
    assert stats["metrics"]["total_folders"] == 2  # noqa: PLR2004
    assert stats["metrics"]["largest_folder_size"] == 2  # noqa: PLR2004
