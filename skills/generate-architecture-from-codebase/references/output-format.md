# Output Format

This skill emits a canonical architecture model plus derived view files as structured text. Visualization is out of scope.

Use YAML unless the user explicitly requests another structured text format.

Default output tree:

```text
architecture/
  manifest.yaml
  model.yaml
  summary.md
  diff.yaml                 # update mode only
  views/
    system-context.yaml
    container.yaml
    component-<container-name>.yaml
    sequence-<workflow-name>.yaml
    deployment.yaml
```

Use lowercase kebab-case for file names and IDs where practical.

## Canonical Model First

`model.yaml` is the source of truth. All view files must reference model IDs rather than redefining architecture facts. Do not invent view-local elements or relationships.

## `manifest.yaml`

Purpose:
Index the artifacts and record scope, mode, archetype, and modeling assumptions.

Schema:

```yaml
version: 2
system_name: "<system name>"
generated_by_skill: "generate-architecture-from-codebase"
mode: "<initial|update>"
repo_archetype: "<library_package|frontend_only_app|modular_monolith|service_oriented_backend|full_stack_product|infrastructure_repo>"
modeling_style:
  primary: "C4"
  supplemental:
    - "Sequence"
    - "Deployment"
scope:
  in_scope:
    - "<system or repo scope>"
  out_of_scope:
    - "<known exclusions>"
audiences:
  - "new_hires"
  - "pms"
  - "senior_architects"
artifacts:
  - id: "model"
    path: "architecture/model.yaml"
    type: "canonical_model"
    status: "complete"
  - id: "system-context"
    path: "architecture/views/system-context.yaml"
    type: "system_context"
    status: "complete"
assumptions:
  - text: "<assumption>"
    confidence: "strong_inference"
unknowns:
  - "<unknown>"
overall_summary: "<2-4 sentence summary>"
```

## `model.yaml`

Purpose:
Represent the canonical architecture graph and supporting evidence.

Schema:

```yaml
version: 2
system_name: "<system name>"
repo_archetype: "<library_package|frontend_only_app|modular_monolith|service_oriented_backend|full_stack_product|infrastructure_repo>"
elements:
  - id: "<stable id>"
    name: "<canonical display name>"
    aliases:
      - "<optional alternate names from code or docs>"
    kind: "<person|software_system|external_system|container|component|database|queue|cache|deployment_node|library_module>"
    c4_level: "<context|container|component|deployment>"
    description: "<what it is>"
    responsibility: "<primary responsibility>"
    technology: "<primary technology or blank>"
    owned_data:
      - "<data entities primarily owned here>"
    system_of_record:
      - "<entities for which this element is authoritative>"
    runtime_boundary: "<process|deployable|internal_module|external|data_store|network_zone>"
    deployable: <true|false>
    external: <true|false>
    parent_id: "<required for components; blank otherwise>"
    source_paths:
      - "<repo-relative path>"
    tags:
      - "<optional tags>"
    confidence: "<confirmed|strong_inference|weak_inference>"
    evidence_ids:
      - "<evidence id>"
relationships:
  - id: "<stable id>"
    source_id: "<element id>"
    target_id: "<element id>"
    label: "<meaningful relationship label>"
    interaction_type: "<uses|calls|publishes|subscribes|reads|writes|stores|authenticates_with|renders|triggers|contains|deploys_to>"
    directionality: "<unidirectional|bidirectional>"
    sync_async: "<sync|async|storage|human|n_a>"
    protocol: "<https|grpc|sql|kafka|s3|in_process|manual|blank>"
    data_objects:
      - "<order|invoice|session|...>"
    confidence: "<confirmed|strong_inference|weak_inference>"
    evidence_ids:
      - "<evidence id>"
evidence:
  - id: "<evidence id>"
    path: "<repo-relative path>"
    kind: "<runtime_entrypoint|deploy_config|api_schema|migration|infra|queue_definition|code_path|doc|directory_name>"
    strength: "<high|medium|low>"
    reason: "<why this source supports the model>"
unknowns:
  - "<open question>"
assumptions:
  - text: "<assumption>"
    confidence: "<strong_inference|weak_inference>"
```

### Required Modeling Rules

- Every element must have `id`, `name`, `kind`, `c4_level`, `description`, `responsibility`, `owned_data`, `system_of_record`, `runtime_boundary`, `source_paths`, `confidence`, and `evidence_ids`.
- Every relationship must have `id`, `source_id`, `target_id`, `label`, `interaction_type`, `directionality`, `sync_async`, `data_objects`, `confidence`, and `evidence_ids`.
- `component` elements must set `parent_id`.
- `container` elements must not set a `parent_id`.
- `library_package` repos may use `library_module` elements instead of containers when no deployable runtime exists.

## View Files

Views are filtered presentations of the canonical model. They may add audience and narrative metadata, but they must not redefine element facts.

Common schema:

