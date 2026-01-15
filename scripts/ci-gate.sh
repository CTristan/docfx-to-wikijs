#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "${repo_root}"

run_step () {
  local name="$1"
  shift
  echo
  echo "Running ${name}..."
  "$@"
  echo "✅ ${name} passed"
}

echo "Running read-only CI checks..."

run_step \
  "ruff format (check)" \
  uv run --project "${repo_root}" --directory "${repo_root}" ruff format --check

run_step \
  "ruff check" \
  uv run --project "${repo_root}" --directory "${repo_root}" ruff check

run_step \
  "mypy" \
  uv run --project "${repo_root}" --directory "${repo_root}" mypy .

run_step \
  "semgrep" \
  uv run --project "${repo_root}" --directory "${repo_root}" semgrep scan --config=auto --quiet --error

run_step \
  "pytest" \
  uv run --project "${repo_root}" --directory "${repo_root}" pytest

echo
echo "All checks passed."
