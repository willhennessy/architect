# DECISIONS

### Approved Instrument Sans Google Fonts Exception — 2026-04-18

**Context**
The typography correction wanted the exact Instrument Sans face, and the user explicitly chose the Google Fonts path instead of preserving strict self-containment. The existing validator and diagram contract still rejected every external `<link>` tag, which meant the new font load failed production validation even though the rest of the artifact remained a single file.

**Decision**
Keep `diagram.html` as a single-file artifact with inline CSS/JS, but allow one narrow external dependency exception: the approved Instrument Sans Google Fonts links (`fonts.googleapis.com` / `fonts.gstatic.com`). Update the validator and contract docs to allow only that exception and continue rejecting arbitrary external assets.

**Consequences**
The diagram keeps practical portability and graceful fallback behavior while matching the intended typography more closely. The tradeoff is that the artifact is no longer strictly self-contained or fully offline-deterministic, so future contract language and evals need to talk about a single-file artifact with an approved font exception rather than "no external dependencies" in absolute terms.

### Fluid Motion Inside The Existing Artifact Contract — 2026-04-18

**Context**
The diagram shell had grown into a real interactive app, and the next design pass wanted Benji-style fluidity: visible continuity between views, modes, and comment interactions. The tempting move was to introduce React or a separate frontend app shell, but Architect’s output contract still depends on emitting one portable self-contained `diagram.html`.

**Decision**
Keep the production artifact contract intact and implement the motion architecture inside `skills/architect-diagram/templates/diagram-app.html`. Use stronger shared design/motion tokens, directional document view transitions for view changes, lighter surface transitions for mode/detail changes, and origin-aware popover motion for inline comments. Skip the motion-heavy path for keyboard-triggered mode switches so repeated actions stay snappy.

**Consequences**
Architect gets a much more fluid shell without changing the renderer contract or introducing a dependency/bundle pipeline yet. The tradeoff is that the template remains large, so the next scaling decision is whether to introduce a source-authored build step that still emits the same self-contained HTML.

### Explicit Explore And Comment Modes In Diagram Shell — 2026-04-17

**Context**
The diagram shell had grown around a one-off `Comment (C)` toggle in the toolbar, a transient banner, and a details sidebar that only appeared for node inspection. That mixed two distinct workflows: drilling into architecture and staging feedback for submission.

**Decision**
Promote diagram interaction into two explicit persisted modes: `Explore` and `Comment`. Use a centered segmented control above the canvas as the primary mode switch, persist the chosen mode in `localStorage`, and make the right sidebar mode-aware: component details in Explore, comment list plus sticky submit footer in Comment.

**Consequences**
The review UI now has a clearer contract: Explore is for inspection and drill-down, Comment is for attaching and reviewing feedback. Future shell work should treat mode as first-class state and add sidebar actions inside the mode-specific panels instead of reintroducing global comment chrome.

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

### Color-Based Elevation Only, No Shadows — 2026-04-18

**Context**  
The diagram shell kept regressing toward shadow-based chrome: after removing shadows from one surface, a new `box-shadow` or `drop-shadow` would appear on a different control or panel in a later pass. That meant the problem was systemic rather than local to one component.

**Decision**  
Treat shadow-based elevation as disallowed across the tracked repo. Do not use `box-shadow`, `filter: drop-shadow`, `text-shadow`, or shadow variables. Use background elevation tokens, 1px borders, and `outline` for `:focus-visible` states instead.

**Consequences**  
Future shadow additions are bugs, not design choices to debate case by case. Controls that need more grounding must solve it with border/background changes, and even reference/eval HTML artifacts should stay shadow-free so repo-wide grep remains a real enforcement tool.

### Plugin-Owned Claude Runtime For Private Beta — 2026-04-17

**Context**  
The Channels-based comment loop was validated, but the operator story still required users to manually start a localhost bridge, manually start a bare channel server, and hand-roll MCP config just to use Architect normally. That friction is too high for private beta distribution.

