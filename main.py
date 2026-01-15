"""Main orchestration script for generating DocFX metadata and Wiki.js documentation."""

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path


def run_command(cmd_list: Sequence[str | Path], cwd: Path | str | None = None) -> None:
    """Run a command and exit if it fails."""
    cmd_str = " ".join(str(x) for x in cmd_list)
    print(f"Running: {cmd_str}")
    try:
        subprocess.run(cmd_list, check=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {cmd_str}")
        sys.exit(e.returncode)


def main() -> None:
    """Run the full documentation generation pipeline."""
    parser = argparse.ArgumentParser(
        description="Generate DocFX metadata and Wiki.js documentation."
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Run development checks (linting, tests) before generating documentation",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze and generate report without writing files",
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Ignore cache and rebuild all clusters",
    )
    parser.add_argument(
        "--prune-stale",
        action="store_true",
        help="Remove stale entries from cache",
    )
    parser.add_argument(
        "--accept-legacy-cache",
        action="store_true",
        help="Accept and migrate legacy cache formats",
    )
    parser.add_argument(
        "--config",
        help="Path to configuration file",
    )
    args = parser.parse_args()

    root_dir = Path(__file__).parent

    if args.dev:
        print("--- Running Development Checks ---")
        check_script = root_dir / "scripts" / "run_checks.sh"
        run_command([str(check_script)])
        print(
            "\n✅ Development checks passed. "
            "Proceeding with documentation generation.\n"
        )

    # 1. Generate YAML metadata using dotnet docfx
    print("--- Step 1: Generating DocFX metadata ---")
    # This command looks for docfx.json in the current directory by default
    run_command(["dotnet", "docfx", "metadata"])

    # 2. Convert YAML to Wiki.js Markdown
    print("\n--- Step 2: Converting YAML to Wiki.js Markdown ---")
    yml_dir = root_dir / "api"
    out_dir = root_dir / "wikijs_out"

    # Using the current python interpreter
    python_exe = sys.executable

    cmd = [
        python_exe,
        "-m",
        "src.docfx_yml_to_wikijs",
        str(yml_dir),
        str(out_dir),
        "--include-namespace-pages",
        "--include-member-details",
        "--home-page",
        "--api-root",
        "/api",
    ]

    if args.dry_run:
        cmd.append("--dry-run")
    if args.force_rebuild:
        cmd.append("--force-rebuild")
    if args.prune_stale:
        cmd.append("--prune-stale")
    if args.accept_legacy_cache:
        cmd.append("--accept-legacy-cache")
    if args.config:
        cmd.extend(["--config", args.config])

    run_command(cmd)

    print(f"\nSUCCESS: Documentation generated in {out_dir}")


if __name__ == "__main__":
    main()
