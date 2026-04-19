# STATE

Last updated: 2026-04-19

## Current Objective

Package the Claude handoff path as a real plugin so end users can run Architect through Claude with a plugin-owned runtime instead of manually starting bridge and channel processes.

## Current Phase

Claude plugin packaging

## Current Task

- [ ] Validate and harden the marketplace-backed installed-plugin flow in real Claude sessions

### Current Task Details

- **Goal**: Ship and verify an installable Claude plugin bundle that owns the browser bridge, channel delivery, and finalize/status tools while preserving rich diagram quality during comment-driven updates.
- **Why now**: The plugin runtime, marketplace packaging, and comment-loop hardening are in place. The main remaining risk is reliability in real end-to-end Claude sessions, not missing core architecture.
- **Files in play**:
  - `.claude-plugin/marketplace.json`
  - `claude-plugin/architect/`
  - `docs/plugin-publish.md`
  - `scripts/new-manual-eval.sh`
  - `scripts/publish-plugin.sh`
  - `scripts/sync-claude-plugin.py`
  - `skills/architect-diagram/scripts/render-diagram-html.py`
  - `skills/architect-diagram/scripts/generate-svg-fragments.py`
  - `skills/architect-diagram/templates/diagram-app.html`
- **Constraints**:
  - Keep `diagram.html` as a single-file artifact with inline CSS/JS plus the approved Instrument Sans font exception
  - Preserve the richer diagram shell and SVG polish that landed on `main`; plugin work must not regress those UI improvements
  - Claude CLI is the only committed host target for this phase
  - Keep the installed-plugin marketplace identity as the canonical dev/test path for plugin channel delivery
  - Preserve the original diagram render profile and view set during comment-driven rerenders
- **Acceptance Criteria**:
  - [x] Add a repo-local Claude plugin root with manifest, runtime bootstrap, and a unified runtime server
  - [x] Mirror the shipping Architect skills, templates, references, and required scripts into the plugin bundle
  - [x] Validate the plugin-owned runtime bootstrap and browser endpoints locally
  - [x] Add a repo-local development marketplace so Claude can address the plugin channel as `plugin:architect@architect-local`
  - [x] Update `scripts/new-manual-eval.sh` to snapshot the plugin, create a run-local marketplace id, install the plugin locally for that run, and launch Claude with the correct plugin-qualified development channel flag
  - [x] Restore the explicit Architect channel handoff system prompt in the plugin launcher path so Claude reliably reacts to inbound comment events
  - [x] Harden the live comment loop so unacknowledged jobs auto-fail instead of leaving the diagram stuck in `received`
  - [x] Make cold-start MCP connects reliable without requiring a manual reconnect after Claude launches
  - [x] Preserve the original diagram quality and view set during comment-driven rerenders instead of silently downgrading rich/demo outputs to fast mode
  - [x] Add a repo-root GitHub marketplace catalog for public installation via `architect@plugins`
  - [x] Define a repeatable publish workflow that syncs, validates, and checks marketplace metadata before push
  - [ ] Validate the marketplace-backed installed-plugin flow in a fresh real Claude session with multiple live comment rounds
- **Status**: In Progress

## Blockers / Open Questions

- We still need one clean fresh-run validation pass using the installed plugin identity, not an older run directory with stale snapshots.
- We still need one clean fresh-run validation pass using the GitHub marketplace identity (`architect@plugins`), not only the local-dev marketplace.
- Cold-start latency is now reliable but still not optimized; we have not decided whether official-marketplace distribution needs prebundled deps instead of bootstrap-on-launch.
- Claude desktop remains unvalidated. CLI is still the only committed host target.
- The plugin channel `instructions` alone were not sufficient in one real no-append test run: the feedback job stayed unacknowledged and auto-failed with `agent_ack_timeout`.

## Up Next

- [ ] Dogfood the unified sidebar status card in a fresh plugin session and confirm the 4-second success auto-refresh feels right
- [ ] Run one fresh end-to-end Claude session with the installed marketplace plugin identity and multiple comment rounds
- [ ] Validate `claude plugin marketplace add willhennessy/architect` and `claude plugin install architect@plugins` from outside this repo
- [ ] Verify the unacknowledged-job timeout behaves well in a fresh plugin session without false positives
- [ ] Add regression coverage for the new canvas-comment path and cursor-priority behavior
- [ ] Add regression coverage for the stale-SVG bug and the render-profile-preservation bug
- [ ] Validate the new `architecture/diagram.html` user-facing packaging in one fresh plugin session
- [ ] Decide whether to keep the legacy bare bridge/channel docs at all or move them fully into dev-only notes

