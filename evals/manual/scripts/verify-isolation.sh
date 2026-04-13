#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
RUNS_ROOT="$REPO_ROOT/evals/manual/runs"

usage() {
  cat <<'EOF'
Usage:
  verify-isolation.sh <run-id|run-path>

Examples:
  verify-isolation.sh run-001
  verify-isolation.sh /abs/path/to/evals/manual/runs/run-001
EOF
}

if [[ $# -ne 1 ]]; then
  usage
  exit 1
fi

if [[ "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  exit 0
fi

ARG="$1"
if [[ -d "$ARG" ]]; then
  RUN_DIR="$ARG"
else
  RUN_DIR="$RUNS_ROOT/$ARG"
fi

if [[ ! -d "$RUN_DIR" ]]; then
  echo "Run directory not found: $RUN_DIR" >&2
  exit 1
fi

python3 - "$RUN_DIR" <<'PY'
import os
import sys

run = os.path.realpath(sys.argv[1])
required = [
    "repo",
    "skills",
    "artifacts",
    os.path.join("home", ".claude", "skills"),
]

missing = [r for r in required if not os.path.exists(os.path.join(run, r))]

escaping = []
for root, dirs, files in os.walk(run):
    for name in dirs + files:
        p = os.path.join(root, name)
        if os.path.islink(p):
            target = os.path.realpath(p)
            if not (target == run or target.startswith(run + os.sep)):
                escaping.append((p, target))

if missing:
    for m in missing:
        print(f"MISSING: {m}")

if escaping:
    for src, tgt in escaping:
        print(f"ESCAPING_SYMLINK: {src} -> {tgt}")

if missing or escaping:
    sys.exit(1)

print(f"OK: {run} is isolated (no escaping symlinks; required layout present)")
PY