**Decision**  
Package Architect as a real Claude plugin with a plugin-owned runtime. The plugin runtime combines the browser bridge endpoints, the Claude channel emitter, and the `update_feedback_status` / `finalize_feedback_update` MCP tools in one process. The plugin uses a `SessionStart` hook to bootstrap Node and Python dependencies into `${CLAUDE_PLUGIN_DATA}` so end users do not manually run `npm install` or set up a separate bridge process. Claude CLI is the only committed host target for this first plugin beta.

**Consequences**  
The primary operator flow moves from "start bridge + start bare channel server" to "launch Claude with the Architect plugin". The old Python bridge and bare channel server remain available as repo-level fallback/dev infrastructure, but they are no longer the primary product story. The plugin bundle must mirror the shipping skills, references, templates, and shipped scripts so installed-plugin execution does not depend on repo-external paths.
The original bootstrap implementation used a `SessionStart` hook; that detail was later superseded by **Bootstrap The Plugin Runtime On MCP Launch** once cold-start races showed up in real sessions.

### Repo-Local Development Marketplace For Channel Testing — 2026-04-17

**Context**  
The plugin bundle loaded correctly via `--plugin-dir`, but Claude’s development-channel flag rejected `plugin:architect` because development channels currently require a marketplace-qualified plugin identifier like `plugin:<name>@<marketplace>`.

**Decision**  
Add a repo-local development marketplace rooted at `claude-plugin/` with the existing `claude-plugin/architect/` bundle published as `architect@architect-local`. For development sessions, install the plugin from that local marketplace and still pass `--plugin-dir` so the live working copy overrides the installed cache while the channel flag uses a valid plugin-qualified identifier.

**Consequences**  
The development command becomes slightly longer, but it is now valid under Claude’s current Channels preview rules. This avoids creating a second plugin copy just to satisfy marketplace identity, and keeps the local plugin bundle as the only packaged artifact we edit directly.
The `--plugin-dir` override part of this decision was later superseded by **Installed Plugin Identity Required For Plugin Channel Delivery** once Claude’s channel identity checks proved stricter than expected.

### Installed Plugin Identity Required For Plugin Channel Delivery — 2026-04-17

**Context**  
After adding the repo-local development marketplace, the team tried to preserve live-working-copy behavior by launching Claude with both `--plugin-dir ./claude-plugin/architect` and `--dangerously-load-development-channels plugin:architect@<marketplace>`. The MCP server connected, but comment jobs stayed stuck in `received` and Claude never reacted. Claude debug logs revealed the reason: `Channel notifications skipped: you asked for plugin:architect@... but the installed architect plugin is from inline`.

**Decision**  
For live plugin-channel testing, do not combine `--plugin-dir` with the plugin-qualified channel flag. Install `architect@<marketplace>` from the repo-local marketplace and launch Claude against that installed plugin identity, plus the explicit Architect channel handoff system prompt. Keep `--plugin-dir` for non-channel plugin loading/dev inspection only.

**Consequences**  
The local development story becomes less convenient because the live session no longer runs directly from the inline plugin override. In return, channel delivery actually works with Claude’s current plugin-channel identity checks. Manual-eval tooling and docs must treat marketplace install as the canonical path for end-to-end comment-loop testing.

### Official Claude Marketplace Is The Public Distribution Path — 2026-04-19

**Context**  
The original plugin docs were written around private-beta distribution and internal dev loops. That was fine for getting the runtime working, but it leaked internal setup details like `--permission-mode auto` and overly verbose operator guidance into the public-facing story.

**Decision**  
Treat the official Claude marketplace as the public distribution path for Architect. The public getting-started guide should show a marketplace install, a normal `--channels plugin:architect@claude-plugins-official` launch, default outputs under `./architecture/`, and a short refresh-based comment loop. Do not require `--permission-mode auto` in the end-user path.

