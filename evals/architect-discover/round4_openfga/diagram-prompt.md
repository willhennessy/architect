# Diagram Prompt Bundle

Upload this file to Claude Chat desktop and use the prompt below.

## Prompt

```text
You are a staff Go backend architect with deep expertise in authorization systems, gRPC/HTTP service design, and C4-based architecture communication.

Use the embedded virtual architecture folder in this uploaded document as the source of truth. The document contains:
- a virtual directory tree
- exact file contents for each architecture artifact

Treat those embedded files as if they were present on disk under:

architecture/

This bundle contains a semantic architecture representation of the OpenFGA codebase using a canonical model plus derived C4-style views and sequence workflows.

Your task:
- Read the embedded files carefully.
- Draw the architecture diagrams from those artifacts.

Requirements:
- Produce visuals for the system context, container view, and component view.
- Also draw the three sequence diagrams for store bootstrap, permission check, and tuple write.
- Keep the diagrams faithful to the canonical model and the view files; do not invent extra elements or relationships.
- Preserve the deployment-mode nuance that persistent SQL backends are external while the memory backend is process-local.
- Preserve the command layer between transport handlers and graph/storage logic.
- Mark optional or configuration-gated behavior clearly where relevant, especially OIDC and experimental AuthZEN support.
- Optimize for clarity and technical accuracy over decoration.
- If you need to choose a diagram notation, prefer clean C4-style diagrams for static views and standard sequence diagrams for workflows.
```

## Virtual Tree

```text
architecture/
  manifest.yaml
  model.yaml
  summary.md
  views/
    component-openfga-server.yaml
    container.yaml
    sequence-permission-check.yaml
    sequence-store-bootstrap.yaml
    sequence-write-relationship-tuples.yaml
    system-context.yaml
```

## Files

### `architecture/manifest.yaml`

```yaml
version: 2
system_name: "OpenFGA"
generated_by_skill: "architect-discover"
mode: "initial"
repo_archetype: "modular_monolith"
modeling_style:
  primary: "C4"
  supplemental:
    - "Sequence"
scope:
  in_scope:
    - "The OpenFGA server runtime implemented by `openfga run`, including its API, access-control, permission-evaluation, and datastore integration paths."
  out_of_scope:
    - "External SDKs, CLI clients, and Terraform providers that live in other repositories."
    - "Environment-specific ingress, orchestration, and multi-cluster deployment topologies beyond the repo's local compose example."
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
  - id: "container"
    path: "architecture/views/container.yaml"
    type: "container"
    status: "complete"
  - id: "component-openfga-server"
    path: "architecture/views/component-openfga-server.yaml"
    type: "component"
    status: "complete"
  - id: "sequence-permission-check"
    path: "architecture/views/sequence-permission-check.yaml"
    type: "sequence"
    status: "complete"
  - id: "sequence-write-relationship-tuples"
    path: "architecture/views/sequence-write-relationship-tuples.yaml"
    type: "sequence"
    status: "complete"
  - id: "sequence-store-bootstrap"
    path: "architecture/views/sequence-store-bootstrap.yaml"
    type: "sequence"
    status: "complete"
  - id: "summary"
    path: "architecture/summary.md"
    type: "summary"
    status: "complete"
assumptions:
  - text: "The local playground is modeled as part of the main OpenFGA server container because `openfga run` starts it from the same process and the repo does not define it as an independently deployable unit."
    confidence: "strong_inference"
  - text: "Persistent SQL backends are modeled as an external dependency, while the in-memory backend is modeled inside the server because it is process-local and ephemeral."
    confidence: "strong_inference"
unknowns:
  - "The repo documents production ingress and multi-instance deployments, but the exact canonical deployment topology is not enforced by code in this repository."
  - "Whether the optional internal access-control store and OIDC integration are enabled depends on deployment configuration."
overall_summary: "OpenFGA is a modular monolith centered on one Go server runtime. The server exposes gRPC natively, serves HTTP through an in-process gRPC gateway, optionally hosts a local playground, and persists authorization state through pluggable datastore adapters that can target either process-local memory or external SQL backends. Permission-evaluation workloads are handled by dedicated command, graph, and planner modules with shared caching and optional weighted-graph execution."
```

### `architecture/model.yaml`

