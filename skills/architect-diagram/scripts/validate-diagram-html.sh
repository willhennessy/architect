#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <path-to-diagram.html>" >&2
  exit 2
fi

HTML_PATH="$1"
if [[ ! -f "$HTML_PATH" ]]; then
  echo "ERROR: diagram file not found: $HTML_PATH" >&2
  exit 1
fi

# Basic self-contained checks
if grep -Eq '<script[^>]+src=' "$HTML_PATH"; then
  echo "ERROR: external <script src=...> found (diagram must be self-contained)." >&2
  exit 1
fi
if grep -Eq '<link[^>]+href=' "$HTML_PATH"; then
  echo "ERROR: external <link href=...> found (diagram must be self-contained)." >&2
  exit 1
fi

# Must contain at least one inline script and render entrypoint
if ! grep -q '<script>' "$HTML_PATH"; then
  echo "ERROR: no inline <script> block found." >&2
  exit 1
fi
if ! grep -q 'render()' "$HTML_PATH"; then
  echo "ERROR: expected render() call/signature not found." >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

python3 - "$HTML_PATH" "$TMP_DIR" <<'PY'
import re
import sys
from pathlib import Path

html = Path(sys.argv[1]).read_text(encoding='utf-8', errors='ignore')
out_dir = Path(sys.argv[2])

scripts = re.findall(r"<script>([\s\S]*?)</script>", html)
if not scripts:
    print("ERROR: no inline script content extracted.", file=sys.stderr)
    raise SystemExit(1)

for i, content in enumerate(scripts, 1):
    (out_dir / f"script_{i}.js").write_text(content, encoding='utf-8')

# heuristic catch for malformed nested template expressions like ${x-${y}}
if re.search(r"\$\{[^}]*-\$\{", html):
    print("ERROR: suspicious nested template expression found (e.g. ${x-${y}}).", file=sys.stderr)
    raise SystemExit(1)
PY

if command -v node >/dev/null 2>&1; then
  for js in "$TMP_DIR"/*.js; do
    node --check "$js" >/dev/null
  done
else
  echo "WARN: node not found; skipped full JS syntax check (heuristics only)." >&2
fi

# Comment mode guardrails (if present)
if grep -q 'Comment' "$HTML_PATH"; then
  if ! grep -q 'data-element-id' "$HTML_PATH"; then
    echo "ERROR: comment-capable diagram missing data-element-id metadata." >&2
    exit 1
  fi
fi

echo "OK: diagram validation passed"
