# DECISIONS

### Warm-Neutral Diagram Theme Tokens — 2026-04-17

**Context**
`diagram-app.html` and `generate-svg-fragments.py` were still anchored to a hard-coded dark palette. That made every visual change expensive, blocked a clean light mode, and forced the browser-side remap layer to do too much work after render.

**Decision**
Adopt one warm-neutral light/dark token system on `html[data-theme]`, add a header toggle that persists to `localStorage`, and emit production SVG fragments with neutral chrome plus category-based element tokens directly. The stable kind-to-token mapping is: people -> Sage, software systems -> Indigo, containers -> Plum, components/caches -> Teal, external systems -> Ochre, databases -> Slate, queues -> Rose.

**Consequences**
Theme switching now works without regenerating the page, future styling work should extend token usage instead of reintroducing hex values, and diagrams stay visually consistent between production fragments and the template's fallback renderer.

### Auto-render diagram after discovery — 2026-04-16

**Context**  
`architect-plan` already auto-invokes `architect-diagram`, but `architect-discover` still documented diagram generation as optional/manual. That mismatch made the plan and discover flows behave differently even though both produce the same artifact contract and both ultimately feed the same interactive diagram experience.

**Decision**  
`architect-discover` should finish by handing off to `architect-diagram` with the same output root so `diagram.html` is generated automatically. The discover skill still owns artifact generation; the diagram skill still owns rendering. `diagram-prompt.md` remains explicit-only through `architect-diagram-prompt`.

**Consequences**  
Discover and plan now share the same default output shape for normal runs. Documentation and agent prompts must reflect the automatic handoff, and diagram regressions now block both flows instead of only diagram-only runs.

### Generic SVG Fragment Pipeline — 2026-04-16

**Context**  
The previous `generate-svg-fragments.py` implementation was really a DocSign illustration script: it hardcoded sample IDs, only supported system-context and container views, and crashed on arbitrary Discover runs like Rundler. That meant the "rich fragment" path was not actually reusable across repos.

**Decision**  
Replace the hardcoded fragment script with a generic scene/layout pipeline that derives node sets and relationships from the view artifacts, applies view-specific layout strategies (`system_context`, `container`, `component`, `deployment`), and renders metadata-preserving SVG fragments for any repo that conforms to the architecture contract.

**Consequences**  
Rich/demo-mode diagram rendering now works on both planning and discovery outputs without sample-specific IDs. The fragment path is still heuristic rather than perfect, but it is now a real reusable renderer and not a DocSign-only special case.

### Localhost Bridge With File-Backed Jobs — 2026-04-16

**Context**  
Phase 2 adds point-and-click comment feedback inside `diagram.html`. The team needs a transport that feels seamless, gives the user immediate status, works with local HTML, and does not depend on a fragile direct API into any one coding-agent app.

**Decision**  
Use a localhost HTTP bridge as the primary handoff mechanism. The browser submits one batched comment payload per user press of `Submit`. The bridge persists the batch to a file-backed job store, immediately acknowledges receipt, and hands the batch to an agent runner. The runner executes a fast patch path first when possible, then optionally continues with a slower reconcile pass. The same `diagram.html` file is overwritten in place so the user can refresh the same file to see updates.

**Consequences**  
This keeps the browser-to-agent handoff simple and reliable, gives the system a durable audit trail for status and recovery, and avoids coupling the transport to Codex- or Claude-specific private interfaces. It also means the implementation needs an agent-host adapter layer to make acknowledgements visible inside the active terminal or desktop session.

### SSE With Polling Fallback — 2026-04-16

**Context**  
The browser needs live job-state updates, but EventSource support and localhost bridge availability may vary across environments and refreshes.

**Decision**  
Use server-sent events as the primary live-status transport, with plain polling fallback. On page load, the diagram asks the bridge for the latest job status by `output_root` instead of trusting an embedded status snapshot from the last render.

**Consequences**  
This keeps the UI responsive when SSE works, remains robust when it does not, and avoids stale status banners after refresh. It also means the bridge has to expose both `/jobs/:id/events` and `/latest-status`.

### In-Process Worker, Not External Agent Lifecycle Control — 2026-04-16

**Context**  
There is no stable repo-local API for directly injecting work into every possible Codex or Claude host. The team still needs a working end-to-end loop today.

**Decision**  
Run an in-process worker inside the bridge and use a terminal-host adapter as the first visible acknowledgement surface. Do not make the bridge responsible for launching or controlling an external agent session. Keep the host adapter pluggable so deeper desktop integration can be added later.