```yaml
version: 2
system_name: "OpenFGA"
repo_archetype: "modular_monolith"
elements:
  - id: "client-applications"
    name: "Client Applications"
    aliases:
      - "SDK consumers"
      - "services using OpenFGA"
    kind: "software_system"
    c4_level: "context"
    description: "Applications and services that call OpenFGA to manage authorization state and evaluate permissions."
    responsibility: "Submit API requests over HTTP or gRPC to store models and tuples and to evaluate authorization decisions."
    technology: "HTTP, gRPC"
    owned_data:
      - "Application-specific authorization requests"
    system_of_record: []
    runtime_boundary: "external"
    deployable: false
    external: true
    source_paths:
      - "README.md"
      - "docs/architecture/architecture.md"
    tags:
      - "entrypoint-consumer"
    confidence: "confirmed"
    evidence_ids:
      - "e-readme"
      - "e-doc-architecture"
  - id: "openfga-system"
    name: "OpenFGA"
    aliases:
      - "openfga"
    kind: "software_system"
    c4_level: "context"
    description: "Fine-grained authorization service inspired by Zanzibar."
    responsibility: "Provide APIs to manage authorization stores, models, and tuples and to answer authorization queries."
    technology: "Go"
    owned_data:
      - "Authorization stores"
      - "Authorization models"
      - "Relationship tuples"
      - "Assertions"
    system_of_record: []
    runtime_boundary: "deployable"
    deployable: false
    external: false
    source_paths:
      - "README.md"
      - "cmd/openfga/main.go"
      - "cmd/run/run.go"
    tags:
      - "system-in-scope"
    confidence: "confirmed"
    evidence_ids:
      - "e-readme"
      - "e-main"
      - "e-run"
  - id: "oidc-issuer"
    name: "OIDC Issuer"
    aliases:
      - "Authorization server"
    kind: "external_system"
    c4_level: "context"
    description: "External identity provider used when OpenFGA validates bearer tokens with OIDC."
    responsibility: "Issue tokens and expose signing keys and issuer metadata for token verification."
    technology: "OIDC, JWKS"
    owned_data:
      - "Client credentials"
      - "JWT signing keys"
    system_of_record:
      - "Client credentials"
      - "JWT signing keys"
    runtime_boundary: "external"
    deployable: false
    external: true
    source_paths:
      - "cmd/run/run.go"
      - "docs/architecture/architecture.md"
    tags:
      - "optional-external"
      - "identity"
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-doc-architecture"
  - id: "persistent-state-backend"
    name: "Persistent State Backend"
    aliases:
      - "Postgres/MySQL/SQLite backend"
    kind: "external_system"
    c4_level: "context"
    description: "External persistent backend selected at runtime for OpenFGA state in non-memory deployments."
    responsibility: "Persist stores, authorization models, relationship tuples, assertions, and change history when OpenFGA is not running with the in-memory adapter."
    technology: "PostgreSQL, MySQL, SQLite"
    owned_data:
      - "Authorization stores"
      - "Authorization models"
      - "Relationship tuples"
      - "Tuple change history"
    system_of_record:
      - "Authorization stores"
      - "Authorization models"
      - "Relationship tuples"
      - "Assertions"
      - "Tuple change history"
    runtime_boundary: "external"
    deployable: false
    external: true
    source_paths:
      - "cmd/run/run.go"
      - "docker-compose.yaml"
      - "pkg/storage/storage.go"
    tags:
      - "persistence"
      - "optional-external"
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-compose"
      - "e-storage"
  - id: "telemetry-collector"
    name: "Telemetry Collector"
    aliases:
      - "OTel collector"
    kind: "external_system"
    c4_level: "context"
    description: "Optional external observability sink for traces and metrics emitted by OpenFGA."
    responsibility: "Receive OpenTelemetry traces and telemetry exports from the server runtime."
    technology: "OpenTelemetry"
    owned_data:
      - "Trace spans"
      - "Operational metrics"
    system_of_record: []
    runtime_boundary: "external"
    deployable: false
    external: true
    source_paths:
      - "cmd/run/run.go"
      - "telemetry/otel-collector-config.yaml"
      - "docs/architecture/architecture.md"
    tags:
      - "optional-external"
      - "observability"
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-otel-config"
      - "e-doc-architecture"
  - id: "openfga-server"
    name: "OpenFGA Server"
    aliases:
      - "openfga run"
    kind: "container"
    c4_level: "container"
    description: "Primary Go runtime that hosts the OpenFGA APIs, the optional experimental AuthZEN APIs, the optional HTTP gateway and playground, and the authorization execution engine."
    responsibility: "Handle API traffic, enforce authn/authz, resolve authorization models, evaluate permission graphs, and coordinate persistence."
    technology: "Go, gRPC, grpc-gateway, net/http"
    owned_data:
      - "Request-scoped evaluation context"
      - "Shared resolver caches"
      - "Operational metrics"
      - "Process-local authorization state when using the in-memory backend"
    system_of_record: []
    runtime_boundary: "process"
    deployable: true
    external: false
    source_paths:
      - "cmd/openfga/main.go"
      - "cmd/run/run.go"
      - "pkg/server/server.go"
    tags:
      - "api"
      - "runtime"
    confidence: "confirmed"
    evidence_ids:
      - "e-main"
      - "e-run"
      - "e-server"
  - id: "api-surface"
    name: "API Surface"
    aliases:
      - "gRPC server"
      - "HTTP gateway"
      - "Playground handler"
    kind: "component"
    c4_level: "component"
    description: "Transport-facing layer that registers the OpenFGA APIs, can register experimental AuthZEN APIs, proxies HTTP to gRPC, and optionally serves the local playground."
    responsibility: "Accept client requests, normalize protocol concerns, and hand off validated calls to service logic."
    technology: "gRPC, grpc-gateway, net/http"
    owned_data:
      - "HTTP and gRPC request/response metadata"
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "openfga-server"
    source_paths:
      - "cmd/run/run.go"
      - "pkg/server/server.go"
    tags:
      - "transport"
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-server"
  - id: "command-services"
    name: "Command Services"
    aliases:
      - "business logic layer"
      - "pkg/server/commands"
    kind: "component"
    c4_level: "component"
    description: "Business-logic layer that sits between transport handlers and lower-level graph and storage modules."
    responsibility: "Validate request-specific semantics, sequence store/model/tuple operations, and invoke graph or storage dependencies from transport-agnostic command objects."
    technology: "Go command objects"
    owned_data:
      - "Operation-specific validation state"
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "openfga-server"
    source_paths:
      - "pkg/server/commands"
      - "AGENTS.md"
    tags:
      - "business-logic"
    confidence: "confirmed"
    evidence_ids:
      - "e-check-command"
      - "e-write-command"
      - "e-openfga-agents"
  - id: "auth-and-access-control"
    name: "Auth And Access Control"
    aliases:
      - "authentication middleware"
      - "authorizer"
    kind: "component"
    c4_level: "component"
    description: "Authentication and request-authorization layer covering preshared-key, OIDC, and optional access-control-store checks."
    responsibility: "Authenticate callers and decide whether an API invocation is permitted before business logic runs."
    technology: "Go middleware, OIDC"
    owned_data:
      - "Caller claims"
      - "Access-control check context"
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "openfga-server"
    source_paths:
      - "cmd/run/run.go"
      - "internal/authz/authz.go"
      - "internal/middleware/authn/authn.go"
    tags:
      - "security"
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-authz"
      - "e-authn-middleware"
  - id: "authorization-engines"
    name: "Authorization Engines"
    aliases:
      - "check resolver"
      - "planner"
      - "typesystem resolver"
    kind: "component"
    c4_level: "component"
    description: "Core evaluation modules that resolve authorization models, plan and execute graph traversals, and cache intermediate results for Check, ListObjects, and ListUsers."
    responsibility: "Turn authorization queries and contextual tuples into allow/deny or graph-expansion results."
    technology: "Go graph resolvers"
    owned_data:
      - "Resolved authorization model graphs"
      - "Intermediate permission-evaluation cache entries"
      - "Resolution metadata"
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "openfga-server"
    source_paths:
      - "pkg/server/check.go"
      - "pkg/server/commands/check_command.go"
      - "pkg/server/commands/reverseexpand"
      - "internal/graph"
      - "internal/modelgraph"
      - "internal/cachecontroller"
    tags:
      - "core-domain"
      - "query-engine"
    confidence: "confirmed"
    evidence_ids:
      - "e-check-rpc"
      - "e-check-command"
      - "e-server"
  - id: "datastore-adapters"
    name: "Datastore Adapters"
    aliases:
      - "storage adapters"
      - "tuple store"
    kind: "component"
    c4_level: "component"
    description: "Persistence abstraction and backend adapters for memory, Postgres, MySQL, and SQLite, including continuation-token handling and transactional tuple writes."
    responsibility: "Provide the read/write contract used by store, model, tuple, and query operations."
    technology: "Go storage interfaces, SQL adapters"
    owned_data:
      - "Continuation tokens"
      - "Persistence adapter configuration"
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "openfga-server"
    source_paths:
      - "pkg/storage/storage.go"
      - "pkg/storage/postgres"
      - "pkg/storage/mysql"
      - "pkg/storage/sqlite"
      - "pkg/storage/memory"
      - "pkg/server/commands/write.go"
    tags:
      - "persistence"
    confidence: "confirmed"
    evidence_ids:
      - "e-storage"
      - "e-run"
      - "e-write-command"
  - id: "in-memory-state-backend"
    name: "In-Memory State Backend"
    aliases:
      - "memory adapter"
    kind: "component"
    c4_level: "component"
    description: "Process-local backend used by the memory storage engine for local and ephemeral OpenFGA state."
    responsibility: "Hold stores, models, tuples, assertions, and change history inside the server process when the memory adapter is selected."
    technology: "Go in-memory storage"
    owned_data:
      - "Authorization stores"
      - "Authorization models"
      - "Relationship tuples"
      - "Assertions"
      - "Tuple change history"
    system_of_record:
      - "Authorization stores"
      - "Authorization models"
      - "Relationship tuples"
      - "Assertions"
      - "Tuple change history"
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "openfga-server"
    source_paths:
      - "pkg/storage/memory"
      - "cmd/run/run.go"
      - "README.md"
    tags:
      - "persistence"
      - "ephemeral"
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-storage"
      - "e-readme"
relationships:
  - id: "r-client-applications-use-openfga"
    source_id: "client-applications"
    target_id: "openfga-system"
    label: "Calls authorization management and query APIs"
    interaction_type: "uses"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: ""
    data_objects:
      - "Store metadata"
      - "Authorization models"
      - "Relationship tuples"
      - "Assertions"
      - "Check and list queries"
    confidence: "confirmed"
    evidence_ids:
      - "e-readme"
      - "e-doc-architecture"
  - id: "r-openfga-system-authenticates-with-oidc"
    source_id: "openfga-system"
    target_id: "oidc-issuer"
    label: "Validates bearer tokens when OIDC authn is enabled"
    interaction_type: "authenticates_with"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "OIDC issuer metadata"
      - "JWT signing keys"
      - "Access tokens"
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-doc-architecture"
  - id: "r-openfga-system-stores-state-in-persistent-backend"
    source_id: "openfga-system"
    target_id: "persistent-state-backend"
    label: "Persists state in external backends when not using the in-memory adapter"
    interaction_type: "stores"
    directionality: "unidirectional"
    sync_async: "storage"
    protocol: "sql"
    data_objects:
      - "Authorization stores"
      - "Authorization models"
      - "Relationship tuples"
      - "Assertions"
      - "Tuple change history"
    confidence: "confirmed"
    evidence_ids:
      - "e-compose"
      - "e-run"
      - "e-storage"
  - id: "r-openfga-system-publishes-telemetry"
    source_id: "openfga-system"
    target_id: "telemetry-collector"
    label: "Exports traces and metrics when telemetry is enabled"
    interaction_type: "publishes"
    directionality: "unidirectional"
    sync_async: "async"
    protocol: ""
    data_objects:
      - "Trace spans"
      - "Operational metrics"
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-otel-config"
      - "e-doc-architecture"
  - id: "r-openfga-system-contains-openfga-server"
    source_id: "openfga-system"
    target_id: "openfga-server"
    label: "Primary runtime implementation"
    interaction_type: "contains"
    directionality: "unidirectional"
    sync_async: "n_a"
    protocol: "in_process"
    data_objects: []
    confidence: "confirmed"
    evidence_ids:
      - "e-main"
      - "e-run"
  - id: "r-openfga-server-authenticates-with-oidc"
    source_id: "openfga-server"
    target_id: "oidc-issuer"
    label: "Retrieves issuer data for token validation"
    interaction_type: "authenticates_with"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "OIDC issuer metadata"
      - "JWT signing keys"
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-authz"
  - id: "r-openfga-server-stores-state-in-persistent-backend"
    source_id: "openfga-server"
    target_id: "persistent-state-backend"
    label: "Reads and writes authorization state through pluggable adapters in persistent deployments"
    interaction_type: "stores"
    directionality: "unidirectional"
    sync_async: "storage"
    protocol: "sql"
    data_objects:
      - "Authorization stores"
      - "Authorization models"
      - "Relationship tuples"
      - "Assertions"
      - "Tuple change history"
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-storage"
      - "e-compose"
  - id: "r-openfga-server-publishes-telemetry"
    source_id: "openfga-server"
    target_id: "telemetry-collector"
    label: "Emits traces and metrics"
    interaction_type: "publishes"
    directionality: "unidirectional"
    sync_async: "async"
    protocol: ""
    data_objects:
      - "Trace spans"
      - "Operational metrics"
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-otel-config"
  - id: "r-openfga-server-contains-api-surface"
    source_id: "openfga-server"
    target_id: "api-surface"
    label: "Hosts transport entrypoints"
    interaction_type: "contains"
    directionality: "unidirectional"
    sync_async: "n_a"
    protocol: "in_process"
    data_objects: []
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-server"
  - id: "r-openfga-server-contains-auth-access"
    source_id: "openfga-server"
    target_id: "auth-and-access-control"
    label: "Hosts authn and request authorization"
    interaction_type: "contains"
    directionality: "unidirectional"
    sync_async: "n_a"
    protocol: "in_process"
    data_objects: []
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-authz"
  - id: "r-openfga-server-contains-command-services"
    source_id: "openfga-server"
    target_id: "command-services"
    label: "Hosts transport-agnostic business commands"
    interaction_type: "contains"
    directionality: "unidirectional"
    sync_async: "n_a"
    protocol: "in_process"
    data_objects: []
    confidence: "confirmed"
    evidence_ids:
      - "e-check-command"
      - "e-write-command"
      - "e-openfga-agents"
  - id: "r-openfga-server-contains-authorization-engines"
    source_id: "openfga-server"
    target_id: "authorization-engines"
    label: "Hosts permission-evaluation logic"
    interaction_type: "contains"
    directionality: "unidirectional"
    sync_async: "n_a"
    protocol: "in_process"
    data_objects: []
    confidence: "confirmed"
    evidence_ids:
      - "e-check-rpc"
      - "e-check-command"
  - id: "r-openfga-server-contains-datastore-adapters"
    source_id: "openfga-server"
    target_id: "datastore-adapters"
    label: "Hosts storage abstraction and backend drivers"
    interaction_type: "contains"
    directionality: "unidirectional"
    sync_async: "n_a"
    protocol: "in_process"
    data_objects: []
    confidence: "confirmed"
    evidence_ids:
      - "e-storage"
      - "e-run"
  - id: "r-openfga-server-contains-in-memory-state-backend"
    source_id: "openfga-server"
    target_id: "in-memory-state-backend"
    label: "Hosts the process-local backend used by the memory adapter"
    interaction_type: "contains"
    directionality: "unidirectional"
    sync_async: "n_a"
    protocol: "in_process"
    data_objects: []
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-storage"
      - "e-readme"
  - id: "r-api-surface-calls-auth-access"
    source_id: "api-surface"
    target_id: "auth-and-access-control"
    label: "Invokes authentication and API authorization before handling requests"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "Bearer tokens"
      - "Preshared keys"
      - "Access-control context"
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-authz"
      - "e-stores-rpc"
  - id: "r-api-surface-calls-command-services"
    source_id: "api-surface"
    target_id: "command-services"
    label: "Delegates business operations to transport-agnostic command logic"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "Store operations"
      - "Authorization model operations"
      - "Tuple mutations"
      - "Check and list queries"
    confidence: "confirmed"
    evidence_ids:
      - "e-openfga-agents"
      - "e-stores-rpc"
      - "e-write-rpc"
      - "e-check-rpc"
  - id: "r-command-services-call-authorization-engines"
    source_id: "command-services"
    target_id: "authorization-engines"
    label: "Delegates graph-based permission evaluation and model-driven query execution"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "Check requests"
      - "ListObjects requests"
      - "ListUsers requests"
      - "Resolved authorization model IDs"
    confidence: "confirmed"
    evidence_ids:
      - "e-check-command"
      - "e-check-rpc"
      - "e-openfga-agents"
  - id: "r-command-services-call-datastore-adapters"
    source_id: "command-services"
    target_id: "datastore-adapters"
    label: "Reads and writes stores, models, tuples, assertions, and change logs"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "Store metadata"
      - "Authorization models"
      - "Relationship tuples"
      - "Assertions"
      - "Tuple change history"
    confidence: "confirmed"
    evidence_ids:
      - "e-stores-rpc"
      - "e-write-rpc"
      - "e-write-command"
      - "e-assertions-rpc"
  - id: "r-auth-access-authenticates-with-oidc"
    source_id: "auth-and-access-control"
    target_id: "oidc-issuer"
    label: "Fetches issuer configuration and keys when OIDC authn is enabled"
    interaction_type: "authenticates_with"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "OIDC issuer metadata"
      - "JWT signing keys"
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-authn-middleware"
  - id: "r-auth-access-calls-authorization-engines"
    source_id: "auth-and-access-control"
    target_id: "authorization-engines"
    label: "Uses permission checks against the access-control store for API authorization"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "Caller claims"
      - "Access-control tuples"
      - "Module permissions"
    confidence: "confirmed"
    evidence_ids:
      - "e-authz"
      - "e-check-rpc"
  - id: "r-authorization-engines-read-via-datastore-adapters"
    source_id: "authorization-engines"
    target_id: "datastore-adapters"
    label: "Reads models and tuples and records cache metadata during evaluation"
    interaction_type: "reads"
    directionality: "unidirectional"
    sync_async: "storage"
    protocol: "in_process"
    data_objects:
      - "Relationship tuples"
      - "Cache invalidation timestamps"
    confidence: "confirmed"
    evidence_ids:
      - "e-check-rpc"
      - "e-check-command"
      - "e-storage"
  - id: "r-datastore-adapters-store-state-in-persistent-backend"
    source_id: "datastore-adapters"
    target_id: "persistent-state-backend"
    label: "Implements backend-specific reads, writes, migrations, and continuation tokens for external persistence"
    interaction_type: "stores"
    directionality: "unidirectional"
    sync_async: "storage"
    protocol: "sql"
    data_objects:
      - "Authorization stores"
      - "Authorization models"
      - "Relationship tuples"
      - "Assertions"
      - "Tuple change history"
    confidence: "confirmed"
    evidence_ids:
      - "e-storage"
      - "e-write-command"
      - "e-run"
  - id: "r-datastore-adapters-store-state-in-memory-backend"
    source_id: "datastore-adapters"
    target_id: "in-memory-state-backend"
    label: "Persists state inside the server process when the memory adapter is selected"
    interaction_type: "stores"
    directionality: "unidirectional"
    sync_async: "storage"
    protocol: "in_process"
    data_objects:
      - "Authorization stores"
      - "Authorization models"
      - "Relationship tuples"
      - "Assertions"
      - "Tuple change history"
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-storage"
      - "e-readme"
evidence:
  - id: "e-readme"
    path: "README.md"
    kind: "doc"
    strength: "medium"
    reason: "Describes OpenFGA as a fine-grained authorization service with HTTP and gRPC APIs, optional playground, and supported storage backends."
  - id: "e-main"
    path: "cmd/openfga/main.go"
    kind: "runtime_entrypoint"
    strength: "high"
    reason: "Defines the root CLI and shows `run`, `migrate`, and `validatemodels` as first-class runtime entrypoints."
  - id: "e-run"
    path: "cmd/run/run.go"
    kind: "runtime_entrypoint"
    strength: "high"
    reason: "Constructs the main server runtime, selects datastore and authn methods, starts gRPC and HTTP servers, and optionally starts the playground."
  - id: "e-compose"
    path: "docker-compose.yaml"
    kind: "deploy_config"
    strength: "high"
    reason: "Shows the local deployment shape with Postgres, a migration step, and the `openfga run` server exposing HTTP, gRPC, playground, and metrics ports."
  - id: "e-server"
    path: "pkg/server/server.go"
    kind: "code_path"
    strength: "high"
    reason: "Defines the server object shared by the OpenFGA and AuthZEN APIs and its core runtime dependencies such as datastore, planner, caches, and authorizer."
  - id: "e-stores-rpc"
    path: "pkg/server/stores.go"
    kind: "code_path"
    strength: "high"
    reason: "Shows store-management RPC methods invoking authz checks and datastore-backed commands."
  - id: "e-write-rpc"
    path: "pkg/server/write.go"
    kind: "code_path"
    strength: "high"
    reason: "Shows tuple writes resolving the active typesystem, enforcing authz, and delegating persistence to the write command."
  - id: "e-check-rpc"
    path: "pkg/server/check.go"
    kind: "code_path"
    strength: "high"
    reason: "Shows the permission-check flow, including authz, feature-flagged weighted-graph execution, cache use, and graph resolver orchestration."
  - id: "e-check-command"
    path: "pkg/server/commands/check_command.go"
    kind: "code_path"
    strength: "high"
    reason: "Shows request validation, contextual tuple handling, cache invalidation, datastore wrapping, and graph resolver execution for Check."
  - id: "e-write-command"
    path: "pkg/server/commands/write.go"
    kind: "code_path"
    strength: "high"
    reason: "Shows write validation against the authorization model and transactional delete-then-insert persistence behavior."
  - id: "e-storage"
    path: "pkg/storage/storage.go"
    kind: "code_path"
    strength: "high"
    reason: "Defines the persistence contract for reading and writing tuples, models, stores, and paginated change streams."
  - id: "e-authz"
    path: "internal/authz/authz.go"
    kind: "code_path"
    strength: "high"
    reason: "Implements the optional access-control authorizer by translating API methods into internal permission checks against an access-control store."
  - id: "e-openfga-agents"
    path: "AGENTS.md"
    kind: "doc"
    strength: "medium"
    reason: "Documents the intended runtime layering as request -> middleware -> server handler -> command -> graph resolution -> storage."
  - id: "e-authn-middleware"
    path: "internal/middleware/authn/authn.go"
    kind: "code_path"
    strength: "high"
    reason: "Integrates authentication into the gRPC interceptor chain."
  - id: "e-assertions-rpc"
    path: "pkg/server/assertions.go"
    kind: "code_path"
    strength: "high"
    reason: "Shows assertions as first-class persisted API resources that resolve typesystems and call datastore-backed commands."
  - id: "e-authz-model-rpc"
    path: "pkg/server/authorization_models.go"
    kind: "code_path"
    strength: "high"
    reason: "Shows authorization-model publication and retrieval as first-class API operations with authz checks and command delegation."
  - id: "e-write-authzmodel-command"
    path: "pkg/server/commands/write_authzmodel.go"
    kind: "code_path"
    strength: "high"
    reason: "Shows authorization-model validation, ULID generation, schema checks, and persistence through the datastore interface."
  - id: "e-doc-architecture"
    path: "docs/architecture/architecture.md"
    kind: "doc"
    strength: "medium"
    reason: "Summarizes the intended high-level runtime and internal architecture and corroborates the major workflow categories."
  - id: "e-otel-config"
    path: "telemetry/otel-collector-config.yaml"
    kind: "infra"
    strength: "medium"
    reason: "Confirms the repo ships telemetry collector configuration for trace export."
unknowns:
  - "The repo supports several experimental graph-resolution modes, but the exact production default for weighted versus classic evaluation depends on deployment-level feature-flag configuration."
  - "The code supports access-control-store recursion for API authorization, but the common production enablement pattern is not fully specified in this repository."
assumptions:
  - text: "The model focuses on the `openfga run` server runtime and treats `migrate` and `validatemodels` as support commands rather than separate long-lived containers."
    confidence: "strong_inference"
  - text: "HTTP and gRPC are treated as one container because the HTTP API is implemented as an in-process gRPC gateway rather than a separately deployed service."
    confidence: "strong_inference"
```

