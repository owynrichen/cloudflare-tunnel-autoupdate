#!/usr/bin/env bash
set -euo pipefail

# Simple loop to run the cli every N seconds
MAPPINGS=${1:-mappings.yaml}
INTERVAL=${INTERVAL:-60}

while true; do
  uv run -- python -m src.cli "$MAPPINGS" || true
  sleep "$INTERVAL"
done