**Consequences**  
The user-facing docs stay aligned with what external users can actually run. Internal eval tooling can still use extra flags when useful, but public guidance should stay marketplace-first, bash-only, and concise.

### Keep The Explicit Channel System Prompt In Internal Eval Launches — 2026-04-19

**Context**  
We tested whether the plugin channel's built-in `instructions` were strong enough to replace the extra `--append-system-prompt` in internal eval sessions. In a real run against `evals/manual-docsign-tests/run-003`, Claude started successfully, the channel connected, and the bridge accepted a comment batch, but the job auto-failed after ~20 seconds with `agent_ack_timeout`.

**Decision**  
Keep the explicit Architect channel system prompt in internal eval launchers such as `scripts/new-manual-eval.sh` for now. Public marketplace docs can stay clean and omit it, but internal validation paths should keep the extra prompt until we find a plugin-native mechanism that proves equally reliable.

**Consequences**  
We do not pretend the no-append path is validated when it is not. Internal eval flows keep a slightly noisier launch command, but the working comment loop remains reliable while we continue investigating whether stronger channel instructions or another plugin-native hook can replace the extra prompt.

### Public Plugin Ships Only User-Facing Skills — 2026-04-19

**Context**  
The repo contains internal eval skills like `run-plan-eval` and `run-architecture-eval` that are useful for maintainers but confusing for marketplace users. Even though the plugin sync path was already only copying the four user-facing skills, it did not actively prune stale extra skill directories from an existing plugin snapshot.

**Decision**  
Treat the public plugin bundle as a strict allowlist. The plugin ships only `architect-plan`, `architect-discover`, `architect-diagram`, `architect-diagram-prompt`, plus shared references. The sync script now removes any other skill directories from `claude-plugin/architect/skills/`, including internal eval skills.

**Consequences**  
Marketplace users see a cleaner slash-command surface, and old plugin snapshots cannot accidentally keep maintainer-only skills alive. Internal eval skills remain in the repo, just not in the public plugin distribution.

### Fail Clearly When The Architect Bridge Port Is Occupied — 2026-04-19

**Context**  
When a second Architect-backed Claude session started while another runtime was still listening on `127.0.0.1:8765`, `/mcp` only showed a generic failed server. The real cause was a fixed-port collision, but the user had to inspect `lsof` manually to discover that.

**Decision**  
Add an explicit startup check in the plugin launcher for `ARCHITECT_BRIDGE_PORT` conflicts and mirror the same wording in the Node runtime's bind error path. The error should name the port, the bind address, the likely owner process, and the recommended recovery command.

**Consequences**  
Plugin users get a concrete, actionable failure instead of a vague MCP reconnect loop. Architect still uses a single fixed local port for now, but the failure mode is much easier to diagnose until we decide whether to support dynamic per-session ports.

### Auto-Fail Unacknowledged Comment Jobs — 2026-04-17

**Context**  
Before hardening, a comment batch could get stuck in `received` forever if Claude never acknowledged the channel event. That left `diagram.html` locked in “Comments sent. The agent is reviewing them now.” and forced manual `failed` status surgery just to submit another batch.

**Decision**  
If a feedback job remains in `received` for roughly 20 seconds without moving to `acknowledged`, the plugin runtime should automatically mark it `failed` with a clear retry message. The browser should treat 409 “job already in progress” responses as a status refresh, not a copy-JSON fallback, so stale locks collapse back into the live status view.

**Consequences**  
The UI now recovers from missing Claude acknowledgements without manual intervention, and stale `received` jobs no longer trap the comment bar indefinitely. The timeout is intentionally narrow to the pre-ack phase so long-running real updates are not interrupted once Claude has actually started work.

### Revision-Keyed SVG Fragments — 2026-04-17

**Context**  
A real comment update renamed `Tenant Admin` to `Frank Admin` in `architecture/model.yaml`, and the details panel showed the new name, but the node label in the visual diagram still showed the old one. Investigation showed the renderer was blindly embedding existing `diagram-svg/*.svg` fragments even after the canonical architecture artifacts changed, so stale fragment text could override the updated model data in `diagram.html`.

