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
  - `architect-discover` — infer architecture from a repository
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

- `diagram.html` (primary interactive diagram)
- optional `diagram-prompt.md` (secondary upload bundle, generated separately via `architect-diagram-prompt`)

Always treat `skills/references/architecture-contract.md` as source of truth.

---

## How to run skills (OpenClaw)

In chat with the agent, use skill commands like:

- `/architect-plan ...`
- `/architect-discover ...`
- `/architect-diagram ...`
- `/architect-diagram-prompt ...`
- `/run-plan-eval ...`
- `/run-architecture-eval ...`

Typical workflow:

1. Run `architect-plan` or `architect-discover`
2. Let that skill automatically hand off to `architect-diagram` to generate `diagram.html`
3. Run `architect-diagram` directly only when you want diagram-only regeneration from existing artifacts
4. Run `architect-diagram-prompt` only if you explicitly need `diagram-prompt.md`

---

## Local scripts

### 1) Isolated manual eval run

```bash
./scripts/new-manual-eval.sh --repo-url <git-url> [--name <run-name>]
```

Creates an isolated run directory and launches Claude in plan mode.

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

### 3) Claude handoff comment loop (primary mode)

Architect now treats **Claude handoff** as the primary comment-update path.

The blessed local launch/setup is documented here:

- `skills/architect-diagram/channels/architect-comments/README.md`

Recommended shape:

1. start Claude with the Architect development channel enabled
2. run the bridge with `--claude-channel-url ... --channel-handoff-only`
3. submit comments from `diagram.html`
4. let Claude own the update loop, progress reporting, validation, and rerender

There is an in-repo development channel server for this flow:

- server code: `skills/architect-diagram/channels/architect-comments/`
- usage notes: `skills/architect-diagram/channels/architect-comments/README.md`

The intended handoff flow is:

1. `diagram.html` submits one batched comment payload to the localhost bridge
2. the bridge persists a file-backed job and acknowledges receipt
3. the bridge forwards the batch into the active Claude session as a `<channel ...>` event
4. Claude uses `update_feedback_status` to stream real progress back to the browser
5. Claude uses `finalize_feedback_update` to validate artifacts, rerender `diagram.html`, and validate the regenerated HTML before completion
6. the user refreshes the same `diagram.html` file to see the updated diagram

This keeps the browser/job contract stable while making the user's live Claude session the orchestrator of the comment-update loop.

### 4) Live comment feedback bridge (fallback deterministic worker)

Run the localhost bridge used by `diagram.html` comment submission:

```bash
python3 skills/architect-diagram/scripts/comment_feedback_bridge.py
```

Default bind:

- `http://127.0.0.1:8765`

What it does:

- accepts one batched comment payload per submit
- writes file-backed jobs under `<output-root>/feedback-jobs/`
- acknowledges receipt immediately in the bridge terminal
- if you do **not** run Claude handoff mode, it can run the built-in deterministic updater as a fallback
- rewrites the same `<output-root>/diagram.html` path in place

Browser behavior:

- submit comments from `diagram.html`
- watch status in the HTML banner and the bridge terminal
- refresh the same `diagram.html` file when the UI says the update is ready
- submitted comments clear after a successful submit and are gone again on refresh

Important:

- `diagram.html` embeds the bridge URL at render time
- default embedded bridge URL is `http://127.0.0.1:8765`
- if you run the bridge on a different port, either rerender `diagram.html` with `--feedback-bridge-url <url>` or restart the bridge on the embedded port

---

## Running evals

Use the eval skills from chat:

- `run-plan-eval`: focuses on planning artifact quality
- `run-architecture-eval`: full discover -> diagram -> review loop

Eval outputs are written under `evals/architect-discover/` and related folders.

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
- Generate that only when requested via `architect-diagram-prompt`.