### `architecture/summary.md`

```md
# OpenFGA Architecture Summary

OpenFGA is best modeled here as a modular monolith built around the `openfga run` server path. The runtime is a single Go process that exposes gRPC natively, serves HTTP through an in-process grpc-gateway, and can optionally host a local playground UI on a separate listener. The same runtime also wires in logging, validation, tracing, metrics, authentication middleware, and an experimental AuthZEN surface when that feature flag is enabled.

The main architectural boundaries inside that process are:

- `API Surface`: transport handlers for gRPC, HTTP, and the optional playground.
- `Auth And Access Control`: request authentication plus optional recursive authorization against a dedicated access-control store.
- `Command Services`: transport-agnostic business logic that sequences request validation, model resolution, graph execution, and persistence.
- `Authorization Engines`: typesystem resolution, graph and modelgraph execution, planner usage, and shared cache coordination for `Check`, `ListObjects`, and `ListUsers`.
- `Datastore Adapters`: the persistence contract plus backend implementations for memory, Postgres, MySQL, and SQLite.

In persistent deployments, the configured SQL backend is the authoritative system of record for authorization stores, models, tuples, assertions, and tuple change history. In local or ephemeral deployments, the in-memory adapter keeps that same state inside the server process instead. The server also supports optional external integrations for OIDC token validation and OpenTelemetry export.

Two workflows dominate the runtime:

1. Store bootstrap: a caller creates a store, then publishes an authorization model that defines the store's policy vocabulary.
2. Permission evaluation: the server authenticates and authorizes the caller, hands the request to the command layer, resolves the active authorization model, reads tuples through storage wrappers, and returns an allow/deny decision. Depending on feature flags, this can run through the classic graph resolver or the weighted-graph path.
3. Tuple mutation: the server resolves the active model, authorizes the caller with that model context, validates tuple semantics and request options, and performs a transactional delete-then-insert write through the configured backend.

The main modeling choice in this round is to keep OpenFGA as one container, not three. Even though the runtime exposes multiple listeners and protocols, the repo starts them from one process and shares the same core server object, command layer, caches, planner, and datastore integration logic. That makes the API, auth, command, graph-evaluation, and persistence layers better represented as internal components than as separate deployable containers.
```

