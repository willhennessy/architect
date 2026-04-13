# Interactive Diagram Prompt Specification

Use this specification when constructing the interactive prompt inside `diagram-prompt.md`.

Purpose:
- produce one interactive drill-down architecture diagram from the provided architecture artifacts
- keep all rendered entities grounded in `model.yaml` + `views/*.yaml`

## Prompt Structure (required order)

Use these sections in order when writing the prompt for Claude Imagine.

### 1) Role statement

The prompt must start by assigning a role that combines:
- technical domain expertise for the target system
- interactive visualization expertise

Example pattern:
- `You are a senior <language/domain> engineer and interactive visualization designer.`

### 2) Context block

State that:
- architecture artifacts are included in the uploaded bundle
- `model.yaml` is the canonical source of truth
- view files represent C4 levels and supplemental views

### 3) Interactive drill-down behavior

#### Navigation model (progressive drill-down)

The prompt must require this behavior:

1. **Entry: System Context**
   - Start at system context (system of interest + external actors + relationships).
   - Elements with child containers must be visibly drillable.

2. **Level 2: Container view**
   - On system/bounded-context click, show deployable units, datastores, queues, and relationships.
   - Containers with component views must be visibly drillable.

3. **Level 3: Component view**
   - On container click, show internal modules/components and relationships.
   - Components with deeper detail must be visibly drillable.

4. **Level 4: Code detail (when available)**
   - On deepest component click, show code-level detail if available.
   - If unavailable, show a detail panel (description, responsibilities, technology, owned data).

#### Breadcrumb behavior

The prompt must require:
- persistent breadcrumb at top
- format like `System > Container > Component` for current depth
- clickable breadcrumb segments for upward navigation
- explicit Back control

#### Visual affordances

The prompt must require:
- visible indicators for drillable nodes (hover/border/icon)
- non-drillable nodes must not look drillable
- smooth or explicit transitions between levels
- consistent color semantics by element type

#### Relationship rendering

The prompt must require:
- render relationships relevant to current view
- label relationships with description and protocol/technology when available
- represent out-of-scope endpoints as simplified edge/reference nodes (not full expansion)

#### Detail panels

The prompt must require element detail display containing:
- name + type
- technology/language
- description + responsibilities
- owned data (if any)
- confidence level (`confirmed|strong_inference|weak_inference`)

Inspection and drill-down interactions must be distinguishable.

### 4) Data sourcing constraints

The prompt must enforce:
- source only from provided architecture artifacts
- no invented elements, edges, metadata, or IDs
- use `manifest.yaml` to determine available views and drill-down mapping
- treat missing deeper views as leaf-node detail panels

### 5) Layout and style constraints

The prompt must enforce:
- clean, professional engineering-oriented visual style
- readability over visual density
- sequence views (if present) exposed in separate tab/panel, not mixed into drill-down hierarchy
- fully self-contained HTML (inline CSS/JS, no external dependencies)

## Prompt Assembly Checklist

Before finalizing the prompt section in `diagram-prompt.md`, verify:

- role statement matches actual system stack/domain
- system name matches artifact content
- drill-down levels match actual available views
- wording explicitly forbids invention
- breadcrumb + back behavior is explicitly required
- sequence handling is specified as separate panel/tab
