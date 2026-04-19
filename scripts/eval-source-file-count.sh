#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: eval-source-file-count.sh <repo-path>" >&2
  exit 1
fi

REPO_PATH="$1"

if [[ ! -d "$REPO_PATH" ]]; then
  echo "Repo path not found: $REPO_PATH" >&2
  exit 1
fi

rg --files "$REPO_PATH" \
  -g '!**/.git/**' \
  -g '!**/node_modules/**' \
  -g '!**/dist/**' \
  -g '!**/build/**' \
  -g '!**/target/**' \
  -g '!**/vendor/**' \
  -g '!**/third_party/**' \
  -g '!**/coverage/**' \
  | wc -l | tr -d ' '
