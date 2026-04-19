#!/usr/bin/env bash
set -euo pipefail

ROOT="${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT is required}"
DATA="${CLAUDE_PLUGIN_DATA:?CLAUDE_PLUGIN_DATA is required}"
PORT="${ARCHITECT_BRIDGE_PORT:-8765}"
BIND="${ARCHITECT_BRIDGE_BIND:-127.0.0.1}"

if command -v lsof >/dev/null 2>&1; then
  port_owner="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -Fpctn 2>/dev/null || true)"
  if [[ -n "$port_owner" ]]; then
    owner_cmd=""
    owner_pid=""
    owner_name=""
    owner_type=""
    while IFS= read -r line; do
      [[ -z "$line" ]] && continue
      tag="${line:0:1}"
      value="${line:1}"
      case "$tag" in
        c) [[ -z "$owner_cmd" ]] && owner_cmd="$value" ;;
        p) [[ -z "$owner_pid" ]] && owner_pid="$value" ;;
        n) [[ -z "$owner_name" ]] && owner_name="$value" ;;
        t) [[ -z "$owner_type" ]] && owner_type="$value" ;;
      esac
    done <<< "$port_owner"
    owner_summary="$owner_cmd"
    [[ -n "$owner_pid" ]] && owner_summary="${owner_summary:+$owner_summary, }pid=$owner_pid"
    [[ -n "$owner_name" ]] && owner_summary="${owner_summary:+$owner_summary, }$owner_name"
    [[ -n "$owner_type" ]] && owner_summary="${owner_summary:+$owner_summary, }$owner_type"
    printf '[architect-plugin] fatal {"error":"bridge port %s on %s is already in use","hint":"Stop the other Architect runtime and restart Claude. Example: pkill -f architect_runtime.cjs","owner":"%s"}\n' "$PORT" "$BIND" "$owner_summary" >&2
    exit 1
  fi
fi

bash "$ROOT/scripts/bootstrap-runtime.sh"

export NODE_PATH="$DATA/node_modules${NODE_PATH:+:$NODE_PATH}"

exec node "$ROOT/runtime/architect_runtime.cjs"
