import argparse
import subprocess
import sys


def run_command(command, step_name) -> None:
    print(f"\n--- Running Step: {step_name} ---")
    print(f"$ {' '.join(command)}")
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        print(f"\n❌ Failed: {step_name}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run development checks and main script."
    )
    parser.add_argument(
        "--ci", action="store_true", help="Run checks and tests only, skipping main.py"
    )
    args = parser.parse_args()

    # 1. Run Ruff Format
    run_command(
        ["uv", "run", "ruff", "format"],
        "Ruff Formatting",
    )

    # 2. Run Ruff
    run_command(
        ["uv", "run", "ruff", "check", "--fix", "--unsafe-fixes"],
        "Ruff Linting & Fixes",
    )

    # 3. Run Mypy
    run_command(
        ["uv", "run", "mypy", "."],
        "Mypy Type Checking",
    )

    # 4. Run Pytest
    run_command(
        ["uv", "run", "pytest"],
        "Pytest Unit Tests",
    )

    if args.ci:
        print("\n✅ CI checks passed successfully. Skipping execution of main.py.")
        return

    # 5. Run main.py
    run_command(
        ["uv", "run", "python", "main.py"],
        "Main Entry Point",
    )

    print("\n✅ All development checks and main script passed successfully.")


if __name__ == "__main__":
    main()
