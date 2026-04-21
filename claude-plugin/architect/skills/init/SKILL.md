---
name: init
description: Discover and model the architecture of an unfamiliar codebase, emit a canonical architecture model plus derived structured view files for multiple audiences, then automatically hand off to architect-diagram for the interactive HTML diagram. Use this skill when asked to explore a repository, identify runtime boundaries, data ownership, key workflows, or generate architecture artifacts from source code.
---

Use this skill to inspect a codebase for the first time and produce structured architecture artifacts. The deliverable is a canonical architecture model plus derived view files, followed by a handoff to `architect-diagram` for `diagram.html`.

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
10. `architecture/diagram.html`

## Required Output Contract

Before writing outputs, read [../references/architecture-contract.md](../references/architecture-contract.md) and follow its schemas exactly.

Resolve the contract through the skill-relative reference path only.

- In the repo checkout, use `../references/architecture-contract.md`.
- In plugin installs, use the mirrored skill reference shipped with the plugin at `skills/references/architecture-contract.md`.
- If that lookup fails, stop and report the missing contract path.
- Do **not** run a repo-wide search for alternate contract files, artifact examples, `manifest.yaml`, `model.yaml`, or nearby architecture outputs.

Default output path:

- `architecture/manifest.yaml`
- `architecture/model.yaml`
- `architecture/views/*.yaml`
- `architecture/summary.md`
- `architecture/diff.yaml` in update mode
- `architecture/diagram.html`
- `architecture/diagram-prompt.md` only when explicitly requested

If the user specifies a different output path, honor it.

## Hard Rules

- Explore first, infer second, write last.
- Build one canonical architecture model, then derive views from it.
- Do not create separate inferred facts per view.
- Unless the user explicitly asks for examples or eval analysis, do **not** read from `evals/`, `examples/`, `iteration-*`, `skill-snapshot/`, or similar archive/snapshot directories to infer the contract or bootstrap artifacts.
- Read repo-local agent or contributor guidance files inside the target repo when they exist, and treat explicit architectural constraints there as high-strength documentation unless stronger runtime evidence disproves them.
- Distinguish source layout from runtime architecture.
- Treat deployment modes and packaging modes separately from runtime roles. If the same runtime role can run collocated or split, model the role as the container and the collocation choice as deployment evidence.
- Use explicit confidence levels: `confirmed`, `strong_inference`, `weak_inference`.
- Prefer stable normalized names and IDs; reuse existing IDs in update mode.
- Record unknowns instead of inventing answers.
- Sequence views must reference elements already defined in the canonical model.
- Do not reuse a forward-call relationship to represent a reply edge in a sequence view. If the step is a response path and no reverse relationship exists in the canonical model, omit `relationship_id` for that step.
- Keep abstraction levels strict. Do not mix C4 levels in one view.
- Treat data ownership and system-of-record information as first-class when applicable.
- Model optional external infrastructure explicitly when it materially affects runtime behavior, but do not let configuration-gated adapters become primary containers unless they own core business state.
- Do not assign the same data object to multiple systems of record unless the duplication is explicitly justified in the summary or notes.
- If a capability supports multiple real transports or deployment boundaries, prefer an explicit mode split or a neutral protocol label over one precise but incomplete claim.
- If storage interfaces or first-class APIs expose persisted entities, include them in data-ownership analysis even when they are not the star of a workflow view.
- After each draft or final artifact generation pass, automatically invoke `architect-diagram` using the same output root so the rendered HTML diagram stays in sync with the latest artifacts.
- Keep the skill boundary explicit: `architect-init` owns discovery and artifact generation; `architect-diagram` owns `diagram.html` rendering.

## Evidence Hierarchy

When signals conflict, trust them in this order:

1. Runtime and deploy reality: entrypoints, process definitions, deployment manifests, service configs
2. Contract and state signals: API schemas, infra definitions, migrations, queue/topic definitions
3. Behavioral code signals: handlers, call sites, imports, adapters, persistence paths
4. Documentation: READMEs, ADRs, internal docs
5. Naming-only signals: directory names, package names, vague file names