### `architecture/views/component-openfga-server.yaml`

```yaml
version: 2
id: "component-openfga-server"
type: "component"
title: "OpenFGA Server Components"
audience:
  - "new_hires"
  - "senior_architects"
purpose: "Show the meaningful internal boundaries inside the main server runtime."
scope: "The `openfga run` container and the components that handle transport, authorization, evaluation, and persistence."
source_model: "architecture/model.yaml"
parent_container_id: "openfga-server"
element_ids:
  - "api-surface"
  - "auth-and-access-control"
  - "command-services"
  - "authorization-engines"
  - "datastore-adapters"
  - "in-memory-state-backend"
  - "persistent-state-backend"
  - "oidc-issuer"
relationship_ids:
  - "r-api-surface-calls-auth-access"
  - "r-api-surface-calls-command-services"
  - "r-auth-access-authenticates-with-oidc"
  - "r-auth-access-calls-authorization-engines"
  - "r-command-services-call-authorization-engines"
  - "r-command-services-call-datastore-adapters"
  - "r-authorization-engines-read-via-datastore-adapters"
  - "r-datastore-adapters-store-state-in-persistent-backend"
  - "r-datastore-adapters-store-state-in-memory-backend"
assumptions:
  - text: "Store CRUD, tuple writes, assertion reads/writes, and change-log reads share one command layer rather than separate domain services."
    confidence: "strong_inference"
unknowns:
  - "ListObjects and Check can run through experimental weighted-graph paths, but the exact production split between engines depends on feature flags."
notes:
  - "The auth-and-access-control component is not just front-door authn; it can recursively use OpenFGA's own authorization engine against an internal access-control store."
  - "The command-services component restores the repo's documented handler -> command -> graph/storage layering."
  - "The authorization-engines component includes planner, graph/modelgraph logic, request-scoped storage wrappers, and cache invalidation coordination."
```

