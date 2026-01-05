import subprocess
import sys
from pathlib import Path


def run_command(cmd_list, cwd=None) -> None:
    """Run a command and exit if it fails."""
    cmd_str = " ".join(str(x) for x in cmd_list)
    print(f"Running: {cmd_str}")
    try:
        subprocess.run(cmd_list, check=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {cmd_str}")
        sys.exit(e.returncode)


def main() -> None:
    root_dir = Path(__file__).parent

    # 1. Generate YAML metadata using dotnet docfx
    print("--- Step 1: Generating DocFX metadata ---")
    # This command looks for docfx.json in the current directory by default
    run_command(["dotnet", "docfx", "metadata"])

    # 2. Convert YAML to Wiki.js Markdown
    print("\n--- Step 2: Converting YAML to Wiki.js Markdown ---")
    script_path = root_dir / "scripts" / "docfx_yml_to_wikijs.py"
    yml_dir = root_dir / "api"
    out_dir = root_dir / "wikijs_out"

    # Using the current python interpreter
    python_exe = sys.executable

    cmd = [
        python_exe,
        str(script_path),
        str(yml_dir),
        str(out_dir),
        "--include-namespace-pages",
        "--include-member-details",
        "--home-page",
        "--api-root",
        "/api",
    ]

    run_command(cmd)

    print(f"\nSUCCESS: Documentation generated in {out_dir}")


if __name__ == "__main__":
    main()
