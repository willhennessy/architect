# Architecture Output Contract (Shared)

This schema is shared by:

- `architect-init`
- `architect-plan`

Both skills must emit architecture artifacts that conform to this contract.

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

`model.yaml` is the source of truth. All views must reference model IDs rather than redefining architecture facts.

## `manifest.yaml`

Purpose:
Index generated artifacts and capture scope, mode, and evidence basis.

Schema:

```yaml
version: 2
system_name: "<system name>"
generated_by_skill: "<architect-init|architect-plan>"
mode: "<initial|update>"
evidence_basis: "<code|plan|mixed>"
architecture_state: "<proposed|approved|implementing|drifted>"   # optional
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
      - "<optional alias>"
    kind: "<person|software_system|external_system|container|component|database|queue|cache|deployment_node|library_module>"
    c4_level: "<context|container|component|deployment>"
    description: "<what it is>"
    responsibility: "<primary responsibility>"
    technology: "<primary technology or blank>"
    owned_data:
      - "<data entity>"
    system_of_record:
      - "<authoritative entities>"
    runtime_boundary: "<process|deployable|internal_module|external|data_store|network_zone>"
    deployable: <true|false>
    external: <true|false>
    parent_id: "<required for components; blank otherwise>"
    source_paths:
      - "<repo-relative path or plan://... reference>"
    tags:
      - "<optional tag>"
    confidence: "<confirmed|strong_inference|weak_inference>"
    evidence_ids:
      - "<evidence id>"
relationships:
  - id: "<stable id>"
    source_id: "<element id>"
    target_id: "<element id>"
    label: "<relationship label>"
    interaction_type: "<uses|calls|publishes|subscribes|reads|writes|stores|authenticates_with|renders|triggers|contains|deploys_to>"
    directionality: "<unidirectional|bidirectional>"
    sync_async: "<sync|async|storage|human|n_a>"
    protocol: "<https|grpc|sql|kafka|s3|in_process|manual|n_a|blank>"
    data_objects:
      - "<data object>"
    confidence: "<confirmed|strong_inference|weak_inference>"
    evidence_ids:
      - "<evidence id>"
evidence:
  - id: "<evidence id>"
    path: "<repo-relative path or plan://... reference>"
    kind: "<runtime_entrypoint|deploy_config|api_schema|migration|infra|queue_definition|code_path|doc|directory_name|plan_requirement|plan_constraint|plan_assumption|plan_tradeoff|user_intent|diagram_annotation>"
    strength: "<high|medium|low>"
    reason: "<why this source supports the model>"
unknowns:
  - "<open question>"
assumptions:
  - text: "<assumption>"
    confidence: "<strong_inference|weak_inference>"
```

### Required Modeling Rules

- Every element must include `id`, `name`, `kind`, `c4_level`, `description`, `responsibility`, `owned_data`, `system_of_record`, `runtime_boundary`, `source_paths`, `confidence`, and `evidence_ids`.
- Every relationship must include `id`, `source_id`, `target_id`, `label`, `interaction_type`, `directionality`, `sync_async`, `data_objects`, `confidence`, and `evidence_ids`.
- `component` elements must set `parent_id`.
- `container` elements must not set `parent_id`.
- `library_package` repos may use `library_module` elements instead of containers when no deployable runtime exists.

## View Files

Views are filtered presentations of the canonical model.

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

Allowed kinds:

- `person`
- `software_system`
- `external_system`

#### `container`

Allowed kinds:

- `person`
- `software_system`
- `external_system`
- `container`
- `database`
- `queue`
- `cache`

#### `component`

Additional required field:

```yaml
parent_container_id: "<container id>"
```

Component views must only include components from one parent container.

### `sequence`

Sequence views must reference only model-defined elements.

Schema:

```yaml
version: 2
id: "<view id>"
type: "sequence"
title: "<title>"
audience:
  - "<audience>"
purpose: "<workflow this explains>"
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

### `deployment`

Additional required fields:

```yaml
deployment_node_ids:
  - "<deployment node id>"
placement:
  - node_id: "<deployment node id>"
    element_id: "<container id>"
```

Only emit deployment views when topology materially changes understanding.

## `summary.md`

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

## Key Decisions
- [DEC-001] <decision statement> | covers: <comma-separated element/relationship/view ids>

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
  - "<summary of significant deltas>"
```

## Planning Evidence Mapping

When producing artifacts from planning input (no codebase scan):

- Use `evidence_basis: plan` in `manifest.yaml`.
- Use `plan://...` references in `source_paths` and evidence `path`.
- Use evidence `kind` values from plan categories (`plan_requirement`, `plan_constraint`, `plan_assumption`, `plan_tradeoff`, `user_intent`, `diagram_annotation`).
- Keep confidence levels explicit and conservative.