### `architecture/views/container.yaml`

```yaml
version: 2
id: "container"
type: "container"
title: "OpenFGA Container View"
audience:
  - "new_hires"
  - "senior_architects"
purpose: "Show the main deployable runtime and the external dependencies it must coordinate with."
scope: "The OpenFGA software system at container granularity."
source_model: "architecture/model.yaml"
element_ids:
  - "openfga-system"
  - "openfga-server"
  - "persistent-state-backend"
  - "oidc-issuer"
  - "telemetry-collector"
relationship_ids:
  - "r-openfga-system-contains-openfga-server"
  - "r-openfga-server-authenticates-with-oidc"
  - "r-openfga-server-stores-state-in-persistent-backend"
  - "r-openfga-server-publishes-telemetry"
assumptions:
  - text: "The optional local playground stays inside the main server container because it is launched by the same `run` command and shares the server's HTTP dependency."
    confidence: "strong_inference"
unknowns:
  - "The repository documents production deployments with ingress and multiple instances, but those nodes are not directly enforced by the code paths modeled here."
notes:
  - "The HTTP API is implemented as an in-process grpc-gateway connected to the server's own gRPC endpoint."
  - "The external persistent backend shown here covers Postgres, MySQL, and SQLite; the memory adapter is process-local and is represented only in the component view."
```

