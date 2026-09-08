#!/usr/bin/env bash
set -euo pipefail

if [ ! -d ".githooks" ]; then
  echo "No .githooks directory found. Nothing to install."
  exit 1
fi

git config core.hooksPath .githooks
echo "Configured git to use .githooks as hooks path."
echo "You can undo with: git config --unset core.hooksPath"