```yaml
version: 2
id: "<view id>"
type: "<system_context|container|component|sequence|deployment>"
title: "<title>"
audience:
  - "<audience>"
purpose: "<single clear question this view answers>"
scope: "<what is included>"
source_model: "architecture/model.yaml"
element_ids:
  - "<element id>"
relationship_ids:
  - "<relationship id>"
assumptions:
  - text: "<assumption>"
    confidence: "<strong_inference|weak_inference>"
unknowns:
  - "<open question>"
notes:
  - "<note>"
```

### Level Rules

#### `system_context`

Allowed element kinds:

- `person`
- `software_system`
- `external_system`

Disallowed:

- `component`
- `database`
- `queue`
- `cache`

#### `container`

Allowed element kinds:

- `person`
- `software_system`
- `external_system`
- `container`
- `database`
- `queue`
- `cache`

Disallowed:

- `component`
- `library_module`

#### `component`

Purpose:
Show meaningful internal modules inside exactly one parent container.

Additional required field:

```yaml
parent_container_id: "<container id>"
```

Allowed element kinds:

- `component`
- `database`
- `queue`
- `cache`
- external dependencies already defined in the model when necessary

Do not include components from multiple parent containers in one component view.

### `sequence`

Sequence views must reference only elements already defined in `model.yaml`.

Schema:

```yaml
version: 2
id: "<view id>"
type: "sequence"
title: "<title>"
audience:
  - "<audience>"
purpose: "<what workflow this explains>"
scope: "<workflow scope>"
source_model: "architecture/model.yaml"
participant_ids:
  - "<element id>"
steps:
  - order: 1
    source_id: "<element id>"
    target_id: "<element id>"
    relationship_id: "<optional relationship id>"
    label: "<step description>"
    sync_async: "<sync|async|storage|human|n_a>"
    data_objects:
      - "<data object>"
    confidence: "<confirmed|strong_inference|weak_inference>"
    evidence_ids:
      - "<evidence id>"
assumptions: []
unknowns: []
notes: []
```

Do not invent ad hoc sequence participants.

### `deployment`

Purpose:
Show placement of deployable containers into nodes, zones, regions, or networks when topology matters.

Additional required fields:

```yaml
deployment_node_ids:
  - "<deployment node id>"
placement:
  - node_id: "<deployment node id>"
    element_id: "<container id>"
```

Only create this view if topology materially changes understanding of the system.

## `summary.md`

Purpose:
Provide a stable executive summary of the generated model.

Use this fixed structure:

```md
# Architecture Summary

## System Purpose
<1 short paragraph>

## Repo Archetype
<one of the defined archetypes and why>

## Primary Containers or Modules
- <name>: <responsibility>

## Critical Flows
- <flow>: <why it matters>

## Data Ownership Notes
- <entity>: <owner or system of record>

## Major Risks or Unknowns
- <risk or unknown>

## Recommended Next Reads
- `<path>`: <why>

## Artifact Index
- `architecture/model.yaml`: canonical architecture model
- `architecture/views/system-context.yaml`: system context view
```

## `diff.yaml`

Required in `update` mode.

Schema:

```yaml
version: 2
mode: "update"
baseline_artifacts:
  model: "<path to previous model if known>"
changes:
  added_elements:
    - "<element id>"
  removed_elements:
    - "<element id>"
  changed_elements:
    - id: "<element id>"
      changed_fields:
        - "<field name>"
  added_relationships:
    - "<relationship id>"
  removed_relationships:
    - "<relationship id>"
  changed_relationships:
    - id: "<relationship id>"
      changed_fields:
        - "<field name>"
  added_views:
    - "<view id>"
  removed_views:
    - "<view id>"
notes:
  - "<summary of significant architectural deltas>"
```

## Minimal Example

```yaml
version: 2
system_name: "Order Platform"
repo_archetype: "service_oriented_backend"
elements:
  - id: "order-api"
    name: "Order API"
    aliases: ["orders-service"]
    kind: "container"
    c4_level: "container"
    description: "Exposes order operations."
    responsibility: "Create and query orders."
    technology: "Node.js"
    owned_data: ["order"]
    system_of_record: ["order"]
    runtime_boundary: "deployable"
    deployable: true
    external: false
    parent_id: ""
    source_paths: ["services/order-api"]
    tags: ["backend"]
    confidence: "strong_inference"
    evidence_ids: ["ev-entry", "ev-routes"]
relationships:
  - id: "web-app-calls-order-api"
    source_id: "web-app"
    target_id: "order-api"
    label: "Calls order endpoints"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects: ["order"]
    confidence: "confirmed"
    evidence_ids: ["ev-client"]
evidence:
  - id: "ev-entry"
    path: "services/order-api/src/main.ts"
    kind: "runtime_entrypoint"
    strength: "high"
    reason: "Defines the API process entrypoint."
unknowns: []
assumptions: []
```
