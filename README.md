# Architect

Architect is a skill suite for generating, reviewing, and iterating software architecture artifacts and interactive diagrams.

It supports two broad use cases:

1. **Plan-first architecture design** (before implementation)
2. **Repo discovery architecture extraction** (from an existing codebase)

Outputs are standardized and compatible across skills.

---

## What this repo contains

- `skills/` — production skills
  - `architect-plan` — generate architecture from requirements/constraints
  - `architect-init` — infer architecture from a repository
  - `architect-diagram` — render interactive `diagram.html`
  - `architect-diagram-prompt` — generate `diagram-prompt.md` (optional, on-demand)
  - `run-plan-eval` / `run-architecture-eval` — eval orchestration skills
- `skills/references/architecture-contract.md` — canonical artifact schema contract
- `scripts/` — local utility scripts and test harnesses
- `evals/` — eval/test outputs

---

## Core output contract

Most skills ultimately produce or consume this structure under an output root:

- `architecture/manifest.yaml`
- `architecture/model.yaml`
- `architecture/views/*.yaml`
- `architecture/summary.md`
- optional `architecture/diff.yaml` (update mode)

Diagram-related outputs:

- `architecture/diagram.html` (primary interactive diagram)
- optional `architecture/diagram-prompt.md` (secondary upload bundle, generated separately via `architect-diagram-prompt`)
- hidden runtime sidecars under `architecture/.out/` when comment mode or rich rendering is enabled

Always treat `skills/references/architecture-contract.md` as source of truth.

---

## How to run skills

In chat with the agent, use skill commands like:

- `/architect-plan ...`
- `/architect-init ...`
- `/architect-diagram ...`
- `/architect-diagram-prompt ...`
- `/run-plan-eval ...`
- `/run-architecture-eval ...`

Typical workflow:

1. Run `architect-plan` or `architect-init`
2. Let that skill automatically hand off to `architect-diagram` to generate `architecture/diagram.html`
3. Run `architect-diagram` directly only when you want diagram-only regeneration from existing artifacts
4. Run `architect-diagram-prompt` only if you explicitly need `architecture/diagram-prompt.md`

---

## Local scripts

### 1) Isolated manual eval run

```bash
./scripts/new-manual-eval.sh --repo-url <git-url> [--name <run-name>]
```

Creates an isolated run directory and launches Claude in `auto` mode.
When `--with-skill` is used, it also snapshots the Architect plugin, wires a run-local development marketplace, installs `architect@...` locally for that run, and launches Claude with the plugin and development channel enabled.

Useful options:

- `--repo-url` or `--repo-path`
- `--run-root`
- `--name` (also passed as Claude session name)
- `--with-skill` / `--without-skill`

### 2) Fixed DocSign regression test harness

```bash
./scripts/run-docsign-test.sh
```

This uses a fixed prompt and writes outputs under:

- `evals/manual-docsign-tests/run-XXX/`
- numbered diagram copies like `evals/manual-docsign-tests/diagram-<n>.html`

The harness decides whether to regenerate plan artifacts or rerender diagram-only based on whether `architect-plan`-related files changed since previous run.

Helper scripts used by harness:

- `scripts/generate-docsign-plan-artifacts.py`
- `skills/architect-diagram/scripts/generate-svg-fragments.py` (production generator used by harness)

### 3) Claude plugin handoff (primary mode)

Architect now treats the **Claude plugin runtime** as the primary comment-update path.

The blessed local development and packaging path lives here:

- `claude-plugin/architect/README.md`

Recommended shape:

1. sync the plugin bundle with `python3 scripts/sync-claude-plugin.py`
2. add the repo-local development marketplace and install `architect@architect-local`
3. start Claude from the installed plugin identity, not `--plugin-dir`, for live channel testing
4. enable the Architect development channel for that session with `plugin:architect@architect-local`
5. append the Architect channel handoff system prompt so Claude acts on inbound comment events in the same session
   `--append-system-prompt` is required to guarantee Claude responds to comments.
6. run `/architect:init` or `/architect:plan`
7. submit comments from `architecture/diagram.html`
8. let the same Claude session own the update loop, progress reporting, validation, and rerender

The first `/mcp` connect may take a little longer on a cold start because the plugin bootstraps its runtime dependencies during MCP launch, but it should not require a manual reconnect anymore.

The intended handoff flow is:

1. `architecture/diagram.html` submits one batched comment payload to the plugin runtime on `http://127.0.0.1:8765`
2. the runtime persists a file-backed job and acknowledges receipt
3. the runtime forwards the batch into the active Claude session as a `<channel ...>` event
4. Claude uses `update_feedback_status` to stream real progress back to the browser
5. Claude uses `finalize_feedback_update` to validate artifacts, rerender `architecture/diagram.html`, and validate the regenerated HTML before completion
6. the user refreshes the same `architecture/diagram.html` file to see the updated diagram

This keeps the browser/job contract stable while making the user's live Claude session the orchestrator of the comment-update loop, without requiring a separately started bridge process.

### 4) Live comment feedback bridge (legacy fallback / dev path)

Run the localhost bridge used by `architecture/diagram.html` comment submission:

```bash
python3 skills/architect-diagram/scripts/comment_feedback_bridge.py
```

Default bind:

- `http://127.0.0.1:8765`

What it does:

- accepts one batched comment payload per submit
- writes file-backed jobs under `<output-root>/architecture/.out/feedback-jobs/`
- acknowledges receipt immediately in the bridge terminal
- if you do **not** run Claude handoff mode, it can run the built-in deterministic updater as a fallback
- rewrites the same `<output-root>/architecture/diagram.html` path in place

Use this path for repo-level development or fallback testing. It is no longer the primary operator story.

Browser behavior:

- submit comments from `architecture/diagram.html`
- watch status in the HTML banner and the bridge terminal
- refresh the same `architecture/diagram.html` file when the UI says the update is ready
- submitted comments clear after a successful submit and are gone again on refresh

Important:

- `architecture/diagram.html` embeds the bridge URL at render time
- default embedded bridge URL is `http://127.0.0.1:8765`
- if you run the bridge on a different port, either rerender `architecture/diagram.html` with `--feedback-bridge-url <url>` or restart the bridge on the embedded port

---

## Running evals

Use the eval skills from chat:

- `run-plan-eval`: focuses on planning artifact quality
- `run-architecture-eval`: full discover -> diagram -> review loop

Eval outputs are written under `evals/architect-init/` and related folders. Historical rounds remain in the archived eval outputs.

---

## Development guidance

- Keep plan/discover outputs aligned to the contract.
- Keep IDs stable across revisions when concepts are unchanged.
- If working on diagrams, validate output with the diagram validator in the diagram skill scripts before calling work done.
- Prefer changing skill references/contracts first, then templates/scripts.
- Keep test/prod behavior aligned (avoid harness-only behavior that does not exist in real skill flow).

---

## Quick start for a new contributor

1. Read:
   - `README.md`
   - `AGENTS.md`
   - `skills/references/architecture-contract.md`
2. Run one baseline test:

```bash
./scripts/run-docsign-test.sh
```

3. Open generated diagram:

- `evals/manual-docsign-tests/diagram-<n>.html`

4. Make a focused change and rerun the same harness.

---

## Notes

- `architect-diagram` intentionally does **not** generate `diagram-prompt.md` by default.
- Generate that only when requested via `architect-diagram-prompt`, and expect it at `architecture/diagram-prompt.md`.