Do not let weak naming signals override runtime or contract evidence.
If docs and runtime evidence diverge, model runtime truth, record the conflict in `unknowns` or `notes`, and avoid silently blending the two.
If README-level claims conflict with stronger runtime evidence or more specific architecture docs, explicitly say so in `summary.md` or `unknowns` instead of silently averaging them together.

Version and capability claims (supported protocol versions, feature coverage, API compatibility) must be verified against code artifacts — contract files, feature flags, protocol definitions, version constants — not documentation alone. If the model states "supports v0.6 and v0.7", the code must contain evidence for exactly those versions.

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
- `service_oriented_backend`: always produce `model`, `manifest`, `summary`, `system-context`, and `container`; add component views only for containers with meaningful internal boundaries and sequence views only for critical workflows.
- `full_stack_product`: context plus container views across frontend, backend, data, and external systems; add sequence views for critical user journeys.
- `infrastructure_repo`: always produce `model`, `manifest`, `summary`, and `deployment`; only create context/container views if the repo defines a runnable platform or control plane.

If the correct answer is "this repo is a library, not a deployable system", say so and adjust outputs accordingly.

Use the smallest artifact set that still explains the runtime truth. Every container should support drill-down when it has meaningful, evidenced internal boundaries. Do not produce component or deployment views by default if they add no explanatory value.

## Discovery Workflow

### 1. Frame the task

Define:

- system in scope
- intended audiences
- output path
- extraction mode: `initial` or `update`
- constraints from the user

Guardrail:
If the request is planning-only (no repo to inspect yet), stop and route to `architect-plan` instead of continuing discovery.

Reason:
Architecture artifacts are communication tools. Scope and mode must be explicit before modeling.

### 2. Write a modeling ledger before YAML

Create a short internal modeling ledger and keep it stable while you work. At minimum capture:

- `system_in_scope`
- `repo_archetype`
- `stable_runtime_units`
- `state_owners`
- `optional_externals`
- `plugin_mechanisms`: identified extension/plugin systems (e.g., custom senders, aggregators, middleware hooks) with an explicit in-scope or out-of-scope decision for each
- `deployment_modes`
- `out_of_scope`

The ledger is a preflight checkpoint, not a deliverable. Use it to decide what the canonical containers are before writing files.

### 3. Check for existing architecture artifacts

In `update` mode, or whenever architecture artifacts already exist:

- read the existing `architecture/model.yaml`, `manifest.yaml`, and relevant views first
- preserve stable IDs where the underlying concept is unchanged
- prefer semantic deltas over full rewrites
- emit `architecture/diff.yaml` describing added, removed, and changed elements, relationships, and views

Reason:
Architecture maintenance depends on stable identity and diffability.

### 4. Build an initial repo map

Inspect:

- top-level directories
- package manifests
- build files
- entrypoints
- infra and deployment files
- migrations and schemas
- docs and ADRs
- repo-local guidance files such as `AGENTS.md`, `CLAUDE.md`, or similarly named contributor/agent instructions when present

Use targeted discovery. Prefer `rg --files` and focused `rg` searches over broad scans.
Use a discovery budget:

- pass 1: manifests, entrypoints, deployment files, top-level docs
- pass 2: only files needed to confirm runtime boundaries, state ownership, and critical flows
- stop once runtime units, state boundaries, and critical workflows are evidenced

Do not keep reading files once additional scans are only repeating already-confirmed structure.

Add an early path sanity check before writing anything:

- verify the repository-under-test path you are modeling
- verify the requested output path
- ensure manifest scope paths and summary language refer to the actual repo-under-test path, not a copied or inferred placeholder

### 4b. Capture repo-local architecture constraints

If the target repo contains repo-local guidance files, extract any explicit architectural constraints before modeling. Especially look for:

- mandated layering or call order
- naming rules for runtime boundaries
- data ownership terminology
- "must not edit" or generated-file boundaries that affect evidence quality

Treat these as strong documentation signals, but still verify them against runtime and code evidence before writing them into the model.

### 5. Identify repo archetype

Determine which primary archetype best fits the repository. Base this on runtime and packaging evidence, not naming preference.

Reason:
The correct artifact set differs across libraries, monoliths, service-oriented systems, frontend apps, and infra repos.

### 5b. Build a deployment mode matrix

Before committing to containers and externals, enumerate any supported modes that materially change runtime boundaries. At minimum check:

