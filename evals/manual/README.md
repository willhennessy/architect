# Manual Eval Harness (Isolated Runs)

Use this harness to run manual skill evals in **strict isolation**.

Isolation goal:
- Each run can only see files inside its own run folder.
- No visibility into other eval runs.
- No visibility into ancestor repo files (for example `CLAUDE.md` at repo root).

## Layout

- `scripts/new-run.sh` — create a new isolated run workspace
- `scripts/verify-isolation.sh` — verify symlinks and run layout are hermetic
- `scripts/run.sh` — launch the agent inside a container with only the run folder mounted
- `runs/run-XXX/` — per-run workspace (ignored by git)

Per-run workspace shape:

- `repo/` — repo-under-test snapshot for this run only
- `skills/` — copied skill snapshots under test (not shared)
- `home/.claude/skills/` — skill links scoped to this run
- `artifacts/` — outputs produced during the run
- `logs/` — optional logs

## Quick start

```bash
cd evals/manual
./scripts/new-run.sh --repo-submodule rundler
./scripts/run.sh run-001 --image <your-agent-image>
```

If your source repo is outside `evals/repos`:

```bash
./scripts/new-run.sh --repo-source /absolute/path/to/repo
```

## Notes

- `new-run.sh` copies skill directories into each run so runs are reproducible and isolated.
- `run.sh` enforces containerized execution and mounts only that run directory at `/workspace`.
- Set `--image` explicitly (or `MANUAL_EVAL_IMAGE`) to your local agent image.