**Consequences**  
The bridge works now without app-specific hooks, terminal users get immediate visible acknowledgement, and the browser-side UX stays stable. Richer host integrations can be added later without changing the browser contract.

### Prefer Official Host Wake-Up Surfaces Over Private Session Attachment — 2026-04-16

**Context**  
Architect Phase 3 wants the user's active coding agent to receive diagram comment batches and perform the update work itself. The tempting route is to reverse-engineer private desktop IPC or terminal internals so the bridge can inject a message into whatever session happens to be open.

**Decision**  
Prefer officially supported host surfaces even if they require different integration shapes. For Claude, treat Channels as the primary official pushed-event surface for a running session, with hooks or Remote Control as secondary automation tools. For Codex, treat App Server as the official programmable surface. Do not plan the product around attaching to private desktop IPC or undocumented internal sockets.

**Consequences**  
This keeps the architecture aligned with stable vendor-supported APIs and lowers long-term maintenance risk. It also means “wake the already-open desktop thread” is currently more viable on Claude than Codex. If we want first-class Codex support, we likely need to own a Codex App Server-backed session rather than hijacking an arbitrary existing desktop conversation.

### Claude First, Codex Backlogged — 2026-04-16

**Context**  
Architect needs a true agent-driven comment loop. Validation showed Claude has a credible official wake-up path for running sessions, while Codex currently has an official programmable protocol but no validated supported attach-to-current-session path for normal user flows.

**Decision**  
Target Claude support first. Primary target: Claude CLI. Secondary nice-to-have: Claude desktop/app surfaces only if they work through the same Claude Code integration shape. Explicitly backlog Codex support for now.

**Consequences**  
This narrows implementation and testing to one host family, lets us optimize the comment loop around Claude-native event delivery, and avoids overdesigning an abstraction for hosts that do not yet have equivalent capabilities. It also means the next major decision is Channels versus Hooks for Claude.

### Use Claude Channels, Not Hooks, For Agent Wake-Up — 2026-04-16

**Context**  
For Claude-first comment updates, the team needed to choose between Channels and Hooks. Hooks can watch files like `feedback-jobs/latest.json`, but they treat comment delivery as a file-change side effect. Channels are the official Claude surface for pushing external events into a running session.

**Decision**  
Use Channels as the primary wake-up and handoff mechanism. Keep hooks out of the primary path. If a fallback is needed later, use hooks only as a degraded local reminder mechanism rather than the main event bus.

**Consequences**  
Architect can model comment submission as a first-class external event instead of a file watcher hack. This gives a clearer contract for acknowledgement, future reply tools, and permission relay. It also means setup will likely require explicit Claude channel enablement and development-channel confirmation during local spike work.

### Channel-Side Finalize Tool For Comment Updates — 2026-04-16

**Context**  
The first live Claude channel run worked, but Claude still guessed at local render commands and could drift off the artifact contract while editing YAML by hand. We needed a safer completion path that preserves the bridge URL, validates the edited artifacts, rerenders the same `diagram.html`, and validates the resulting HTML before the job is marked complete.

**Decision**  
Add a Claude MCP tool in the Architect channel server named `finalize_feedback_update`. Claude should use normal repo tools for exploration and editing, but it should use `update_feedback_status` for progress reporting and `finalize_feedback_update` for the validate-render-validate completion step instead of inventing shell commands ad hoc.

**Consequences**  
The live agent keeps ownership of the update loop, but the riskiest step becomes deterministic and easier to audit. This also gives us one place to harden post-feedback validation over time without rewriting the Claude prompt every time a new drift pattern appears.

### Blessed Claude Launch Path — 2026-04-16

**Context**  
Once Claude handoff became the primary product mode, the team no longer needed multiple experimental setup stories. What we needed instead was one canonical launch recipe that future operators and agents could follow without rediscovering the same hidden flags, startup quirks, and verification steps.

**Decision**  
Document one blessed Claude setup path in `skills/architect-diagram/channels/architect-comments/README.md` and link to it from the root `README.md`. The blessed path uses a temporary MCP config, runs the bridge with `--claude-channel-url ... --channel-handoff-only`, starts Claude with `--strict-mcp-config`, `--dangerously-load-development-channels server:architect-comments`, and `--permission-mode auto`, and treats `/mcp` connection status as the authoritative health check.

**Consequences**  
This gives the repo one operator story instead of several half-valid ones. It also captures the important quirks explicitly: do not also pass `--channels server:architect-comments`, `claude --help` may omit the relevant flags, and the startup warning about `no MCP server configured with that name` can still appear even when `/mcp` shows a healthy connected session.