- process-local versus external state backends
- single-binary versus split-service runtime modes
- optional versus required externals
- dev/test quickstart modes versus persistent production modes

For each meaningful mode, note:

- what changes boundary type
- what stays the same
- whether the difference belongs in the canonical model, a deployment view, or view notes

Reason:
Many repos support both in-process and externalized modes. Failing to model that split is a common source of false external dependencies and incorrect container boundaries.

### 6. Identify canonical architecture elements

Populate the canonical model with normalized, deduplicated elements.

Required questions:

- what runs as a separate process or deployable unit?
- what stores persistent state?
- what external systems matter?
- what meaningful internal modules exist?
- who owns what data?
- what is the system of record for major entities?

Do not create near-duplicate elements such as `Order Service`, `Orders API`, and `Order Backend` unless evidence shows they are distinct.
Classify each important data object as one of:

- authoritative system of record
- local working state
- cache or derived state
- external source of truth

Do a data coverage pass before moving on:

- enumerate persisted entities surfaced by storage interfaces, migrations, schemas, or first-class CRUD APIs
- ensure each important entity appears in `owned_data` and, where appropriate, `system_of_record`
- check that no entity is accidentally assigned to two systems of record without an explicit reason

If a dependency is configuration-gated and not required for baseline operation, model it as optional external infrastructure unless it owns core business state.

When a component appears to submit work to an external system, inspect the transport layer before assigning the external relationship. Search for client, sender, adapter, transport, gateway, or relay abstractions so you do not over-attribute transport behavior to an orchestrator, tracker, or controller that merely delegates into a lower layer.

### 6b. Cross-cutting dependency analysis

After identifying canonical elements, check which internal modules or crates are consumed by multiple runtime units. This catches shared infrastructure that crosses container boundaries.

For each runtime unit (container), inspect its dependency declarations:

- Rust: check `Cargo.toml` dependencies for references to other workspace crates
- Node/TS: check `package.json` dependencies for workspace packages
- Go: check `go.mod` or import paths for internal packages
- Python: check imports of sibling packages
- Java/Kotlin: check Gradle/Maven module dependencies

For any internal module depended on by 2+ runtime units:

- flag it as a shared module
- decide whether to model it as a component under its primary consumer (with a note about shared usage) or as a standalone container/library element
- ensure relationships from all consumers are represented in the model

This step prevents the common mistake of attributing a shared module to only one container while other containers silently depend on it.

### 7. Identify relationships and critical workflows

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
- bootstrap or provisioning path when the system is not meaningfully usable without initial setup
- primary business transaction
- background processing or async propagation
- any path that involves external system dependencies not visible in the container view (e.g., an API layer performing computation against an external system beyond simple routing)

API/RPC containers are frequently assumed to be stateless thin proxies. Do not accept this assumption without checking the container's actual dependencies. If an API layer performs computation (validation, estimation, transformation, simulation) beyond routing, model those dependencies explicitly.

Before writing views, do a relationship preflight. For each important relationship, note:

- `relationship_id`
- source abstraction level
- target abstraction level
- allowed view types

If the relationship would force mixed abstraction levels in a view, change the model or use a different view.

For config-gated behavior, record that conditionality explicitly. If a relationship depends on enabled namespaces, feature flags, optional integrations, or deployment mode, preserve the relationship in the canonical model when it is real, but call out the condition in view notes, assumptions, or unknowns instead of implying the traffic is always active.

Before finalizing sequence views, cross-check step order against the actual handler/command path for that workflow. Do not let a plausible conceptual flow override the real execution order.

### 8. Cross-check operational reality

Inspect deployment and operational artifacts:

- deployment manifests
- CI/CD
- runtime env config
- feature flags
- observability config
- runbooks

Reason:
Static code alone often misstates runtime truth.

### 9. Build the canonical model first

Write `architecture/model.yaml` before writing any views.

The model is the only place where architecture facts are defined. Views only reference model IDs and filter/present them.

### 10. Derive views from the canonical model

Apply strict view rules:

- `system_context`: only the system of interest, people, and external systems
- `container`: only deployable/runtime units, datastores, queues/brokers, and relevant externals
- `component`: only meaningful internal modules within one container
- `sequence`: only previously defined model elements; do not invent ad hoc participants
- `deployment`: only nodes, zones, and placement when topology is architecturally relevant

