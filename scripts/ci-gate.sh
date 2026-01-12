#!/bin/bash
set -e

echo ""
echo "--- Running Step: Ruff Formatting (Check) ---"
echo "$ uv run ruff format --check"
uv run ruff format --check

echo ""
echo "--- Running Step: Ruff Linting ---"
echo "$ uv run ruff check"
uv run ruff check

echo ""
echo "--- Running Step: Mypy Type Checking ---"
echo "$ uv run mypy ."
uv run mypy .

echo ""
echo "--- Running Step: Pytest Unit Tests ---"
echo "$ uv run pytest"
uv run pytest

echo ""
echo "✅ CI checks passed successfully."
