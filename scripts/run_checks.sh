#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "${repo_root}"

# Usage / Help
print_help() {
  echo "Usage: $(basename "$0")"
  echo
  echo "Run project validation checks. Performs formatting/autofixing first,"
  echo "then runs read-only checks (ci-gate.sh)."
  echo
}

for arg in "$@"; do
  case "$arg" in
    --help|-h)
      print_help
      exit 0
      ;;
    *)
      echo "Unknown option: $arg"
      print_help
      exit 1
      ;;
  esac
done

# -----------------------------------------------------------------------------
# 1) Mutating gate first: ruff format + fix, then fail if it changed anything.
# -----------------------------------------------------------------------------

echo "Running lint formatting + autofixes (must be clean before read-only checks)..."
echo "Running ruff format..."
uv run --project "${repo_root}" --directory "${repo_root}" ruff format

echo "Running ruff fix (no-error mode)..."
uv run --project "${repo_root}" --directory "${repo_root}" ruff check --exit-zero --fix --unsafe-fixes -q

echo "Formatting checks passed (no changes)."

# -----------------------------------------------------------------------------
# 2) Run core CI gate checks (parallelized in ci-gate.sh)
# -----------------------------------------------------------------------------

echo "Delegating to scripts/ci-gate.sh for core checks..."
./scripts/ci-gate.sh

echo "All checks passed."