Operational view rules:

- If a runtime role can run split or collocated, keep the role in the container view and show the collocation choice only in deployment notes or a deployment view.
- Component views may include components from exactly one parent container plus peer containers or external systems when needed for context.
- Component views must never include components from multiple parent containers.
- If a relationship references a foreign component, replace that foreign component with its parent container in the view.
- For sequence views, check each step against canonical relationship direction. Request steps may reference a matching relationship ID; response steps should either reference a reverse relationship that exists in the model or omit `relationship_id`.

### 11. Write summary and diff artifacts

Write `summary.md` using the fixed structure in the reference file.

In update mode, write `diff.yaml` with:

- added elements
- removed elements
- changed elements
- added relationships
- removed relationships
- changed relationships
- added or removed views

### 12. Validate before finishing

Run a lightweight consistency pass after generation. At minimum verify:

- every element ID referenced by a view exists in `model.yaml`
- every relationship ID referenced by a view exists in `model.yaml`
- every sequence participant exists in `model.yaml`
- every sequence step source/target exists in `model.yaml`
- no important persisted entity surfaced by storage or CRUD APIs is missing from ownership fields
- no data object is assigned to multiple systems of record without explicit justification
- sequence step ordering matches the actual handler/command path for the modeled workflow
- protocol labels are directly evidenced, or intentionally generalized when multiple transports are supported
- deployment-mode differences that materially change boundaries are either modeled explicitly or called out in notes/assumptions/unknowns
- every sequence step that includes `relationship_id` uses a relationship whose direction matches the step source and target
- component views contain components from only one parent container
- system-context and container views contain only allowed kinds
- deployment placements reference declared deployment nodes and existing deployable/container elements
- views do not reference relationships whose endpoints are absent from that view
- manifest scope paths match the actual repository-under-test path and output location supplied for the run
- for each container, its declared relationships account for its actual code dependencies on other containers' internal modules (cross-check dependency manifests against modeled relationships)

If validation fails, fix the artifacts before completing the task.

### 13. Handoff to diagram skill (required)

After architecture artifacts are complete for the current draft/final revision, hand off to `architect-diagram`.

Pass it:

- the parent output folder containing `architecture/`
- the generated `manifest.yaml`, `model.yaml`, and `views/*.yaml`

Expected default visible output in the same artifact package:

- `architecture/diagram.html` (primary interactive diagram)

Optional only when the user explicitly requests it:

- `architecture/diagram-prompt.md` via `architect-diagram-prompt`

Present the rendered diagram as part of the same discovery response so the diagram step feels automatic, not separately requested.
Do not generate `architecture/diagram.html` or `architecture/diagram-prompt.md` directly in this skill; use the dedicated diagram skills for those outputs.

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
Do not let deployment modes, CLIs, or launch commands become containers when they only package existing runtime roles.

## Data Ownership Rules

Whenever applicable, every container or component in the canonical model should declare:

- `owned_data`
- `system_of_record`

If ownership is unclear, record an unknown rather than omitting the issue silently.
Be explicit about the difference between:

- owned working state
- caches or derived state
- external source-of-truth data

If an element does not authoritatively own an entity, do not imply that it does.

## Common Mistakes To Avoid

Do not:

- start diagramming before identifying repo archetype and runtime boundaries
- confuse folders with containers
- create one giant view containing multiple abstraction levels
- generate views before the canonical model exists
- infer ownership from names alone
- ignore data ownership, dual writes, caches, or system-of-record questions
- let docs override stronger runtime evidence
- let packaging modes or docker-compose service names define containers without confirming runtime responsibility
- pull optional adapters into the core architecture without evidence that they own important state or runtime behavior
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
7. a post-generation validation pass has been completed and any reference or abstraction-level errors have been fixed
8. `architecture/diagram.html` has been generated for the current artifact set via `architect-diagram`
9. if requested, `architecture/diagram-prompt.md` has been generated for the current artifact set via `architect-diagram-prompt`


## Sequence View Policy (default)

- Do not generate sequence views by default.
- Generate sequence views only when the user explicitly requests them.
