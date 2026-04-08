# Claude Architect — Marketing + Press Materials

## Marketing ideas
Leave lines of code to the agent. Architect gives you control over higher level design decisions with a birds eye view architecture diagram and point-and-click feedback to the agent.

Coding agents are writing code faster than ever. The bottleneck remains human review - but you don’t need to review every line. Architect is a new steering interface for coding agents that lets you operate with leverage at a higher layer of abstraction. Review architecture - not lines of code.

## Press release

1. 90-second demo script (voiceover)

Title card (0:00–0:03)
“Claude Architect: diagrams as the control surface for coding agents”

Problem (0:03–0:12)
“Coding agents can generate PRs faster than humans can reason about architecture.
Senior engineers need a higher-level interface than line-by-line review.”

Step 1 — Initialize architecture (0:12–0:25)
“I run architect init on this repo.
Claude Architect builds an evidence-backed architecture model: context, containers, components, and dependency edges.”

Step 2 — Interactive architecture + WHY (0:25–0:40)
“Each component is clickable.
For every edge and design choice, I can inspect the rationale and source evidence: files, symbols, and commit references.”

Step 3 — Steering loop (lean-forward moment) (0:40–0:56)
“I click this edge and comment: ‘Route this through async queue, not direct sync call.’
The agent updates the architecture and explains second-order effects: latency, failure isolation, and ownership boundaries.”

Step 4 — Implementation handoff (0:56–1:05)
“Once approved, I switch from architect mode to implementation.
The coding agent executes against the approved architecture.”

Step 5 — PR architecture diff (1:05–1:24)
“When the PR opens, Claude Architect auto-attaches a visual architecture diff.
It shows what changed, why it changed, evidence links, and risk flags like boundary crossings and coupling increases.”

Close (1:24–1:30)
“Claude Architect turns diagrams from documentation into a control plane for AI-native engineering.”

───

1. Shot list / storyboard (what to show on screen)

1) Repo + problem text overlay (agent PR velocity up, architecture review bottleneck)
2) Terminal: architect init + generated architecture/\*.yaml
3) Diagram view: click container/component, open rationale panel
4) Comment action on edge (“use queue”)
5) Regenerated diagram + updated WHY panel
6) Terminal: “approve architecture / implement”
7) GitHub PR view with attached architecture diff artifact
8) Diff panel with 3 sections: Changed, Why, Risk
9) Final frame: “Diagram = control surface”
