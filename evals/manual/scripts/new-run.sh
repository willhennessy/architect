#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
MANUAL_ROOT="$REPO_ROOT/evals/manual"
RUNS_ROOT="$MANUAL_ROOT/runs"

DEFAULT_SKILLS=(
  architect-plan
  architect-discover
  architect-diagram
  run-architecture-eval
  run-plan-eval
)

usage() {
  cat <<'EOF'
Usage:
  new-run.sh [--run-id run-001] [--repo-source /path/to/repo | --repo-submodule name]
             [--skill <name> ...] [--all-skills] [--empty-repo]

Options:
  --run-id <id>           Explicit run id (default: next run-XXX)
  --repo-source <path>    Copy repo snapshot from local path into run/repo
  --repo-submodule <name> Copy from evals/repos/<name>
  --skill <name>          Include one skill (repeatable)
  --all-skills            Include every directory under repo-root/skills
  --empty-repo            Do not copy any repo (create empty repo dir)
  -h, --help              Show this help
EOF
}

RUN_ID=""
REPO_SOURCE=""
USE_ALL_SKILLS=0
EMPTY_REPO=0
SKILLS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-id)
      RUN_ID="$2"; shift 2 ;;
    --repo-source)
      REPO_SOURCE="$2"; shift 2 ;;
    --repo-submodule)
      REPO_SOURCE="$REPO_ROOT/evals/repos/$2"; shift 2 ;;
    --skill)
      SKILLS+=("$2"); shift 2 ;;
    --all-skills)
      USE_ALL_SKILLS=1; shift ;;
    --empty-repo)
      EMPTY_REPO=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 1 ;;
  esac
done

mkdir -p "$RUNS_ROOT"

if [[ -z "$RUN_ID" ]]; then
  max=0
  shopt -s nullglob
  for d in "$RUNS_ROOT"/run-*; do
    b="$(basename "$d")"
    n="${b#run-}"
    if [[ "$n" =~ ^[0-9]+$ ]]; then
      n10=$((10#$n))
      (( n10 > max )) && max="$n10"
    fi
  done
  shopt -u nullglob
  RUN_ID="run-$(printf '%03d' "$((max + 1))")"
fi

RUN_DIR="$RUNS_ROOT/$RUN_ID"
if [[ -e "$RUN_DIR" ]]; then
  echo "Run already exists: $RUN_DIR" >&2
  exit 1
fi

mkdir -p "$RUN_DIR"/{repo,artifacts,skills,home/.claude/skills,logs}

if (( USE_ALL_SKILLS )); then
  mapfile -t SKILLS < <(find "$REPO_ROOT/skills" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
elif [[ ${#SKILLS[@]} -eq 0 ]]; then
  SKILLS=("${DEFAULT_SKILLS[@]}")
fi

for skill in "${SKILLS[@]}"; do
  src="$REPO_ROOT/skills/$skill"
  dst="$RUN_DIR/skills/$skill"
  if [[ ! -d "$src" ]]; then
    echo "Skill not found: $src" >&2
    exit 1
  fi
  cp -R "$src" "$dst"
  ln -s "../../../skills/$skill" "$RUN_DIR/home/.claude/skills/$skill"
done

if (( EMPTY_REPO )); then
  :
elif [[ -n "$REPO_SOURCE" ]]; then
  if [[ ! -d "$REPO_SOURCE" ]]; then
    echo "Repo source not found: $REPO_SOURCE" >&2
    exit 1
  fi
  cp -a "$REPO_SOURCE"/. "$RUN_DIR/repo/"
else
  cat > "$RUN_DIR/repo/README.md" <<'EOF'
Place your repo-under-test files here before running the eval.
EOF
fi

created_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
{
  echo "{" 
  echo "  \"run_id\": \"$RUN_ID\"," 
  echo "  \"created_at_utc\": \"$created_at\"," 
  echo "  \"repo_source\": \"${REPO_SOURCE:-<none>}\"," 
  echo "  \"skills\": ["
  for i in "${!SKILLS[@]}"; do
    comma=","; [[ "$i" -eq "$((${#SKILLS[@]} - 1))" ]] && comma=""
    echo "    \"${SKILLS[$i]}\"$comma"
  done
  echo "  ]"
  echo "}"
} > "$RUN_DIR/run.json"

"$SCRIPT_DIR/verify-isolation.sh" "$RUN_ID"

echo "Created isolated run: $RUN_DIR"
echo "Next:"
echo "  $MANUAL_ROOT/scripts/run.sh $RUN_ID --image <your-agent-image>"
