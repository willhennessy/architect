# STATE

Last updated: 2026-04-18

## Current Objective

Tighten the diagram review shell so Explore and Comment are explicit, mode-aware workflows.

## Current Phase

Inline comment popover polish

## Current Task

- [x] Polish the inline comment popover so it behaves like a proper annotation UI

### Current Task Details

- **Goal**: Keep the comment popover spatially tied to its target, make draft dismissal safer, and tighten the popover’s visual hierarchy in both light and dark mode.
- **Why now**: The first floating composer solved the full-screen modal problem, but it still covered targets, lacked a clear target indicator, and behaved more like a generic modal than an inline annotation tool.
- **Files in play**:
  - `STATE.md`
  - `skills/architect-diagram/templates/diagram-app.html`
- **Constraints**:
  - Do not add React; keep the implementation in the existing template JS/CSS
  - Use existing theme tokens in both light and dark mode
  - Keep the popover inside the diagram bounds instead of borrowing room from the sidebar
  - Preserve the production render/validate path by verifying with `./scripts/run-docsign-test.sh`
  - Produce the requested verification screenshots from generated output
- **Acceptance Criteria**:
  - [x] The popover sits adjacent to the target with a pointer tail and no longer obscures the commented node
  - [x] The active target stays visually highlighted while the popover is open
  - [x] The popover width is constrained and the footer is simplified to a single `Add` action with keyboard hint
  - [x] Empty popovers dismiss immediately, draft popovers require a second dismissal action, clicking a different diagram element retargets the composer, and `Cmd/Ctrl+Enter` submits
  - [x] Verified against `diagram-4.html` with four screenshots plus scripted behavior checks
- **Status**: Ready for Review

## Blockers / Open Questions

- None.

## Up Next

- [ ] Decide whether relationship comments need a richer persistent target treatment than the current stroke highlight
- [ ] Consider extracting the Playwright verification script into a reusable UI regression helper
- [ ] If visual polish continues, evaluate whether the pointer tail wants a slightly softer shadow treatment

## Completed

- [x] Swapped the Explore-mode shortcut from `V` to `E` in the UI and key handler, then verified `diagram-10.html`
- [x] Simplified the popover header to the element name, renamed the primary action to `Add`, and set the empty-state input-to-button gap to 12px, then verified `diagram-9.html`
- [x] Clicking a different diagram element while the comment popover is open now retargets the composer to that element, then verified `diagram-8.html`
- [x] Fixed the inline comment popover tail so relationship comments anchor to the clicked segment and the pointer orientation follows the final on-screen geometry, then verified `diagram-7.html`
- [x] Polished the inline comment popover with smart side-aware placement inside the diagram bounds, a pointer tail, target highlighting, safer draft dismissal, and keyboard-hinted `Comment` submit, then verified `diagram-4.html`
- [x] Replaced the centered Comment Mode modal with a click-anchored floating composer for nodes and edges, then removed the anchor drift so the dialog opens at the actual click point and verified `diagram-2.html`

## Notes for Next Session

`diagram-app.html` still owns the entire review shell without React, but the comment composer now behaves like an inline annotation popover instead of a click-point modal. Positioning is target-relative and constrained to the `.canvas-wrap` bounds, not the full viewport, so nodes near the right edge of the diagram flip the popover left instead of borrowing space from the sidebar. The popover now includes a small pointer tail, a narrowed 340px width, a header that shows only the element name, a single `Add` button with dynamic `⌘↵` / `Ctrl+↵` hint, an Explore shortcut of `E`, and an empty-state input-to-button gap controlled by a 12px footer margin instead of leftover textarea/hint spacing. Active node targets get an SVG ring overlay with a short pulse; relationship targets use a stroke highlight. Relationship-tail placement now anchors to the actual click point instead of the whole edge-group bounding box, and the pointer edge is derived from the final clamped popover geometry so it keeps facing the target after bounds adjustments. Clicking a different diagram element beneath the overlay now immediately retargets the composer to that element instead of being ignored. Latest production verification used `./scripts/run-docsign-test.sh`, which wrote `evals/manual-docsign-tests/diagram-10.html`; the earlier inline-comment screenshot set remains under `evals/manual-docsign-tests/screenshots-diagram-4-inline-comment-polish/` (`light-left-edge.png`, `light-right-edge.png`, `dark-ring-visible.png`, `dark-populated-shortcut.png`) with `verification.json`.
