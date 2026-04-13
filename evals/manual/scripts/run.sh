#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
RUNS_ROOT="$REPO_ROOT/evals/manual/runs"
VERIFY_SCRIPT="$SCRIPT_DIR/verify-isolation.sh"

usage() {
  cat <<'EOF'
Usage:
  run.sh <run-id|run-path> [--image <container-image>] [--workdir /workspace/repo]
         [--no-verify] [--] [agent command...]

Examples:
  run.sh run-001 --image ghcr.io/your/agent:latest
  run.sh run-001 --image ghcr.io/your/agent:latest -- claude
  run.sh run-001 --image ghcr.io/your/agent:latest -- bash

Notes:
- Strict isolation is achieved by mounting ONLY the run directory at /workspace.
- HOME is set to /workspace/home so only per-run skills are visible.
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

if [[ "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  exit 0
fi

RUN_ARG="$1"; shift

IMAGE="${MANUAL_EVAL_IMAGE:-}"
WORKDIR="/workspace/repo"
DO_VERIFY=1
CMD=("claude")

while [[ $# -gt 0 ]]; do
  case "$1" in
    --image)
      IMAGE="$2"; shift 2 ;;
    --workdir)
      WORKDIR="$2"; shift 2 ;;
    --no-verify)
      DO_VERIFY=0; shift ;;
    --)
      shift
      if [[ $# -gt 0 ]]; then
        CMD=("$@")
      fi
      break ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 1 ;;
  esac
done

if [[ -d "$RUN_ARG" ]]; then
  RUN_DIR="$RUN_ARG"
else
  RUN_DIR="$RUNS_ROOT/$RUN_ARG"
fi

[[ -d "$RUN_DIR" ]] || { echo "Run not found: $RUN_DIR" >&2; exit 1; }

if (( DO_VERIFY )); then
  "$VERIFY_SCRIPT" "$RUN_DIR"
fi

if [[ -z "$IMAGE" ]]; then
  echo "Missing container image. Pass --image or set MANUAL_EVAL_IMAGE." >&2
  exit 1
fi

if command -v docker >/dev/null 2>&1; then
  RUNTIME="docker"
elif command -v podman >/dev/null 2>&1; then
  RUNTIME="podman"
else
  echo "Neither docker nor podman found." >&2
  exit 1
fi

ENV_ARGS=()
for v in ANTHROPIC_API_KEY OPENAI_API_KEY OPENROUTER_API_KEY CLAUDE_CODE_OAUTH_TOKEN; do
  if [[ -n "${!v:-}" ]]; then
    ENV_ARGS+=("-e" "$v=${!v}")
  fi
done

exec "$RUNTIME" run --rm -it \
  -v "$RUN_DIR:/workspace" \
  -w "$WORKDIR" \
  -e HOME=/workspace/home \
  "${ENV_ARGS[@]}" \
  "$IMAGE" \
  "${CMD[@]}"
