"""Development script to run checks (linting, types, tests) and the main application."""

import argparse
import subprocess
import sys


def run_command(command: list[str], step_name: str) -> None:
    """Run a shell command as a step in the development process."""
    print(f"\n--- Running Step: {step_name} ---")
    print(f"$ {' '.join(command)}")
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        print(f"\n❌ Failed: {step_name}")
        sys.exit(1)


def main() -> None:
    """Run the development checks and optionally the main script."""
    parser = argparse.ArgumentParser(
        description="Run development checks and main script."
    )
    parser.add_argument(
        "--ci", action="store_true", help="Run checks and tests only, skipping main.py"
    )
    args = parser.parse_args()

    if args.ci:
        run_command(["./scripts/ci-gate.sh"], "CI Gate Checks")
        print("\n✅ CI checks passed successfully. Skipping execution of main.py.")
        return

    # Run auto-formatting and fixing
    run_command(["uv", "run", "ruff", "format"], "Ruff Formatting")
    run_command(
        ["uv", "run", "ruff", "check", "--fix", "--unsafe-fixes"],
        "Ruff Linting & Fixes",
    )

    # Run the CI gate to verify everything
    run_command(["./scripts/ci-gate.sh"], "CI Gate Checks")

    # 5. Run main.py
    run_command(
        ["uv", "run", "python", "main.py"],
        "Main Entry Point",
    )

    print("\n✅ All development checks and main script passed successfully.")


if __name__ == "__main__":
    main()
