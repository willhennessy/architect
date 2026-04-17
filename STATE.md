# STATE

Last updated: 2026-04-17

## Current Objective

Ship and document the Claude Channels-based handoff path so the user's active Claude session is the primary orchestrator of architect comment updates.

## Current Phase

Claude Channels productization

## Current Task

- [x] Document the blessed Claude handoff launch/setup path

### Current Task Details

- **Goal**: Turn the validated manual Claude Channels recipe into one canonical, copy-pasteable setup path for future sessions and contributors.
- **Why now**: Claude handoff is now the primary mode. The launch/setup story needs one blessed path so the team does not drift back into experimental flags or conflicting instructions.
- **Files in play**:
  - `STATE.md`
  - `DECISIONS.md`
  - `README.md`
  - `skills/architect-diagram/channels/architect-comments/README.md`
- **Constraints**:
  - Avoid PTY wrapping as the primary adoption path
  - Prefer official supported host surfaces over reverse-engineered ones
  - The user's active coding agent should remain the orchestrator of the architect loop
- **Acceptance Criteria**:
  - [x] Add one explicit “known good” Claude setup section with exact commands
  - [x] Document the required Claude flags and the MCP verification step
  - [x] Document the misleading startup warning so operators do not misread a healthy session as broken
  - [x] Link the blessed path from the root README
- **Status**: Ready for Review

## Blockers / Open Questions

- The manual interactive run succeeded, but the startup text still showed a misleading `no MCP server configured with that name` warning even though `/mcp` showed `architect-comments` connected and Claude received the event. This appears to be a Claude CLI startup quirk and is now documented.
- We now have a full manual end-to-end proof where Claude used both `update_feedback_status` and `finalize_feedback_update` during a real channel-driven update session; the remaining question is whether Claude desktop can ride on the same setup shape or needs separate guidance.
- The repo contract and historical artifacts are not perfectly aligned on enums like `protocol` and `runtime_boundary`, so the validator currently follows real Architect output conventions where needed instead of the narrowest reading of `architecture-contract.md`.

## Up Next

- [ ] Decide whether Claude desktop is supported through the same Claude Code channel setup or remains CLI-only initially
- [ ] Decide whether to expose the finalize flow anywhere outside the Claude channel spike or keep it Claude-only for now
- [ ] Decide whether the bridge CLI should auto-prefer Claude handoff when a channel URL is present, or whether that stays an explicit flag

## Completed

- [x] Fixed the DocSign person-card label alignment regression in `diagram-app.html` and verified `diagram-2.html` in a browser screenshot
- [x] Fixed the dark-mode Pattern C regression plus modal polish in `diagram-app.html`, and verified `diagram-20.html` with fresh light/dark screenshots
- [x] Applied the warm-neutral light/dark design system to `diagram-app.html` and `generate-svg-fragments.py`, including a persisted theme toggle and tokenized SVG output
- [x] Polished diagram rendering so authored SVGs stay bounded on large screens and header rows read lighter, tighter, and transparent
- [x] Documented the blessed Claude handoff launch/setup path with the exact known-good commands and verification steps
- [x] Added `validate-feedback-update.py` plus the `finalize_feedback_update` Claude MCP tool for deterministic validate-render-validate completion
- [x] Added `POST /jobs/:id/status` plus the `update_feedback_status` Claude MCP tool for real-agent status updates

## Notes for Next Session

Claude handoff is now the primary documented mode and the deterministic worker is fallback. The blessed setup lives in `skills/architect-diagram/channels/architect-comments/README.md`: install the channel dependency, write `/tmp/architect-channel-mcp.json`, start the bridge with `--claude-channel-url ... --channel-handoff-only`, then start Claude with `--strict-mcp-config`, `--dangerously-load-development-channels server:architect-comments`, and `--permission-mode auto`. Do not also pass `--channels server:architect-comments`. `/mcp` is the real health check. Claude may still print a misleading startup warning about `no MCP server configured with that name`; if `/mcp` shows `architect-comments` connected, the session is healthy. The channel server provides `update_feedback_status` and `finalize_feedback_update`; a real manual run validated both tools end to end. `validate-feedback-update.py` is intentionally opinionated but follows real Architect artifact conventions where the written contract is narrower than current output practice. The diagram UI now uses a tokenized warm-neutral light/dark theme on `html[data-theme]`, the header has a persisted theme toggle, and production SVG fragments emit element/neutral CSS vars directly instead of a hard-coded dark palette. The latest visual regression artifact is `evals/manual-docsign-tests/diagram-20.html`, with verification screenshots in `evals/manual-docsign-tests/screenshots-diagram-20/`.
The person-card runtime normalizer in `diagram-app.html` now preserves a top-aligned eyebrow/title/body stack instead of recentering `Person` into the middle of the card. The fresh DocSign verification artifact is `evals/manual-docsign-tests/diagram-2.html`, with a dark screenshot at `/tmp/architect-screens/diagram-2-dark.png`.
