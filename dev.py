import subprocess
import sys

def run_command(command, step_name):
    print(f"\n--- Running Step: {step_name} ---")
    print(f"$ {' '.join(command)}")
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        print(f"\n❌ Failed: {step_name}")
        sys.exit(1)

def main():
    # 1. Run Ruff
    run_command(
        ["uv", "run", "ruff", "check", "--fix", "--unsafe-fixes"],
        "Ruff Linting & Fixes"
    )

    # 2. Run Mypy
    run_command(
        ["uv", "run", "mypy", "."],
        "Mypy Type Checking"
    )

    # 3. Run main.py
    run_command(
        ["uv", "run", "python", "main.py"],
        "Main Entry Point"
    )
    
    print("\n✅ All development checks and main script passed successfully.")

if __name__ == "__main__":
    main()

