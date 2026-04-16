# STATE

Last updated: 2026-04-16

## Current Objective

Make rich SVG fragment generation generic enough to support both planning and discovery outputs on arbitrary repos.

## Current Phase

Diagram renderer generalization

## Current Task

- [x] Replace the DocSign-only SVG fragment generator with a generic rich layout pipeline

### Current Task Details

- **Goal**: Make rich fragment generation work on arbitrary architecture artifacts instead of only the fixed DocSign sample.
- **Why now**: The Rundler eval proved the real blocker was the fragment generator, not Discover itself.
- **Files in play**:
  - `skills/architect-diagram/scripts/generate-svg-fragments.py`
  - `skills/architect-diagram/scripts/render-diagram-html.py`
  - `evals/architect-discover/round7_rundler/diagram-svg/`
  - `evals/architect-discover/round7_rundler/diagram.html`
  - `evals/manual-docsign-tests/run-003/diagram-svg/`
  - `evals/manual-docsign-tests/diagram-3.html`
  - `STATE.md`
  - `DECISIONS.md`
- **Constraints**:
  - Preserve the separation of responsibilities between discover and diagram skills.
  - Do not revert unrelated local changes in diagram artifacts/templates.
  - Keep interactivity metadata intact (`data-element-id`, `data-relationship-id`).
- **Acceptance Criteria**:
  - [x] `generate-svg-fragments.py` no longer depends on DocSign-specific element IDs.
  - [x] Rich fragments are emitted for `system_context`, `container`, `component`, and `deployment` views.
  - [x] Rundler rich fragments render successfully in demo mode.
  - [x] DocSign planning harness still passes with the new generator.
  - [x] Rendered diagrams validate after the change.
- **Status**: Ready for Review

## Blockers / Open Questions

- No functional blockers currently. Visual polish has not yet been reviewed manually in a browser.

## Up Next

- [ ] Visually inspect Rundler and DocSign fragment outputs and tune heuristics where the new generic layout still looks stiff
- [ ] Decide whether to add diagram hint fields to the artifact contract for stronger layout control on difficult repos

## Completed

- [x] Read `README.md`, `skills/references/architecture-contract.md`, and the relevant skill files
- [x] Ran the baseline regression and captured the current failure mode
- [x] Updated discover skill guidance and agent prompt to auto-handoff to `architect-diagram`
- [x] Fixed the diagram generator f-string syntax error
- [x] Reran `./scripts/run-docsign-test.sh` successfully and generated `diagram-1.html`
- [x] Initialized `evals/repos/rundler` and updated it to latest `origin/main`
- [x] Generated `round7_rundler` architecture artifacts, diagram, prompt bundle, review, scores, and reflections
- [x] Verified that `diagram.html` validates
- [x] Identified the remaining arbitrary-repo fragment-renderer regression in `generate-svg-fragments.py`
- [x] Replaced the hardcoded fragment generator with a generic scene/layout pipeline
- [x] Verified rich fragment generation and demo-mode rendering on `round7_rundler`
- [x] Reran `./scripts/run-docsign-test.sh` successfully and generated `diagram-3.html`

## Notes for Next Session

There are pre-existing local edits in `evals/architect-discover/round6_vegeta/diagram.html`, `skills/architect-diagram/templates/diagram-app.html`, and `tmp-sample-review.html`. Work around them rather than reverting them. The current fragment generator is now generic, but it still uses heuristic layout rather than contract-level layout hints, so the next likely iteration is visual tuning rather than functional unblocking.
