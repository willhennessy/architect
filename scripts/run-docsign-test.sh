#!/usr/bin/env bash
set -euo pipefail

# Runs the fixed DocSign architecture test in an isolated directory.
# Process:
# 1) Use fixed prompt.
# 2) New run directory each time.
# 3) If architect-plan changed since last run, regenerate architecture artifacts.
#    Otherwise, reuse previous architecture artifacts and rerun diagram only.
# 4) Generate SVG fragments first, then render in demo mode (no fallback).
# 5) Produce numbered diagram-N.html output.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_ROOT="$REPO_ROOT/evals/manual-docsign-tests"
STATE_FILE="$TEST_ROOT/state.json"
PROMPT_FILE_NAME="test-prompt.txt"

TEST_PROMPT="I’m building a new multi-tenant B2B document-signing platform. We need:
- create/send documents for signature
- signer flow with email + magic link
- webhook callbacks to customer systems
- audit trail for every signature event
- admin analytics dashboard
Team is 5 engineers and we want an MVP in 10 weeks. Can you propose the architecture?"

mkdir -p "$TEST_ROOT"

last_commit=""
last_run_dir=""
next_index=1

if [[ -f "$STATE_FILE" ]]; then
  last_commit="$(python3 - <<PY
import json
p='$STATE_FILE'
try:
  d=json.load(open(p))
  print(d.get('last_commit',''))
except Exception:
  print('')
PY
)"
  last_run_dir="$(python3 - <<PY
import json
p='$STATE_FILE'
try:
  d=json.load(open(p))
  print(d.get('last_run_dir',''))
except Exception:
  print('')
PY
)"
  next_index="$(python3 - <<PY
import json
p='$STATE_FILE'
try:
  d=json.load(open(p))
  print(int(d.get('next_index',1)))
except Exception:
  print(1)
PY
)"
fi

RUN_ID="$(printf '%03d' "$next_index")"
RUN_DIR="$TEST_ROOT/run-$RUN_ID"
mkdir -p "$RUN_DIR"

printf '%s\n' "$TEST_PROMPT" > "$RUN_DIR/$PROMPT_FILE_NAME"

current_commit="$(git -C "$REPO_ROOT" rev-parse HEAD)"
plan_changed=1
reason="first run or no state"

if [[ -n "$last_commit" ]]; then
  changed_files="$(git -C "$REPO_ROOT" diff --name-only "$last_commit".."$current_commit" || true)"
  plan_changed=0
  reason="no architect-plan changes detected"
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    case "$f" in
      skills/architect-plan/*|skills/references/architecture-contract.md)
        plan_changed=1
        reason="architect-plan-related changes detected"
        break
        ;;
    esac
  done <<< "$changed_files"
fi

if (( plan_changed )); then
  # Regenerate architecture artifacts (architect-plan path)
  python3 "$REPO_ROOT/scripts/generate-docsign-plan-artifacts.py" --output-root "$RUN_DIR" >/dev/null
  run_mode="architect-plan"
else
  if [[ -z "$last_run_dir" || ! -d "$last_run_dir/architecture" ]]; then
    echo "ERROR: cannot run diagram-only mode; previous architecture artifacts not found." >&2
    exit 1
  fi
  cp -R "$last_run_dir/architecture" "$RUN_DIR/architecture"
  run_mode="architect-diagram-only"
fi

# Always generate SVG fragments first, then render in strict demo mode (no fallback)
python3 "$REPO_ROOT/skills/architect-diagram/scripts/generate-svg-fragments.py" --output-root "$RUN_DIR" >/dev/null
python3 "$REPO_ROOT/skills/architect-diagram/scripts/render-diagram-html.py" --output-root "$RUN_DIR" --demo-mode >/dev/null
"$REPO_ROOT/skills/architect-diagram/scripts/validate-diagram-html.sh" "$RUN_DIR/architecture/diagram.html" >/dev/null

DIAGRAM_NAME="diagram-$next_index.html"
cp "$RUN_DIR/architecture/diagram.html" "$TEST_ROOT/$DIAGRAM_NAME"

python3 - <<PY
import json
from pathlib import Path
state_path=Path('$STATE_FILE')
run_dir=Path('$RUN_DIR')
state={
  'last_commit': '$current_commit',
  'last_run_dir': str(run_dir),
  'next_index': int($next_index)+1,
}
state_path.write_text(json.dumps(state, indent=2))

meta={
  'run_id': '$RUN_ID',
  'run_dir': str(run_dir),
  'mode': '$run_mode',
  'render_mode': 'demo-mode-with-fragments',
  'reason': '$reason',
  'source_commit': '$current_commit',
  'diagram_file': str(Path('$TEST_ROOT') / '$DIAGRAM_NAME'),
  'svg_dir': str(run_dir / 'architecture' / '.out' / 'diagram-svg'),
}
(Path('$RUN_DIR')/'run-metadata.json').write_text(json.dumps(meta, indent=2))
PY

cat <<EOF
RUN_DIR=$RUN_DIR
RUN_MODE=$run_mode
REASON=$reason
DIAGRAM_FILE=$TEST_ROOT/$DIAGRAM_NAME
EOF
