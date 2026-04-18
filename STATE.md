# STATE

Last updated: 2026-04-17

## Current Objective

Tighten the diagram review shell so Explore and Comment are explicit, mode-aware workflows.

## Current Phase

Diagram comment UX refinement

## Current Task

- [x] Refactor `diagram.html` into explicit Explore and Comment modes

### Current Task Details

- **Goal**: Replace the one-off comment toggle with a persisted two-mode shell and a sidebar that changes meaning with the active mode.
- **Why now**: Review/commenting has outgrown the old top-toolbar toggle. The current chrome splits comment context across a banner, queue bar, and details panel, which makes the primary review flows feel muddled.
- **Files in play**:
  - `STATE.md`
  - `DECISIONS.md`
  - `skills/architect-diagram/templates/diagram-app.html`
- **Constraints**:
  - Use existing theme tokens only; do not introduce new hard-coded chrome colors
  - Keep Explore and Comment keyboard-accessible (`V` / `C`) and persist mode in `localStorage`
  - Preserve the production render/validate path by verifying with `./scripts/run-docsign-test.sh`
- **Acceptance Criteria**:
  - [x] Add a centered Explore/Comment segmented control with inline icons, active signal styling, and `V` / `C` shortcuts
  - [x] Make the right sidebar mode-aware: component details in Explore, comment list plus sticky submit footer in Comment
  - [x] Remove the old comment toggle/banner/queue chrome and verify the production HTML plus light/dark screenshot states
- **Status**: Ready for Review

## Blockers / Open Questions

- The dedicated Explore icon is now wired in from `/Users/will/Downloads/location-arrow.svg`, but the final Comment-mode icon was not provided in this session. The toggle currently reuses the existing inline comment glyph.
- Screenshot/interaction verification used generated driver HTML under `evals/manual-docsign-tests/` plus headless Chrome/CDP. Decide later whether that deserves a first-class reusable harness or should stay ad hoc.

## Up Next

- [ ] Swap in the dedicated Comment icon if design provides a new SVG
- [ ] Decide whether mode-toggle screenshot automation should become a reusable UI regression harness
- [ ] Polish the stacked/mobile sidebar behavior if diagram review on smaller screens becomes a priority

## Completed

- [x] Refactored the Explore details sidebar so Kind renders as a color-mapped subtitle, Confidence is inline metadata, Tags stay chips, and relationships resolve to human names without duplicate cards
- [x] Fixed the sidebar viewport-height regression by pinning `.workspace` to the final `1fr` grid row instead of letting hidden toolbar auto-placement collapse it
- [x] Replaced the old `Comment (C)` toolbar toggle with persisted Explore/Comment modes, a mode-aware sidebar, and a sidebar-owned submit flow in `diagram-app.html`
- [x] Fixed the dark-mode Pattern C regression plus modal polish in `diagram-app.html`, and verified `diagram-20.html` with fresh light/dark screenshots
- [x] Applied the warm-neutral light/dark design system to `diagram-app.html` and `generate-svg-fragments.py`, including a persisted theme toggle and tokenized SVG output
- [x] Polished diagram rendering so authored SVGs stay bounded on large screens and header rows read lighter, tighter, and transparent

## Notes for Next Session

`diagram-app.html` now treats review mode as first-class state via `localStorage['viewMode']`. Explore is the default, Comment is explicit, and the right sidebar is always present: component details in Explore, comment cards plus sticky submit footer in Comment. Inside the Explore sidebar, Kind is now a small color-mapped subtitle under the component title, Confidence is rendered as inline label/value metadata, Tags are the only remaining chip treatment, and relationship cards resolve source/target display names from the element model instead of showing raw slugs. Duplicate relationship cards caused by aggregating view-level edges were fixed by deduping against the canonical relationship map plus a signature-level sidebar filter. The viewport-height regression was fixed by pinning `.topbar`, `.tabbar`, `.toolbar`, and `.workspace` to explicit grid rows so `.workspace` always occupies the stretch row. Keep overwriting `evals/manual-docsign-tests/diagram-10.html` for iterative diagram tweaks; the current light/dark selected-component screenshots live under `evals/manual-docsign-tests/screenshots-diagram-10-details/`. The current Comment toggle uses the old inline comment icon until a dedicated asset arrives.
