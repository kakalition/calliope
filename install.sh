#!/usr/bin/env bash
# Idempotent setup for Calliope.
set -euo pipefail

cd "$(dirname "$0")"

echo "== syncing dependencies (uv) =="
uv sync --extra dev --extra observability-phoenix

if [ ! -f .env ]; then
  echo "== creating .env from .env.example =="
  cp .env.example .env
  echo "Edit .env and set OPENAI_API_KEY before running 'calliope chat'."
fi

echo "== done =="
echo "Try: uv run calliope entry \"today was a good day\" && uv run calliope stats"
