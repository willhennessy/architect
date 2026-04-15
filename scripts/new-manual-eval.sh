#!/usr/bin/env bash
set -euo pipefail

# One-shot isolated manual eval setup.
# Creates a per-run sandbox with:
#   - copied skills snapshot
#   - copied shared skill references (skills/references)
#   - isolated HOME/.claude/skills
#   - isolated repo checkout/copy

usage() {
  cat <<'EOF'
Usage:
  new-manual-eval.sh [--repo-url <git-url> | --repo-path <local-path>]

Options:
  --repo-url <url>       Clone target repo into isolated run folder (optional)
  --repo-path <path>     Copy local repo into isolated run folder (optional)
  --run-root <path>      Parent folder for runs (default: ~/tmp/architect-manual-evals)
  --name <suffix>        Optional folder name suffix appended after timestamp
  --skills <csv>         Skill dirs to snapshot (default: architect-plan,architect-discover,architect-diagram)
  --with-skill           Include skills in run-local HOME (default)
  --without-skill        Do not include skills (baseline run)
  -h, --help             Show help

Example:
  ./scripts/new-manual-eval.sh --repo-url https://github.com/openfga/openfga.git
EOF
}

REPO_URL=""
REPO_PATH=""
RUN_ROOT="$HOME/tmp/architect-manual-evals"
RUN_NAME_SUFFIX=""
SKILLS_CSV="architect-plan,architect-discover,architect-diagram"
WITH_SKILL=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-url)
      REPO_URL="$2"; shift 2 ;;
    --repo-path)
      REPO_PATH="$2"; shift 2 ;;
    --run-root)
      RUN_ROOT="$2"; shift 2 ;;
    --name|--run-name)
      RUN_NAME_SUFFIX="$2"; shift 2 ;;
    --skills)
      SKILLS_CSV="$2"; shift 2 ;;
    --with-skill)
      WITH_SKILL=1; shift ;;
    --without-skill)
      WITH_SKILL=0; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 1 ;;
  esac
done

if [[ -n "$REPO_URL" && -n "$REPO_PATH" ]]; then
  echo "Use at most one of --repo-url or --repo-path." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHITECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_ROOT="$ARCHITECT_ROOT/skills"

timestamp="$(date +%Y%m%d-%H%M%S)-$RANDOM"
if [[ -n "$RUN_NAME_SUFFIX" ]]; then
  SAFE_SUFFIX="$(printf '%s' "$RUN_NAME_SUFFIX" | tr '[:space:]' '-' | tr -cd '[:alnum:]_.-')"
  SAFE_SUFFIX="${SAFE_SUFFIX#-}"
  SAFE_SUFFIX="${SAFE_SUFFIX%-}"
  if [[ -z "$SAFE_SUFFIX" ]]; then
    echo "Invalid --name value: '$RUN_NAME_SUFFIX'" >&2
    echo "Use letters, numbers, dot, underscore, or dash." >&2
    exit 1
  fi
  RUN_DIR="$RUN_ROOT/run-$timestamp-$SAFE_SUFFIX"
else
  RUN_DIR="$RUN_ROOT/run-$timestamp"
fi
if [[ -e "$RUN_DIR" ]]; then
  echo "Run dir already exists: $RUN_DIR" >&2
  exit 1
fi
mkdir -p "$RUN_DIR"/{skills,repo,out,home/.claude/skills}

if (( WITH_SKILL )); then
  # Copy shared references used by multiple skills (e.g., architecture-contract.md)
  if [[ -d "$SKILLS_ROOT/references" ]]; then
    cp -R "$SKILLS_ROOT/references" "$RUN_DIR/skills/references"
  fi

  IFS=',' read -r -a SKILLS <<< "$SKILLS_CSV"
  for s in "${SKILLS[@]}"; do
    src="$SKILLS_ROOT/$s"
    dst="$RUN_DIR/skills/$s"
    if [[ ! -d "$src" ]]; then
      echo "Skill not found: $src" >&2
      exit 1
    fi
    cp -R "$src" "$dst"
    ln -sfn "$RUN_DIR/skills/$s" "$RUN_DIR/home/.claude/skills/$s"
  done
fi

if [[ -n "$REPO_URL" ]]; then
  git clone "$REPO_URL" "$RUN_DIR/repo"
elif [[ -n "$REPO_PATH" ]]; then
  if [[ ! -d "$REPO_PATH" ]]; then
    echo "Repo path not found: $REPO_PATH" >&2
    exit 1
  fi
  cp -a "$REPO_PATH"/. "$RUN_DIR/repo/"
else
  cat > "$RUN_DIR/repo/README.md" <<'EOF'
No repo was provided for this run.

This is intentional for plan-only/manual evals (e.g., testing architect-plan).
EOF
fi

if (( WITH_SKILL )); then
  MODE="with-skill"
else
  MODE="without-skill"
fi

cat <<EOF
✅ Isolated manual eval ready:

Mode:      $MODE
Run dir:   $RUN_DIR
Repo dir:  $RUN_DIR/repo
Skills:    $RUN_DIR/skills
HOME:      $RUN_DIR/home

Start Claude in isolation:
  cd "$RUN_DIR/repo"
  HOME="$RUN_DIR/home" claude

(Everything is isolated to this run folder; no access to architect/ ancestor files.)
EOF