**Decision**  
Treat `diagram-svg/` as a revision-keyed cache, not a source of truth. `generate-svg-fragments.py` now writes `diagram-svg/_metadata.json` with the current architecture revision ID, and `render-diagram-html.py` only uses SVG fragments when that revision matches the current `architecture/` state. If metadata is missing or stale, the renderer falls back to the live in-template layout path instead of embedding stale SVG.

**Consequences**  
The visual diagram and the details panel now stay in sync after comment-driven YAML edits, even when old SVG fragments are still on disk. Rich/demo flows need fresh fragment generation to get fragment-backed visuals, but they can no longer silently reuse stale SVG text after a model change.

### Bootstrap The Plugin Runtime On MCP Launch — 2026-04-17

**Context**  
The first plugin-backed Claude sessions were flaky: `/mcp` would often show `plugin:architect:architect-comments · ✘ failed` immediately after startup, and manually reconnecting the server would then work. The plugin manifest was bootstrapping Node and Python dependencies in a separate `SessionStart` hook while the MCP server itself launched independently, so cold starts could race the server connection against dependency installation.

**Decision**  
Move runtime bootstrap onto the MCP launch path itself. The plugin MCP server now starts through `scripts/launch-runtime.sh`, which first runs `bootstrap-runtime.sh`, then exports `NODE_PATH`, then execs the runtime server. Remove the separate `SessionStart` bootstrap hook instead of relying on parallel startup work.

**Consequences**  
Cold starts may spend a bit longer before the first MCP connection completes, but the server no longer needs a manual reconnect after Claude launches. The runtime prerequisites are now serialized behind MCP startup, which makes behavior more predictable and easier to reason about than a background hook racing the connection.

### Preserve Existing Render Profile On Comment Updates — 2026-04-17

**Context**  
A simple comment-driven rename on a rich Rundler diagram caused an unacceptable downgrade: Claude updated the YAML correctly, but `finalize_feedback_update` rerendered with `render_mode=fast`, which dropped the component views and fell back to a much more basic visual presentation. That makes comment submission feel destructive even when the underlying architecture change is tiny.

**Decision**  
Treat the current `diagram.html` render profile as the default contract for comment updates. `finalize_feedback_update` now inspects the existing diagram, preserves rich/component view sets, preserves sequence inclusion when already present, and regenerates SVG fragments when the current diagram was using them. `render-diagram-html.py` also embeds `comment_handoff.render_context` so future comment updates can carry this profile forward explicitly.

**Consequences**  
Small comment edits no longer silently downgrade a high-quality diagram into a stripped-down fast render. Comment updates may spend a little longer regenerating SVG fragments for rich diagrams, but the quality stays consistent with what the user was already reviewing, which is the right tradeoff for trust and product feel.

### User-Facing Artifacts Live Under `architecture/` — 2026-04-19

**Context**  
The visible output package had drifted into an awkward split: canonical YAML artifacts lived under `architecture/`, but the main rendered diagram and related user-facing files were written beside that folder. That leaked internal implementation structure into the user experience and forced docs/examples to talk about a parent output root instead of one clear artifact package.

**Decision**  
Treat `architecture/` as the visible artifact package. The primary rendered diagram now lives at `architecture/diagram.html`, and any user-facing upload bundle should live at `architecture/diagram-prompt.md`. Internal render/comment-loop state is allowed to live under hidden `architecture/.out/` sidecar paths so the browser/job system can keep working without cluttering the visible package.

**Consequences**  
End users can reason about one artifact directory instead of a split output shape, and public docs/examples no longer need to teach `./out/...` style phrasing just to explain where the diagram landed. Runtime/path-sensitive code has to preserve the distinction between visible artifacts in `architecture/` and hidden state in `architecture/.out/`.