### `architecture/views/sequence-permission-check.yaml`

```yaml
version: 2
id: "sequence-permission-check"
type: "sequence"
title: "Permission Check Workflow"
audience:
  - "new_hires"
  - "senior_architects"
purpose: "Explain how an authorization check request is authenticated, evaluated, and answered."
scope: "A representative `Check` request through the main OpenFGA server runtime."
source_model: "architecture/model.yaml"
participant_ids:
  - "client-applications"
  - "api-surface"
  - "auth-and-access-control"
  - "command-services"
  - "authorization-engines"
  - "datastore-adapters"
  - "persistent-state-backend"
steps:
  - order: 1
    source_id: "client-applications"
    target_id: "api-surface"
    relationship_id: "r-client-applications-use-openfga"
    label: "Submit a `Check` request over HTTP or gRPC with tuple key, consistency, and optional contextual tuples."
    sync_async: "sync"
    data_objects:
      - "Check request"
      - "Contextual tuples"
    confidence: "confirmed"
    evidence_ids:
      - "e-readme"
      - "e-check-rpc"
  - order: 2
    source_id: "api-surface"
    target_id: "auth-and-access-control"
    relationship_id: "r-api-surface-calls-auth-access"
    label: "Validate the caller's authentication context and authorize the API method before executing business logic."
    sync_async: "sync"
    data_objects:
      - "Bearer token or preshared key"
      - "Access-control context"
    confidence: "confirmed"
    evidence_ids:
      - "e-run"
      - "e-authz"
      - "e-check-rpc"
  - order: 3
    source_id: "auth-and-access-control"
    target_id: "authorization-engines"
    relationship_id: "r-auth-access-calls-authorization-engines"
    label: "When access-control is enabled, reuse OpenFGA's own permission engine to decide whether the caller may invoke `Check` on the target store."
    sync_async: "sync"
    data_objects:
      - "Caller claims"
      - "Access-control tuples"
    confidence: "confirmed"
    evidence_ids:
      - "e-authz"
      - "e-check-rpc"
  - order: 4
    source_id: "api-surface"
    target_id: "command-services"
    relationship_id: "r-api-surface-calls-command-services"
    label: "Delegate the request to the command layer, which resolves the active authorization model and prepares graph execution."
    sync_async: "sync"
    data_objects:
      - "Resolved authorization model ID"
      - "Check request"
    confidence: "confirmed"
    evidence_ids:
      - "e-check-rpc"
      - "e-check-command"
  - order: 5
    source_id: "command-services"
    target_id: "authorization-engines"
    relationship_id: "r-command-services-call-authorization-engines"
    label: "Execute the graph-based permission evaluation through the classic or weighted engine."
    sync_async: "sync"
    data_objects:
      - "Check request"
      - "Resolved authorization model ID"
    confidence: "confirmed"
    evidence_ids:
      - "e-check-rpc"
      - "e-check-command"
  - order: 6
    source_id: "authorization-engines"
    target_id: "datastore-adapters"
    relationship_id: "r-authorization-engines-read-via-datastore-adapters"
    label: "Read tuples and cache invalidation metadata through request-scoped storage wrappers."
    sync_async: "storage"
    data_objects:
      - "Relationship tuples"
      - "Cache invalidation timestamps"
    confidence: "confirmed"
    evidence_ids:
      - "e-check-command"
      - "e-storage"
  - order: 7
    source_id: "datastore-adapters"
    target_id: "persistent-state-backend"
    relationship_id: "r-datastore-adapters-store-state-in-persistent-backend"
    label: "Fetch persisted authorization data from the configured backend."
    sync_async: "storage"
    data_objects:
      - "Authorization models"
      - "Relationship tuples"
    confidence: "confirmed"
    evidence_ids:
      - "e-storage"
      - "e-check-command"
  - order: 8
    source_id: "authorization-engines"
    target_id: "command-services"
    relationship_id: "r-command-services-call-authorization-engines"
    label: "Return the allow or deny result plus resolution metadata for logging and metrics."
    sync_async: "sync"
    data_objects:
      - "Check decision"
      - "Resolution metadata"
    confidence: "confirmed"
    evidence_ids:
      - "e-check-rpc"
  - order: 9
    source_id: "command-services"
    target_id: "api-surface"
    relationship_id: "r-api-surface-calls-command-services"
    label: "Return the evaluated result to the transport layer."
    sync_async: "sync"
    data_objects:
      - "Check decision"
      - "Resolution metadata"
    confidence: "confirmed"
    evidence_ids:
      - "e-check-rpc"
  - order: 10
    source_id: "api-surface"
    target_id: "client-applications"
    relationship_id: "r-client-applications-use-openfga"
    label: "Respond with the final allow or deny decision."
    sync_async: "sync"
    data_objects:
      - "Check response"
    confidence: "confirmed"
    evidence_ids:
      - "e-check-rpc"
assumptions:
  - text: "This sequence shows the main evaluation path and not the optional shadow-check comparison path used for experimental validation."
    confidence: "strong_inference"
unknowns:
  - "Whether weighted-graph evaluation is active depends on per-store feature flags."
notes:
  - "OIDC key retrieval is omitted from the mainline sequence because it is conditional on auth configuration and may be cached between requests."
```

