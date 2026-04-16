# DECISIONS

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