## Completed

- [x] Moved comment processing status into the sidebar, kept submitted drafts visible through pending and failure, and restyled comment cards around the shared kind-color mapping
- [x] Removed the plugin MCP cold-start race by moving runtime bootstrap onto the MCP launch path instead of a separate `SessionStart` hook
- [x] Added a repo-root GitHub marketplace catalog (`plugins`) and a repeatable `scripts/publish-plugin.sh` workflow for public distribution
- [x] Fixed stale SVG reuse so comment-driven YAML edits cannot leave node labels out of sync with the details panel
- [x] Fixed comment-update rerenders so rich diagrams keep their component views and regenerated SVG-backed visuals after small edits
- [x] Moved the visible diagram artifact packaging under `architecture/diagram.html` while hiding render/comment sidecars under `architecture/.out/`

## Notes for Next Session

The active control plane is the plugin bundle at `claude-plugin/architect/`, the public GitHub marketplace catalog at `.claude-plugin/marketplace.json`, and the repo-local development marketplace at `claude-plugin/.claude-plugin/marketplace.json`. `scripts/sync-claude-plugin.py` rebuilds the plugin-local mirrors from the source skills/scripts after any shipped-file change, and `scripts/publish-plugin.sh` is now the repeatable publish gate for agents: clean `main`, sync, validate, verify marketplace metadata, then stop for human review/push. The runtime now bootstraps Node/Python dependencies on the MCP launch path itself, then serves the browser bridge on port `8765` while also exposing the Claude channel tools. The critical Claude Channels lesson is that live plugin-channel testing must use the installed marketplace identity, not `--plugin-dir`; Claude will skip channel notifications if the requested channel identity is marketplace-installed but the loaded plugin is `inline`. The runtime now auto-fails unacknowledged `received` jobs after about 20 seconds so the HTML app unlocks without manual status surgery. Rich comment updates preserve the current diagram render profile and regenerate SVG fragments when needed, and SVG fragment reuse is now revision-keyed via `architecture/.out/diagram-svg/_metadata.json`. The visible artifact package is now `architecture/`: user-facing docs and render outputs should point to `architecture/diagram.html` and `architecture/diagram-prompt.md`, while hidden sidecars live under `architecture/.out/`. The live repo now uses `architect-init` as the canonical repo-derived architecture skill name, with `/architect:init` as the documented plugin command. Public install docs now assume `claude plugin marketplace add willhennessy/architect` followed by `claude plugin install architect@plugins`; the local `architect-local` marketplace remains for unpublished dev testing only. A real no-append validation run against `evals/manual-docsign-tests/run-003` failed with `agent_ack_timeout`, so both public docs and the internal eval launcher should keep the explicit Architect channel system prompt until we find a plugin-native replacement that is equally reliable. `diagram-app.html` now supports view-level comments anywhere on the canvas, titles those comments from the active breadcrumb label, and applies cursor precedence from the canvas surface outward so comment mode stays crosshair-first. Feedback batch channel copy is now intentionally a single friendly line (`Got it, let me noodle on these N comments.` for multi-comment batches), and the detailed job/comment context is carried in channel metadata (`bridge_url`, `output_root`, `diagram_revision_id`, `comments_json`, `comments_summary`). New Claude sessions should use the updated prompt text so Claude treats that channel line as the acknowledgment instead of posting a second chat ack. The diagram app now auto-reloads once per job when it sees a final `completed` status with `has_final_result=true`, which keeps the comment loop hands-off without reloading on intermediate `fast_patch_ready` states.

The comment sidebar now owns the full batch lifecycle: pending uses a neutral in-sidebar status card, success stays visible for about four seconds before the automatic reload, failure keeps the submitted drafts in place with `Retry` and `Details`, and comment target dots still come from the shared `colorForKind` mapping instead of a sidebar-only palette. `diagram-38.html` is the latest validated DocSign regression artifact for this UI pass.
