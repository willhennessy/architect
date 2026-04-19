#!/usr/bin/env bash
set -euo pipefail

ROOT="${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT is required}"
DATA="${CLAUDE_PLUGIN_DATA:?CLAUDE_PLUGIN_DATA is required}"

mkdir -p "$DATA"

install_node_deps() {
  if ! diff -q "$ROOT/package.json" "$DATA/package.json" >/dev/null 2>&1; then
    cp "$ROOT/package.json" "$DATA/package.json"
    rm -rf "$DATA/node_modules"
    (
      cd "$DATA"
      npm install --omit=dev --no-fund --no-audit
    ) || {
      rm -f "$DATA/package.json"
      exit 1
    }
  fi
}

install_python_deps() {
  if ! diff -q "$ROOT/requirements.txt" "$DATA/requirements.txt" >/dev/null 2>&1; then
    cp "$ROOT/requirements.txt" "$DATA/requirements.txt"
    rm -rf "$DATA/venv"
    python3 -m venv "$DATA/venv"
    "$DATA/venv/bin/python" -m pip install --upgrade pip >/dev/null
    "$DATA/venv/bin/python" -m pip install -r "$DATA/requirements.txt" || {
      rm -f "$DATA/requirements.txt"
      exit 1
    }
  fi
}

install_node_deps
install_python_deps
