#!/bin/bash
set -e

echo ""
echo "--- Running Step: Ruff Formatting ---"
echo "$ uv run ruff format"
uv run ruff format

echo ""
echo "--- Running Step: Ruff Linting & Fixes ---"
echo "$ uv run ruff check --fix --unsafe-fixes"
uv run ruff check --fix --unsafe-fixes

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
