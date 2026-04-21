#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_ROOT="$REPO_ROOT/skills"

SKILL_NAMES=(
  architect-diagram
  architect-init
  architect-plan
  run-architecture-eval
  run-plan-eval
)

link_skill_set() {
  local target_root="$1"
  mkdir -p "$target_root"

  for skill_name in "${SKILL_NAMES[@]}"; do
    ln -sfn "../../skills/$skill_name" "$target_root/$skill_name"
  done
}

if [[ ! -d "$SKILLS_ROOT" ]]; then
  echo "setup-local-skill-links: skills root not found at $SKILLS_ROOT" >&2
  exit 1
fi

link_skill_set "$REPO_ROOT/.agents/skills"
link_skill_set "$REPO_ROOT/.claude/skills"

cat <<EOF
Created local skill symlinks:
- $REPO_ROOT/.agents/skills
- $REPO_ROOT/.claude/skills

These paths are local-only convenience shims and are gitignored.
EOF