### `architecture/views/sequence-store-bootstrap.yaml`

```yaml
version: 2
id: "sequence-store-bootstrap"
type: "sequence"
title: "Store Bootstrap Workflow"
audience:
  - "new_hires"
  - "senior_architects"
purpose: "Explain how a new OpenFGA store is created and receives its first authorization model."
scope: "The bootstrap path for provisioning a store and publishing its policy model."
source_model: "architecture/model.yaml"
participant_ids:
  - "client-applications"
  - "api-surface"
  - "auth-and-access-control"
  - "command-services"
  - "datastore-adapters"
  - "persistent-state-backend"
steps:
  - order: 1
    source_id: "client-applications"
    target_id: "api-surface"
    relationship_id: "r-client-applications-use-openfga"
    label: "Submit `CreateStore` to provision a new authorization store."
    sync_async: "sync"
    data_objects:
      - "CreateStore request"
      - "Store metadata"
    confidence: "confirmed"
    evidence_ids:
      - "e-stores-rpc"
  - order: 2
    source_id: "api-surface"
    target_id: "auth-and-access-control"
    relationship_id: "r-api-surface-calls-auth-access"
    label: "Authenticate the caller and authorize the store-creation API."
    sync_async: "sync"
    data_objects:
      - "Caller claims"
      - "Store-creation permission context"
    confidence: "confirmed"
    evidence_ids:
      - "e-stores-rpc"
      - "e-authz"
  - order: 3
    source_id: "api-surface"
    target_id: "command-services"
    relationship_id: "r-api-surface-calls-command-services"
    label: "Delegate store provisioning to the command layer."
    sync_async: "sync"
    data_objects:
      - "Store metadata"
    confidence: "confirmed"
    evidence_ids:
      - "e-stores-rpc"
      - "e-openfga-agents"
  - order: 4
    source_id: "command-services"
    target_id: "datastore-adapters"
    relationship_id: "r-command-services-call-datastore-adapters"
    label: "Create the store record in the selected backend."
    sync_async: "storage"
    data_objects:
      - "Store metadata"
    confidence: "confirmed"
    evidence_ids:
      - "e-stores-rpc"
      - "e-storage"
  - order: 5
    source_id: "datastore-adapters"
    target_id: "persistent-state-backend"
    relationship_id: "r-datastore-adapters-store-state-in-persistent-backend"
    label: "Persist the new store in the external backend for persistent deployments."
    sync_async: "storage"
    data_objects:
      - "Store metadata"
    confidence: "confirmed"
    evidence_ids:
      - "e-stores-rpc"
      - "e-storage"
  - order: 6
    source_id: "client-applications"
    target_id: "api-surface"
    relationship_id: "r-client-applications-use-openfga"
    label: "Submit `WriteAuthorizationModel` for the new store."
    sync_async: "sync"
    data_objects:
      - "Authorization model"
    confidence: "confirmed"
    evidence_ids:
      - "e-readme"
      - "e-authz-model-rpc"
  - order: 7
    source_id: "api-surface"
    target_id: "auth-and-access-control"
    relationship_id: "r-api-surface-calls-auth-access"
    label: "Authenticate the caller and authorize model publication."
    sync_async: "sync"
    data_objects:
      - "Caller claims"
      - "Authorization-model write permission context"
    confidence: "confirmed"
    evidence_ids:
      - "e-authz-model-rpc"
      - "e-authz"
  - order: 8
    source_id: "api-surface"
    target_id: "command-services"
    relationship_id: "r-api-surface-calls-command-services"
    label: "Delegate model validation and publication to the command layer."
    sync_async: "sync"
    data_objects:
      - "Authorization model"
    confidence: "confirmed"
    evidence_ids:
      - "e-authz-model-rpc"
      - "e-write-authzmodel-command"
  - order: 9
    source_id: "command-services"
    target_id: "datastore-adapters"
    relationship_id: "r-command-services-call-datastore-adapters"
    label: "Validate schema and size, then persist the new authorization model."
    sync_async: "storage"
    data_objects:
      - "Authorization model"
    confidence: "confirmed"
    evidence_ids:
      - "e-authz-model-rpc"
      - "e-write-authzmodel-command"
  - order: 10
    source_id: "datastore-adapters"
    target_id: "persistent-state-backend"
    relationship_id: "r-datastore-adapters-store-state-in-persistent-backend"
    label: "Store the new authorization model and return its generated ID."
    sync_async: "storage"
    data_objects:
      - "Authorization model"
      - "Authorization model ID"
    confidence: "confirmed"
    evidence_ids:
      - "e-write-authzmodel-command"
      - "e-storage"
  - order: 11
    source_id: "api-surface"
    target_id: "client-applications"
    relationship_id: "r-client-applications-use-openfga"
    label: "Return the created store and new authorization model ID."
    sync_async: "sync"
    data_objects:
      - "CreateStore response"
      - "WriteAuthorizationModel response"
    confidence: "confirmed"
    evidence_ids:
      - "e-stores-rpc"
      - "e-authz-model-rpc"
assumptions:
  - text: "The bootstrap sequence shows the persistent-backend path; the in-memory adapter follows the same logical steps inside the server process."
    confidence: "strong_inference"
unknowns:
  - "The repo supports additional follow-on bootstrap state such as assertions, but that is not required for a store to begin serving core authorization queries."
notes:
  - "A usable OpenFGA store needs both a store record and at least one authorization model; that is why bootstrap is modeled as a combined lifecycle flow."
```

