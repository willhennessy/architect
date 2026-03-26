---
name: generate-architecture-from-codebase
description: Discover and model the architecture of an unfamiliar codebase, then emit a canonical architecture model plus derived structured view files for multiple audiences. Use this skill when asked to explore a repository, identify runtime boundaries, data ownership, key workflows, or generate architecture artifacts from source code.
---

Use this skill to inspect a codebase for the first time and produce structured architecture artifacts. The deliverable is a canonical architecture model plus derived view files. Do not render diagrams in this skill.

Default modeling style:

- `C4` for static structure
- `Sequence` views for critical workflows
- `Deployment` view only when topology materially affects understanding

The source of truth is the canonical architecture model, not the audience-specific views.

## Outcome

Produce a small, grounded set of artifacts that explain:

- what the system is and what it interacts with
- what the main runtime boundaries are
- which responsibilities and data ownership boundaries exist
- how critical workflows behave
- which claims are confirmed versus inferred

The minimum useful output is usually:

1. `architecture/model.yaml`
2. `architecture/views/system-context.yaml`
3. `architecture/views/container.yaml` when deployable/runtime units exist
4. `architecture/views/component-*.yaml` only for important internal boundaries
5. `architecture/views/sequence-*.yaml` only for critical workflows
6. `architecture/views/deployment.yaml` only when topology matters
7. `architecture/manifest.yaml`
8. `architecture/summary.md`
9. `architecture/diff.yaml` in update mode only

## Required Output Contract

Before writing outputs, read [references/output-format.md](references/output-format.md) and follow its schemas exactly.

Default output path:

- `architecture/manifest.yaml`
- `architecture/model.yaml`
- `architecture/views/*.yaml`
- `architecture/summary.md`
- `architecture/diff.yaml` in update mode

If the user specifies a different output path, honor it.

## Hard Rules

- Explore first, infer second, write last.
- Build one canonical architecture model, then derive views from it.
- Do not create separate inferred facts per view.
- Distinguish source layout from runtime architecture.
- Use explicit confidence levels: `confirmed`, `strong_inference`, `weak_inference`.
- Prefer stable normalized names and IDs; reuse existing IDs in update mode.
- Record unknowns instead of inventing answers.
- Sequence views must reference elements already defined in the canonical model.
- Keep abstraction levels strict. Do not mix C4 levels in one view.
- Treat data ownership and system-of-record information as first-class when applicable.

## Evidence Hierarchy

When signals conflict, trust them in this order:

1. Runtime and deploy reality: entrypoints, process definitions, deployment manifests, service configs
2. Contract and state signals: API schemas, infra definitions, migrations, queue/topic definitions
3. Behavioral code signals: handlers, call sites, imports, adapters, persistence paths
4. Documentation: READMEs, ADRs, internal docs
5. Naming-only signals: directory names, package names, vague file names

Do not let weak naming signals override runtime or contract evidence.

## Repo Archetype Branching

Classify the repo before deciding which views to emit. Use one primary archetype:

- `library_package`
- `frontend_only_app`
- `modular_monolith`
- `service_oriented_backend`
- `full_stack_product`
- `infrastructure_repo`

Apply these defaults:

- `library_package`: produce a context view only if consumers are visible; prefer component/module views over container views.
- `frontend_only_app`: one frontend container plus external APIs; add component views for state, routing, or domain modules only if meaningful.
- `modular_monolith`: one deployable container; represent bounded modules as components; do not invent multiple containers unless runtime evidence supports them.
- `service_oriented_backend`: system context and container views are usually mandatory; add component and sequence views selectively.
- `full_stack_product`: context plus container views across frontend, backend, data, and external systems; add sequence views for critical user journeys.
- `infrastructure_repo`: deployment view is usually primary; only create context/container views if the repo defines a runnable platform or control plane.

If the correct answer is "this repo is a library, not a deployable system", say so and adjust outputs accordingly.

## Discovery Workflow

### 1. Frame the task

Define:

- system in scope
- intended audiences
- output path
- extraction mode: `initial` or `update`
- constraints from the user

Reason:
Architecture artifacts are communication tools. Scope and mode must be explicit before modeling.

### 2. Check for existing architecture artifacts

In `update` mode, or whenever architecture artifacts already exist:

- read the existing `architecture/model.yaml`, `manifest.yaml`, and relevant views first
- preserve stable IDs where the underlying concept is unchanged
- prefer semantic deltas over full rewrites
- emit `architecture/diff.yaml` describing added, removed, and changed elements, relationships, and views

Reason:
Architecture maintenance depends on stable identity and diffability.

### 3. Build an initial repo map

Inspect:

- top-level directories
- package manifests
- build files
- entrypoints
- infra and deployment files
- migrations and schemas
- docs and ADRs

Use targeted discovery. Prefer `rg --files` and focused `rg` searches over broad scans.

### 4. Identify repo archetype

Determine which primary archetype best fits the repository. Base this on runtime and packaging evidence, not naming preference.

Reason:
The correct artifact set differs across libraries, monoliths, service-oriented systems, frontend apps, and infra repos.

### 5. Identify canonical architecture elements

Populate the canonical model with normalized, deduplicated elements.

Required questions:

- what runs as a separate process or deployable unit?
- what stores persistent state?
- what external systems matter?
- what meaningful internal modules exist?
- who owns what data?
- what is the system of record for major entities?

Do not create near-duplicate elements such as `Order Service`, `Orders API`, and `Order Backend` unless evidence shows they are distinct.

### 6. Identify relationships and critical workflows

For each important path, identify:

- source and target
- interaction type
- sync versus async
- protocol or transport
- major data objects involved
- failure-sensitive boundaries

Critical workflows usually include:

- request entry path
- authentication or identity path
- primary business transaction
- background processing or async propagation

### 7. Cross-check operational reality

Inspect deployment and operational artifacts:

- deployment manifests
- CI/CD
- runtime env config
- feature flags
- observability config
- runbooks

Reason:
Static code alone often misstates runtime truth.

### 8. Build the canonical model first

Write `architecture/model.yaml` before writing any views.

The model is the only place where architecture facts are defined. Views only reference model IDs and filter/present them.

### 9. Derive views from the canonical model

Apply strict view rules:

- `system_context`: only the system of interest, people, and external systems
- `container`: only deployable/runtime units, datastores, queues/brokers, and relevant externals
- `component`: only meaningful internal modules within one container
- `sequence`: only previously defined model elements; do not invent ad hoc participants
- `deployment`: only nodes, zones, and placement when topology is architecturally relevant

### 10. Write summary and diff artifacts

Write `summary.md` using the fixed structure in the reference file.

In update mode, write `diff.yaml` with:

- added elements
- removed elements
- changed elements
- added relationships
- removed relationships
- changed relationships
- added or removed views

## Stable Naming and Deduplication

- Normalize names around responsibility, not implementation detail.
- Reuse a canonical name across model and views.
- Reuse an element unless evidence proves it is distinct.
- Prefer explicit IDs that remain stable across regeneration.
- Record aliases when the codebase uses multiple names for the same concept.

## C4 Boundary Rules

- `System Context`: system-of-interest, people, external systems only.
- `Container`: deployable/runtime units plus stateful stores and brokers only.
- `Component`: internal modules inside exactly one container only.
- `Code`: out of scope for this skill unless the user explicitly requests code-level modeling.

Do not place components on a system-context or container view. Do not place classes on component views.

## Data Ownership Rules

Whenever applicable, every container or component in the canonical model should declare:

- `owned_data`
- `system_of_record`

If ownership is unclear, record an unknown rather than omitting the issue silently.

## Common Mistakes To Avoid

Do not:

- start diagramming before identifying repo archetype and runtime boundaries
- confuse folders with containers
- create one giant view containing multiple abstraction levels
- generate views before the canonical model exists
- infer ownership from names alone
- ignore data ownership, dual writes, caches, or system-of-record questions
- let docs override stronger runtime evidence
- create duplicate elements with slightly different names
- emit sequence participants that do not exist in the model
- rewrite IDs on every run
- omit `diff.yaml` in update mode
- overproduce container views for libraries or modular monoliths

## Completion Standard

The skill is complete only when:

1. `architecture/model.yaml` exists and follows the schema
2. views are derived from that model and obey level rules
3. `summary.md` follows the fixed structure
4. `manifest.yaml` records scope, archetype, mode, and artifacts
5. `diff.yaml` exists in update mode
6. assumptions, unknowns, confidence, and evidence are explicit
