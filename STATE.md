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

- [x] Polished diagram rendering so authored SVGs stay bounded on large screens and header rows read lighter, tighter, and transparent
- [x] Documented the blessed Claude handoff launch/setup path with the exact known-good commands and verification steps
- [x] Added `validate-feedback-update.py` plus the `finalize_feedback_update` Claude MCP tool for deterministic validate-render-validate completion
- [x] Added `POST /jobs/:id/status` plus the `update_feedback_status` Claude MCP tool for real-agent status updates
- [x] Verified a real interactive Claude CLI session receives the Architect channel event and responds to the feedback batch end to end

## Notes for Next Session

Claude handoff is now the primary documented mode and the deterministic worker is fallback. The blessed setup lives in `skills/architect-diagram/channels/architect-comments/README.md`: install the channel dependency, write `/tmp/architect-channel-mcp.json`, start the bridge with `--claude-channel-url ... --channel-handoff-only`, then start Claude with `--strict-mcp-config`, `--dangerously-load-development-channels server:architect-comments`, and `--permission-mode auto`. Do not also pass `--channels server:architect-comments`. `/mcp` is the real health check. Claude may still print a misleading startup warning about `no MCP server configured with that name`; if `/mcp` shows `architect-comments` connected, the session is healthy. The channel server provides `update_feedback_status` and `finalize_feedback_update`; a real manual run validated both tools end to end. `validate-feedback-update.py` is intentionally opinionated but follows real Architect artifact conventions where the written contract is narrower than current output practice. Recent diagram polish landed in the renderer: bounded SVG sizing on wide screens, lighter/tighter header rows, transparent SVG backgrounds, and no drilldown plus badge. Upstream main already includes the generic SVG fragment pipeline work for arbitrary discovery outputs, so the next likely iteration is product polish and host-support expansion rather than diagram-renderer unblocking.