### `architecture/views/sequence-write-relationship-tuples.yaml`

```yaml
version: 2
id: "sequence-write-relationship-tuples"
type: "sequence"
title: "Tuple Write Workflow"
audience:
  - "new_hires"
  - "senior_architects"
purpose: "Explain how OpenFGA validates and persists tuple mutations."
scope: "A representative `Write` request through the main OpenFGA server runtime."
source_model: "architecture/model.yaml"
participant_ids:
  - "client-applications"
  - "api-surface"
  - "auth-and-access-control"
  - "command-services"
  - "datastore-adapters"
  - "persistent-state-backend"
steps:
  - order: 1
    source_id: "client-applications"
    target_id: "api-surface"
    relationship_id: "r-client-applications-use-openfga"
    label: "Submit a tuple mutation request with writes, deletes, store ID, and an optional authorization model ID."
    sync_async: "sync"
    data_objects:
      - "Write request"
      - "Tuple mutations"
    confidence: "confirmed"
    evidence_ids:
      - "e-write-rpc"
  - order: 2
    source_id: "api-surface"
    target_id: "command-services"
    relationship_id: "r-api-surface-calls-command-services"
    label: "Delegate the write request to the command-oriented business layer."
    sync_async: "sync"
    data_objects:
      - "Requested tuple mutations"
    confidence: "confirmed"
    evidence_ids:
      - "e-write-rpc"
      - "e-write-command"
  - order: 3
    source_id: "command-services"
    target_id: "datastore-adapters"
    relationship_id: "r-command-services-call-datastore-adapters"
    label: "Load the effective authorization model so the handler can resolve the active typesystem."
    sync_async: "storage"
    data_objects:
      - "Authorization model"
      - "Tuple mutations"
    confidence: "confirmed"
    evidence_ids:
      - "e-write-rpc"
      - "e-write-command"
  - order: 4
    source_id: "datastore-adapters"
    target_id: "persistent-state-backend"
    relationship_id: "r-datastore-adapters-store-state-in-persistent-backend"
    label: "Read the persisted authorization model for the target store."
    sync_async: "storage"
    data_objects:
      - "Authorization model"
    confidence: "confirmed"
    evidence_ids:
      - "e-write-command"
      - "e-storage"
  - order: 5
    source_id: "api-surface"
    target_id: "auth-and-access-control"
    relationship_id: "r-api-surface-calls-auth-access"
    label: "Authenticate the caller and verify write permission for the target store or modules using the resolved typesystem."
    sync_async: "sync"
    data_objects:
      - "Caller claims"
      - "Resolved authorization model ID"
      - "Requested tuple mutations"
    confidence: "confirmed"
    evidence_ids:
      - "e-write-rpc"
      - "e-authz"
  - order: 6
    source_id: "api-surface"
    target_id: "command-services"
    relationship_id: "r-api-surface-calls-command-services"
    label: "Invoke the write command to validate duplicates, tuple structure, and request options."
    sync_async: "sync"
    data_objects:
      - "Validated tuple mutations"
      - "Resolved authorization model ID"
    confidence: "confirmed"
    evidence_ids:
      - "e-write-rpc"
      - "e-write-command"
  - order: 7
    source_id: "command-services"
    target_id: "datastore-adapters"
    relationship_id: "r-command-services-call-datastore-adapters"
    label: "Re-read the model for command validation, then issue a transactional delete-then-insert write."
    sync_async: "storage"
    data_objects:
      - "Validated tuple deletions"
      - "Validated tuple writes"
    confidence: "confirmed"
    evidence_ids:
      - "e-write-command"
  - order: 8
    source_id: "datastore-adapters"
    target_id: "persistent-state-backend"
    relationship_id: "r-datastore-adapters-store-state-in-persistent-backend"
    label: "Persist the tuple mutations and update change history in the configured backend."
    sync_async: "storage"
    data_objects:
      - "Relationship tuples"
      - "Tuple change history"
    confidence: "confirmed"
    evidence_ids:
      - "e-write-command"
      - "e-storage"
  - order: 9
    source_id: "command-services"
    target_id: "api-surface"
    relationship_id: "r-api-surface-calls-command-services"
    label: "Return success or a transactional/validation error to the transport layer."
    sync_async: "sync"
    data_objects:
      - "Write result"
    confidence: "confirmed"
    evidence_ids:
      - "e-write-rpc"
      - "e-write-command"
  - order: 10
    source_id: "api-surface"
    target_id: "client-applications"
    relationship_id: "r-client-applications-use-openfga"
    label: "Return success or a transactional/validation error."
    sync_async: "sync"
    data_objects:
      - "Write response"
    confidence: "confirmed"
    evidence_ids:
      - "e-write-rpc"
assumptions:
  - text: "The sequence focuses on tuple mutations and not on `WriteAuthorizationModel`, although model writes are another part of the same API surface."
    confidence: "strong_inference"
unknowns:
  - "Whether deletes or duplicate inserts are ignored versus rejected depends on request options."
notes:
  - "The handler resolves the typesystem before module-level write authorization, then the write command validates against the active model again before calling datastore `Write`."
```

### `architecture/views/system-context.yaml`

```yaml
version: 2
id: "system-context"
type: "system_context"
title: "OpenFGA System Context"
audience:
  - "new_hires"
  - "pms"
  - "senior_architects"
purpose: "Show what OpenFGA is, who uses it, and which external systems materially affect runtime behavior."
scope: "OpenFGA as a software system plus its key external consumers and integrations."
source_model: "architecture/model.yaml"
element_ids:
  - "client-applications"
  - "openfga-system"
  - "oidc-issuer"
  - "persistent-state-backend"
  - "telemetry-collector"
relationship_ids:
  - "r-client-applications-use-openfga"
  - "r-openfga-system-authenticates-with-oidc"
  - "r-openfga-system-stores-state-in-persistent-backend"
  - "r-openfga-system-publishes-telemetry"
assumptions:
  - text: "The datastore is shown as a single external system even though deployments can swap between several backend implementations."
    confidence: "strong_inference"
unknowns:
  - "Whether a given deployment uses OIDC, preshared keys, or no authentication is configuration dependent."
notes:
  - "Client traffic can enter over gRPC directly or over HTTP through SDKs and the grpc-gateway."
  - "The default quickstart in-memory mode is process-local and therefore not shown as an external system in this view."
  - "Telemetry and OIDC are optional integrations rather than mandatory dependencies for every deployment."
```
