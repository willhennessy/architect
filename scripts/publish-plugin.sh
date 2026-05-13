#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MARKETPLACE_PATH="$REPO_ROOT/.claude-plugin/marketplace.json"
PLUGIN_ROOT="$REPO_ROOT/claude-plugin/architect"
EXPECTED_MARKETPLACE_NAME="plugins"
EXPECTED_MARKETPLACE_DESCRIPTION="Interactive architecture diagrams for planning, steering, and code review"
EXPECTED_PLUGIN_SOURCE="./claude-plugin/architect"

die() {
  echo "publish-plugin: $*" >&2
  exit 1
}

require_clean_git_state() {
  if [[ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]]; then
    die "git worktree is not clean. Commit or stash changes before publishing."
  fi
}

require_main_branch() {
  local branch
  branch="$(git -C "$REPO_ROOT" branch --show-current)"
  if [[ "$branch" != "main" ]]; then
    die "current branch is '$branch'. Switch to 'main' before publishing."
  fi
}

resolve_claude_cmd() {
  if command -v claude >/dev/null 2>&1; then
    CLAUDE_CMD=(claude)
  elif command -v claude-code >/dev/null 2>&1; then
    CLAUDE_CMD=(claude-code)
  elif command -v npx >/dev/null 2>&1; then
    CLAUDE_CMD=(npx -y @anthropic-ai/claude-code)
  else
    die "could not find 'claude', 'claude-code', or 'npx' in PATH."
  fi
}

verify_marketplace_json() {
  python3 - "$MARKETPLACE_PATH" "$EXPECTED_MARKETPLACE_NAME" "$EXPECTED_MARKETPLACE_DESCRIPTION" "$EXPECTED_PLUGIN_SOURCE" <<'PY'
import json
import pathlib
import sys

marketplace_path = pathlib.Path(sys.argv[1])
expected_name = sys.argv[2]
expected_description = sys.argv[3]
expected_source = sys.argv[4]

if not marketplace_path.exists():
    raise SystemExit(f"root marketplace file is missing: {marketplace_path}")

data = json.loads(marketplace_path.read_text(encoding="utf-8"))

if data.get("name") != expected_name:
    raise SystemExit(
        f"marketplace name mismatch: expected '{expected_name}', got '{data.get('name')}'"
    )

metadata = data.get("metadata") or {}
if metadata.get("description") != expected_description:
    raise SystemExit(
        "marketplace description mismatch: "
        f"expected '{expected_description}', got '{metadata.get('description')}'"
    )

plugins = data.get("plugins") or []
architect = next((plugin for plugin in plugins if plugin.get("name") == "architect"), None)
if architect is None:
    raise SystemExit("marketplace does not define an 'architect' plugin entry")

if architect.get("source") != expected_source:
    raise SystemExit(
        "architect plugin source mismatch: "
        f"expected '{expected_source}', got '{architect.get('source')}'"
    )
PY
}

print_checklist() {
  cat <<'EOF'

Publish checklist:
1. Review the diff from sync + marketplace changes.
2. Commit the synced plugin files and marketplace changes.
3. Push to GitHub.
4. Refresh the local published-plugin install:
   claude plugin marketplace update plugins && claude plugin update architect@plugins --scope user
5. Restart Claude so the updated plugin version is actually loaded.
EOF
}

main() {
  require_clean_git_state
  require_main_branch
  resolve_claude_cmd

  cd "$REPO_ROOT"

  echo "Syncing plugin bundle..."
  python3 "$REPO_ROOT/scripts/sync-claude-plugin.py"

  echo "Validating root marketplace..."
  "${CLAUDE_CMD[@]}" plugin validate "$REPO_ROOT"

  echo "Validating plugin bundle..."
  "${CLAUDE_CMD[@]}" plugin validate "$PLUGIN_ROOT"

  echo "Verifying root marketplace metadata..."
  verify_marketplace_json

  print_checklist
}

main "$@"
