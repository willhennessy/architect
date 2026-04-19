#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ensure-eval-repo.sh [--repo-url <git-url> | --repo-path <local-path>] [--slug <name>] [--refresh]

Options:
  --repo-url <url>       Clone the repo into evals/repos/<slug>
  --repo-path <path>     Copy a local repo into evals/repos/<slug>
  --slug <name>          Cache directory name (default: derived from repo URL/path)
  --cache-root <path>    Override cache root (default: <repo>/evals/repos)
  --refresh              Fast-forward an existing cached git clone if it is clean
  -h, --help             Show help

Notes:
  - The clone path intentionally does NOT recurse into git submodules.
  - evals/repos/ is a local cache and is ignored by git.
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHITECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

REPO_URL=""
REPO_PATH=""
SLUG=""
CACHE_ROOT="$ARCHITECT_ROOT/evals/repos"
REFRESH=0

normalize_slug() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's#^.*/##; s/\.git$//; s/[^a-z0-9._-]+/-/g; s/^-+//; s/-+$//; s/-+/-/g'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-url)
      REPO_URL="$2"; shift 2 ;;
    --repo-path)
      REPO_PATH="$2"; shift 2 ;;
    --slug|--name)
      SLUG="$2"; shift 2 ;;
    --cache-root)
      CACHE_ROOT="$2"; shift 2 ;;
    --refresh)
      REFRESH=1; shift ;;
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

if [[ -z "$REPO_URL" && -z "$REPO_PATH" ]]; then
  echo "One of --repo-url or --repo-path is required." >&2
  exit 1
fi

if [[ -z "$SLUG" ]]; then
  if [[ -n "$REPO_URL" ]]; then
    SLUG="$(normalize_slug "$REPO_URL")"
  else
    SLUG="$(normalize_slug "$REPO_PATH")"
  fi
fi

if [[ -z "$SLUG" ]]; then
  echo "Could not derive a slug. Pass --slug explicitly." >&2
  exit 1
fi

DEST="$CACHE_ROOT/$SLUG"
mkdir -p "$CACHE_ROOT"

if [[ -e "$DEST" ]]; then
  if [[ ! -d "$DEST/.git" && ! -f "$DEST/.git" ]]; then
    echo "Cache path exists but is not a git repo: $DEST" >&2
    exit 1
  fi

  if (( REFRESH )); then
    if [[ -n "$(git -C "$DEST" status --porcelain)" ]]; then
      echo "Refusing to refresh dirty cached repo: $DEST" >&2
      exit 1
    fi
    current_branch="$(git -C "$DEST" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
    if [[ -z "$current_branch" ]]; then
      echo "Refusing to refresh detached HEAD cache: $DEST" >&2
      exit 1
    fi
    git -C "$DEST" fetch --depth 1 --no-tags origin "$current_branch"
    git -C "$DEST" pull --ff-only --no-rebase --no-recurse-submodules origin "$current_branch"
  fi

  printf '%s\n' "$DEST"
  exit 0
fi

if [[ -n "$REPO_URL" ]]; then
  git clone --depth 1 --single-branch --no-tags --recurse-submodules=no "$REPO_URL" "$DEST"
else
  if [[ ! -d "$REPO_PATH" ]]; then
    echo "Repo path not found: $REPO_PATH" >&2
    exit 1
  fi
  SOURCE_REAL="$(cd "$REPO_PATH" && pwd -P)"
  DEST_REAL="$(cd "$CACHE_ROOT" && pwd -P)/$SLUG"
  case "$DEST_REAL/" in
    "$SOURCE_REAL/"*)
      echo "Refusing to copy a repo into a cache path inside itself: $SOURCE_REAL -> $DEST_REAL" >&2
      exit 1
      ;;
  esac
  mkdir -p "$DEST"
  cp -a "$REPO_PATH"/. "$DEST"/
fi

printf '%s\n' "$DEST"
