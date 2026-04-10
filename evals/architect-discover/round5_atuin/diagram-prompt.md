# Diagram Prompt Bundle — round5_atuin

## Agent Instruction: Execute the Prompt Below Exactly

If this file is uploaded without any user-typed prompt, treat the prompt in the code block below as the full instruction and execute it directly.

```text
You are a senior Rust engineer and interactive visualization designer.

Build a single interactive architecture diagram for **Atuin** from the provided files.

Output requirements:
1) Draw one self-contained diagram.
2) The diagram must support progressive drill-down navigation:
   - Level 1: System Context
   - Level 2: Container View
   - Level 3: Component View
   - Level 4: Code Detail (only if code-level data exists; otherwise show detail panel)
3) Show a breadcrumb at the top at all times:
   - Format: `Atuin > <Container> > <Component>`
   - Each segment is clickable to navigate back
   - Include a Back button
4) Click behavior:
   - Single click: open detail panel (name, type, tech, description, responsibilities, owned_data, confidence)
   - Expand icon or double click: drill down to child level
5) Visual behavior:
   - Clickable nodes must look clickable (hover + affordance)
   - Non-expandable nodes must not look clickable
   - Smooth transition between levels
   - Consistent color families by type (container, external system, datastore, component)
6) Relationship behavior:
   - Render only relationships relevant to current level
   - Label edges with interaction/description and protocol when available
   - If endpoint is outside current view, show simplified edge reference node at boundary
7) Sequence views:
   - Do NOT mix sequence flows into drill-down graph
   - Put sequence views in a separate tab/panel
8) Data integrity:
   - Use only facts from provided files (`model.yaml`, `manifest.yaml`, `views/*.yaml`, `summary.md`)
   - Do not invent elements or relationships

Known container set (for validation): Atuin CLI, Atuin Daemon, Client Library, Local SQLite Databases, Sync Server

Now generate the interactive diagram.
```

## View-to-Level Mapping

| View File | Drill-down Level |
|---|---|
| views/component-client-library.yaml | Component |
| views/component-server.yaml | Component |
| views/container.yaml | Container |
| views/sequence-history-capture.yaml | Sequence (separate tab/panel) |
| views/sequence-sync.yaml | Sequence (separate tab/panel) |
| views/system-context.yaml | System Context |

## Virtual Directory Tree

```text
round5_atuin/
  architecture/
    manifest.yaml
    model.yaml
    summary.md
    views/
      component-client-library.yaml
      component-server.yaml
      container.yaml
      sequence-history-capture.yaml
      sequence-sync.yaml
      system-context.yaml
```

## File Contents

### architecture/manifest.yaml

```yaml
skill_version: "1.0"
repo: "atuinsh/atuin"
repo_path: "evals/repos/atuin"
output_path: "evals/architect-discover/round5_atuin/architecture"
extraction_mode: "initial"
archetype: "full_stack_product"
audiences:
  - "senior developers"
  - "architecture reviewers"
artifacts:
  - path: "model.yaml"
    type: "canonical_model"
  - path: "views/system-context.yaml"
    type: "system_context_view"
  - path: "views/container.yaml"
    type: "container_view"
  - path: "views/component-client-library.yaml"
    type: "component_view"
    parent: "client-library"
  - path: "views/component-server.yaml"
    type: "component_view"
    parent: "server-binary"
  - path: "views/sequence-sync.yaml"
    type: "sequence_view"
  - path: "views/sequence-history-capture.yaml"
    type: "sequence_view"
  - path: "summary.md"
    type: "summary"
scope:
  in_scope:
    - "evals/repos/atuin/crates/"
    - "evals/repos/atuin/Cargo.toml"
    - "evals/repos/atuin/Dockerfile"
    - "evals/repos/atuin/docker-compose.yml"
    - "evals/repos/atuin/k8s/"
  out_of_scope:
    - "evals/repos/atuin/docs/"
    - "evals/repos/atuin/docs-i18n/"
    - "evals/repos/atuin/scripts/"
    - "evals/repos/atuin/ui/"

```

### architecture/model.yaml

```yaml
version: 2
system_name: "Atuin"
repo_archetype: "full_stack_product"
elements:
  # === Context-level ===
  - id: "atuin-system"
    name: "Atuin"
    aliases: ["magical shell history"]
    kind: "software_system"
    c4_level: "context"
    description: "Shell history tool that replaces built-in shell history with a SQLite database, adds context (cwd, exit code, duration, hostname), and optionally syncs across machines with end-to-end encryption."
    responsibility: "Record, search, and sync shell history across machines with encryption."
    technology: "Rust"
    owned_data: ["shell_history", "dotfiles", "kv_store", "scripts"]
    system_of_record: ["shell_history"]
    runtime_boundary: "process"
    deployable: true
    external: false
    parent_id: ""
    source_paths: ["crates/"]
    tags: ["shell", "history", "sync"]
    confidence: "confirmed"
    evidence_ids: ["ev-readme", "ev-agents-md", "ev-cargo-workspace"]

  - id: "shell-user"
    name: "Developer / Shell User"
    aliases: []
    kind: "person"
    c4_level: "context"
    description: "Developer using a shell (bash, zsh, fish, nushell, xonsh, powershell) with Atuin installed for history management."
    responsibility: "Runs commands, searches history, configures sync."
    technology: ""
    owned_data: []
    system_of_record: []
    runtime_boundary: "external"
    deployable: false
    external: true
    parent_id: ""
    source_paths: []
    tags: []
    confidence: "confirmed"
    evidence_ids: ["ev-readme"]

  - id: "atuin-sync-server"
    name: "Atuin Sync Server"
    aliases: ["atuin.sh"]
    kind: "external_system"
    c4_level: "context"
    description: "Remote sync server (self-hosted or atuin.sh hosted) that stores encrypted records for cross-machine synchronization. Can run Postgres or SQLite as its backend."
    responsibility: "Store and serve encrypted sync records. User registration and authentication."
    technology: "Rust / axum"
    owned_data: ["encrypted_sync_records", "user_accounts", "session_tokens"]
    system_of_record: ["encrypted_sync_records"]
    runtime_boundary: "network"
    deployable: true
    external: true
    parent_id: ""
    source_paths: ["crates/atuin-server/"]
    tags: ["sync", "server"]
    confidence: "confirmed"
    evidence_ids: ["ev-server-main", "ev-docker-compose", "ev-agents-md"]
    notes: "This is modeled as external because the client and server are independently deployed. The server crate is also in this repo but runs as a separate binary."

  - id: "postgres"
    name: "PostgreSQL"
    aliases: []
    kind: "external_system"
    c4_level: "context"
    description: "Database backend for the sync server in production deployments."
    responsibility: "Persist user accounts, session tokens, and encrypted sync records for the server."
    technology: "PostgreSQL"
    owned_data: ["server_persisted_data"]
    system_of_record: []
    runtime_boundary: "external"
    deployable: false
    external: true
    parent_id: ""
    source_paths: ["crates/atuin-server-postgres/"]
    tags: ["database"]
    confidence: "confirmed"
    evidence_ids: ["ev-docker-compose", "ev-server-postgres"]
    notes: "SQLite is also supported as an alternative server backend."

  # === Container-level ===
  - id: "atuin-cli"
    name: "Atuin CLI"
    aliases: ["atuin binary"]
    kind: "container"
    c4_level: "container"
    description: "Primary CLI binary and TUI for shell history management. Handles commands like history start/end, search, sync, import, stats, and shell init scripts."
    responsibility: "User-facing interface for all Atuin operations. Shell integration via init scripts."
    technology: "Rust / clap / ratatui / crossterm"
    owned_data: []
    system_of_record: []
    runtime_boundary: "process"
    deployable: true
    external: false
    parent_id: "atuin-system"
    source_paths: ["crates/atuin/"]
    tags: ["cli", "tui"]
    confidence: "confirmed"
    evidence_ids: ["ev-agents-md", "ev-cli-src"]

  - id: "atuin-daemon-container"
    name: "Atuin Daemon"
    aliases: ["background daemon"]
    kind: "container"
    c4_level: "container"
    description: "Background gRPC daemon process for shell hooks. Provides fast history recording and search without CLI startup latency."
    responsibility: "Accept history events and search queries from shell hooks via Unix socket gRPC."
    technology: "Rust / tonic (gRPC)"
    owned_data: []
    system_of_record: []
    runtime_boundary: "process"
    deployable: true
    external: false
    parent_id: "atuin-system"
    source_paths: ["crates/atuin-daemon/"]
    tags: ["daemon", "grpc"]
    confidence: "confirmed"
    evidence_ids: ["ev-agents-md", "ev-daemon-server"]

  - id: "client-library"
    name: "Client Library"
    aliases: ["atuin-client"]
    kind: "container"
    c4_level: "container"
    description: "Core client library providing local database access, encryption, sync protocol, settings management, and history import. Used by both CLI and daemon."
    responsibility: "Local history storage, record store, encryption/decryption, sync operations."
    technology: "Rust / sqlx / SQLite"
    owned_data: ["local_history_db", "local_record_store", "encryption_key"]
    system_of_record: ["shell_history"]
    runtime_boundary: "library"
    deployable: false
    external: false
    parent_id: "atuin-system"
    source_paths: ["crates/atuin-client/"]
    tags: ["library", "encryption", "database"]
    confidence: "confirmed"
    evidence_ids: ["ev-agents-md", "ev-client-src"]

  - id: "local-sqlite"
    name: "Local SQLite Databases"
    aliases: []
    kind: "datastore"
    c4_level: "container"
    description: "Local SQLite databases storing shell history, record store, KV data, and scripts. Uses WAL mode."
    responsibility: "Persistent local storage for all client-side data."
    technology: "SQLite (WAL mode)"
    owned_data: ["shell_history", "record_store", "kv_data", "scripts"]
    system_of_record: ["shell_history"]
    runtime_boundary: "file"
    deployable: false
    external: false
    parent_id: "atuin-system"
    source_paths: ["crates/atuin-client/src/database.rs", "crates/atuin-client/src/record/sqlite_store.rs"]
    tags: ["database", "sqlite"]
    confidence: "confirmed"
    evidence_ids: ["ev-agents-md", "ev-client-database"]

  - id: "server-binary"
    name: "Sync Server"
    aliases: ["atuin-server"]
    kind: "container"
    c4_level: "container"
    description: "HTTP sync server (axum) that handles user registration, authentication, and encrypted record sync. Supports Postgres or SQLite as its database backend."
    responsibility: "User management, session auth, record storage and retrieval for sync protocol."
    technology: "Rust / axum"
    owned_data: ["user_accounts", "session_tokens", "encrypted_records"]
    system_of_record: ["encrypted_sync_records"]
    runtime_boundary: "process"
    deployable: true
    external: false
    parent_id: "atuin-system"
    source_paths: ["crates/atuin-server/"]
    tags: ["server", "http", "sync"]
    confidence: "confirmed"
    evidence_ids: ["ev-server-main", "ev-server-router"]
    notes: "Modeled as a container within the system because it's in the same repo and workspace, even though it deploys independently."

  # === Component-level: Client Library ===
  - id: "client-history-store"
    name: "History Store"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Manages shell history records. Handles history capture (start/end), import from other shells, and query/search."
    responsibility: "CRUD operations for shell history, import from bash/zsh/fish/nu/etc."
    technology: "Rust / sqlx"
    owned_data: ["shell_history"]
    system_of_record: ["shell_history"]
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "client-library"
    source_paths: ["crates/atuin-client/src/history/", "crates/atuin-client/src/database.rs"]
    tags: ["history", "database"]
    confidence: "confirmed"
    evidence_ids: ["ev-client-src"]

  - id: "client-record-store"
    name: "Record Store"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Generic record store abstraction. All synced data types (history, KV, aliases, vars, scripts) share this infrastructure using tagged records."
    responsibility: "Store, retrieve, and manage encrypted records for sync. Tag-based routing to data type handlers."
    technology: "Rust / sqlx / SQLite"
    owned_data: ["records"]
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "client-library"
    source_paths: ["crates/atuin-client/src/record/"]
    tags: ["record-store", "sync"]
    confidence: "confirmed"
    evidence_ids: ["ev-agents-md", "ev-record-store"]

  - id: "client-encryption"
    name: "Encryption Engine"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Envelope encryption using PASETO V4 Local (XChaCha20-Poly1305 + Blake2b). Each record gets a random content-encryption key (CEK) wrapped with the master key. Supports V1 legacy (XSalsa20Poly1305) for backward compatibility."
    responsibility: "Encrypt and decrypt sync records. Key wrapping, CEK generation, implicit assertion binding."
    technology: "Rust / rusty_paseto / rusty_paserk"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "client-library"
    source_paths: ["crates/atuin-client/src/record/encryption.rs"]
    tags: ["encryption", "paseto"]
    confidence: "confirmed"
    evidence_ids: ["ev-agents-md", "ev-encryption"]

  - id: "client-sync"
    name: "Sync Protocol"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Bidirectional sync protocol between client and server. Computes diffs between local and remote record status, then uploads/downloads as needed."
    responsibility: "Diff computation, upload, download, conflict resolution for encrypted records."
    technology: "Rust"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "client-library"
    source_paths: ["crates/atuin-client/src/record/sync.rs", "crates/atuin-client/src/sync.rs"]
    tags: ["sync"]
    confidence: "confirmed"
    evidence_ids: ["ev-agents-md", "ev-sync"]

  - id: "client-api"
    name: "API Client"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "HTTP client for communicating with the Atuin sync server. Handles registration, login, record push/pull."
    responsibility: "HTTP requests to the sync server API."
    technology: "Rust / reqwest"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "client-library"
    source_paths: ["crates/atuin-client/src/register.rs"]
    tags: ["api-client"]
    confidence: "strong_inference"
    evidence_ids: ["ev-agents-md"]

  # === Component-level: Server ===
  - id: "server-handlers"
    name: "API Handlers"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "HTTP route handlers for user registration, login, history sync (v1 legacy), record sync (v2), health check, and status."
    responsibility: "Process API requests, enforce authentication, delegate to database layer."
    technology: "Rust / axum"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "server-binary"
    source_paths: ["crates/atuin-server/src/handlers/"]
    tags: ["handlers"]
    confidence: "confirmed"
    evidence_ids: ["ev-server-router"]

  - id: "server-auth"
    name: "Authentication"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Token-based session authentication. Users register with username/email/password, receive a session token for subsequent requests."
    responsibility: "User registration, login, session token validation."
    technology: "Rust"
    owned_data: ["session_tokens"]
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "server-binary"
    source_paths: ["crates/atuin-server/src/router.rs", "crates/atuin-server/src/handlers/user.rs"]
    tags: ["auth"]
    confidence: "confirmed"
    evidence_ids: ["ev-server-router"]

  - id: "server-database-trait"
    name: "Database Abstraction"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Database trait defining the server's storage interface. Implementations exist for Postgres and SQLite."
    responsibility: "Abstract database operations for user, history, and record management."
    technology: "Rust / async_trait"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "server-binary"
    source_paths: ["crates/atuin-server-database/", "crates/atuin-server-postgres/", "crates/atuin-server-sqlite/"]
    tags: ["database", "abstraction"]
    confidence: "confirmed"
    evidence_ids: ["ev-agents-md", "ev-server-main"]

relationships:
  # Context-level
  - id: "rel-user-cli"
    source_id: "shell-user"
    target_id: "atuin-cli"
    label: "Runs atuin commands, searches history, triggers sync"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "cli"
    data_objects: ["Command", "SearchQuery"]
    confidence: "confirmed"
    evidence_ids: ["ev-readme"]

  - id: "rel-shell-daemon"
    source_id: "shell-user"
    target_id: "atuin-daemon-container"
    label: "Shell hooks send history events via Unix socket"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "grpc_unix_socket"
    data_objects: ["HistoryEvent", "SearchQuery"]
    confidence: "confirmed"
    evidence_ids: ["ev-daemon-server"]

  - id: "rel-cli-client"
    source_id: "atuin-cli"
    target_id: "client-library"
    label: "Uses client library for all operations"
    interaction_type: "uses"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects: []
    confidence: "confirmed"
    evidence_ids: ["ev-agents-md"]

  - id: "rel-daemon-client"
    source_id: "atuin-daemon-container"
    target_id: "client-library"
    label: "Uses client library for history and search operations"
    interaction_type: "uses"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects: []
    confidence: "confirmed"
    evidence_ids: ["ev-agents-md"]

  - id: "rel-client-sqlite"
    source_id: "client-library"
    target_id: "local-sqlite"
    label: "Reads and writes history, records, KV, scripts"
    interaction_type: "reads_writes"
    directionality: "bidirectional"
    sync_async: "sync"
    protocol: "sqlite"
    data_objects: ["History", "Record", "KV", "Script"]
    confidence: "confirmed"
    evidence_ids: ["ev-client-database", "ev-agents-md"]

  - id: "rel-client-server"
    source_id: "client-library"
    target_id: "atuin-sync-server"
    label: "Syncs encrypted records (upload/download), user registration/login"
    interaction_type: "calls"
    directionality: "bidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects: ["EncryptedRecord", "UserCredentials", "SessionToken", "RecordStatus"]
    confidence: "confirmed"
    evidence_ids: ["ev-sync", "ev-agents-md"]

  - id: "rel-server-postgres"
    source_id: "server-binary"
    target_id: "postgres"
    label: "Persists users, sessions, and encrypted records"
    interaction_type: "reads_writes"
    directionality: "bidirectional"
    sync_async: "sync"
    protocol: "postgresql"
    data_objects: ["User", "Session", "EncryptedRecord"]
    confidence: "confirmed"
    evidence_ids: ["ev-docker-compose", "ev-server-postgres"]

  # Component-level relationships
  - id: "rel-sync-recordstore"
    source_id: "client-sync"
    target_id: "client-record-store"
    label: "Reads and writes records during sync operations"
    interaction_type: "uses"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects: ["Record", "RecordStatus"]
    confidence: "confirmed"
    evidence_ids: ["ev-sync"]

  - id: "rel-sync-encryption"
    source_id: "client-sync"
    target_id: "client-encryption"
    label: "Encrypts records before upload, decrypts after download"
    interaction_type: "uses"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects: ["EncryptedData", "DecryptedData"]
    confidence: "confirmed"
    evidence_ids: ["ev-encryption"]

  - id: "rel-sync-api"
    source_id: "client-sync"
    target_id: "client-api"
    label: "Makes HTTP requests to sync server"
    interaction_type: "uses"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects: ["EncryptedRecord"]
    confidence: "strong_inference"
    evidence_ids: ["ev-sync"]

  - id: "rel-handlers-auth"
    source_id: "server-handlers"
    target_id: "server-auth"
    label: "Validates session tokens on protected routes"
    interaction_type: "uses"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects: ["SessionToken", "User"]
    confidence: "confirmed"
    evidence_ids: ["ev-server-router"]

  - id: "rel-handlers-db"
    source_id: "server-handlers"
    target_id: "server-database-trait"
    label: "CRUD operations for users, history, and records"
    interaction_type: "uses"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects: ["User", "Record", "History"]
    confidence: "confirmed"
    evidence_ids: ["ev-server-router"]

evidence:
  - id: "ev-readme"
    path: "README.md"
    kind: "doc"
    strength: "high"
    reason: "States Atuin replaces shell history with SQLite, provides encrypted sync."

  - id: "ev-agents-md"
    path: "AGENTS.md"
    kind: "doc"
    strength: "high"
    reason: "Detailed workspace crate descriptions, sync protocols, encryption schemes, conventions."

  - id: "ev-cargo-workspace"
    path: "Cargo.toml"
    kind: "runtime_entrypoint"
    strength: "high"
    reason: "Workspace manifest defining all crates."

  - id: "ev-cli-src"
    path: "crates/atuin/src/"
    kind: "directory_name"
    strength: "high"
    reason: "CLI binary with command modules."

  - id: "ev-client-src"
    path: "crates/atuin-client/src/"
    kind: "directory_name"
    strength: "high"
    reason: "Client library with database, encryption, sync, settings."

  - id: "ev-client-database"
    path: "crates/atuin-client/src/database.rs"
    kind: "code_path"
    strength: "high"
    reason: "SQLite database implementation with sqlx."

  - id: "ev-daemon-server"
    path: "crates/atuin-daemon/src/server.rs"
    kind: "code_path"
    strength: "high"
    reason: "gRPC server using tonic over Unix socket."

  - id: "ev-server-main"
    path: "crates/atuin-server/src/bin/main.rs"
    kind: "runtime_entrypoint"
    strength: "high"
    reason: "Server binary with Postgres/SQLite backend selection."

  - id: "ev-server-router"
    path: "crates/atuin-server/src/router.rs"
    kind: "code_path"
    strength: "high"
    reason: "Axum router with auth, history, record, user handlers."

  - id: "ev-server-postgres"
    path: "crates/atuin-server-postgres/"
    kind: "directory_name"
    strength: "high"
    reason: "Postgres implementation of server Database trait."

  - id: "ev-docker-compose"
    path: "docker-compose.yml"
    kind: "deploy_config"
    strength: "high"
    reason: "Docker Compose with Postgres backend for server deployment."

  - id: "ev-encryption"
    path: "crates/atuin-client/src/record/encryption.rs"
    kind: "code_path"
    strength: "high"
    reason: "PASETO V4 envelope encryption implementation."

  - id: "ev-sync"
    path: "crates/atuin-client/src/record/sync.rs"
    kind: "code_path"
    strength: "high"
    reason: "Sync protocol with diff computation and upload/download operations."

  - id: "ev-record-store"
    path: "crates/atuin-client/src/record/store.rs"
    kind: "code_path"
    strength: "high"
    reason: "Record store trait definition."

unknowns:
  - "Exact relationship between v1 (legacy) and v2 sync protocols at runtime — are they mutually exclusive or can both run simultaneously?"
  - "Whether atuin-ai crate is actively used or experimental."
  - "Exact deployment topology of the hosted atuin.sh service."

assumptions:
  - "The daemon is optional — the CLI can operate independently without it."
  - "The server binary (atuin-server) deploys independently from the CLI, even though they share a workspace."
  - "In production (atuin.sh), the server runs with Postgres backend."
  - "SQLite server backend is intended for self-hosted/dev deployments."

```

### architecture/summary.md

```markdown
# Atuin — Architecture Summary

## System Overview

Atuin is a shell history tool that replaces built-in shell history with a SQLite database. It records additional context (cwd, exit code, duration, hostname, session) and optionally syncs history across machines via an Atuin sync server with end-to-end encryption.

## Archetype

**Full-stack product.** The repo contains both the client-side tooling (CLI, daemon, client library) and the server-side sync infrastructure (HTTP server, database adapters). These deploy independently but share a Cargo workspace.

## Key Architectural Decisions

### Client/Server Split
The system has a clear client/server boundary. The client (CLI + daemon + client library) operates independently with local SQLite storage. The sync server is optional — Atuin works fully offline.

### Envelope Encryption (PASETO V4)
All synced data is encrypted client-side using envelope encryption. Each record gets a random content-encryption key (CEK) encrypted with the user's master key. The server stores only ciphertext and can never access plaintext history.

### Record Store Abstraction (V2 Sync)
The V2 sync protocol introduces a generic "record store" — all data types (history, KV, aliases, variables, scripts) share the same sync infrastructure using tagged records. This replaces the V1 protocol which synced history entries directly.

### Daemon for Low-Latency Shell Hooks
The `atuin-daemon` provides a background gRPC service over Unix socket. Shell hooks can record history without the CLI startup overhead. This is critical because `history start` and `history end` are hot paths that run on every command.

### Pluggable Server Database
The sync server supports both Postgres (production) and SQLite (self-hosted/dev) backends via a Database trait with separate crate implementations.

## Runtime Containers

| Container | Technology | Role |
|-----------|-----------|------|
| Atuin CLI | Rust / clap / ratatui | User-facing commands, TUI search, sync trigger |
| Atuin Daemon | Rust / tonic (gRPC) | Background service for low-latency shell hooks |
| Client Library | Rust / sqlx | Core logic: local DB, encryption, sync protocol |
| Local SQLite | SQLite (WAL) | Persistent local storage for all client data |
| Sync Server | Rust / axum | User mgmt, session auth, encrypted record sync |

## Data Ownership

| Data | Owner | System of Record |
|------|-------|-----------------|
| Shell history | Client Library / Local SQLite | Local SQLite (authoritative) |
| Encrypted sync records | Sync Server | Server database (Postgres/SQLite) |
| Encryption key | Client (local filesystem) | `~/.local/share/atuin/key` |
| User accounts & sessions | Sync Server | Server database |
| KV store, dotfiles, scripts | Client Library / Local SQLite | Local SQLite |

## Critical Workflows

1. **History Capture**: Shell hook → `atuin history start/end` → client library → local SQLite. Hot path, no DB init.
2. **Record Sync (V2)**: Client computes diff with server → encrypts local records → uploads → downloads remote records → decrypts → stores locally.
3. **Interactive Search**: User presses Ctrl-R → TUI renders → queries local SQLite with filters.

## Deployment Modes

- **Standalone (no sync)**: CLI + local SQLite only. No server needed.
- **Self-hosted sync**: CLI + sync server (Docker Compose with Postgres).
- **Hosted sync (atuin.sh)**: CLI syncs with the official hosted server.

## Unknowns

- Exact runtime interaction between V1 and V2 sync protocols — are they mutually exclusive?
- Whether the `atuin-ai` crate is actively used or experimental.
- Deployment topology of the hosted atuin.sh service.

```

### architecture/views/component-client-library.yaml

```yaml
view_type: "component"
title: "Client Library - Component View"
description: "Internal components of the atuin-client library."
parent_container: "client-library"
elements:
  - ref: "client-history-store"
  - ref: "client-record-store"
  - ref: "client-encryption"
  - ref: "client-sync"
  - ref: "client-api"
  # Context elements for relationship rendering
  - ref: "local-sqlite"
  - ref: "atuin-sync-server"
relationships:
  - ref: "rel-sync-recordstore"
  - ref: "rel-sync-encryption"
  - ref: "rel-sync-api"
  - ref: "rel-client-sqlite"
  - ref: "rel-client-server"
notes:
  - "The record store is the V2 sync abstraction — all data types share this infrastructure via tagged records."
  - "Encryption happens at the record store level before sync. The server never sees plaintext."
  - "The history store uses a separate SQLite database from the record store."

```

### architecture/views/component-server.yaml

```yaml
view_type: "component"
title: "Sync Server - Component View"
description: "Internal components of the Atuin sync server."
parent_container: "server-binary"
elements:
  - ref: "server-handlers"
  - ref: "server-auth"
  - ref: "server-database-trait"
  # Context elements
  - ref: "postgres"
relationships:
  - ref: "rel-handlers-auth"
  - ref: "rel-handlers-db"
  - ref: "rel-server-postgres"
notes:
  - "The Database trait has two implementations: atuin-server-postgres and atuin-server-sqlite."
  - "Backend type is selected at startup based on the DB URI prefix."
  - "Auth uses simple token-based sessions, not OIDC (OIDC is optional and separate)."

```

### architecture/views/container.yaml

```yaml
view_type: "container"
title: "Atuin - Container View"
description: "Runtime containers within the Atuin system."
elements:
  - ref: "atuin-cli"
  - ref: "atuin-daemon-container"
  - ref: "client-library"
  - ref: "local-sqlite"
  - ref: "server-binary"
  - ref: "shell-user"
  - ref: "postgres"
  - ref: "atuin-sync-server"
relationships:
  - ref: "rel-user-cli"
  - ref: "rel-shell-daemon"
  - ref: "rel-cli-client"
  - ref: "rel-daemon-client"
  - ref: "rel-client-sqlite"
  - ref: "rel-client-server"
  - ref: "rel-server-postgres"
notes:
  - "The client-library is modeled as a container (shared library) because it is the core runtime unit consumed by both CLI and daemon."
  - "The sync server can use SQLite instead of Postgres — this is a deployment mode choice, not an architectural difference."
  - "The daemon communicates via Unix socket gRPC, providing low-latency history recording for shell hooks."

```

### architecture/views/sequence-history-capture.yaml

```yaml
view_type: "sequence"
title: "History Capture"
description: "How a shell command is recorded via shell hooks."
participants:
  - ref: "shell-user"
  - ref: "atuin-cli"
  - ref: "client-history-store"
  - ref: "local-sqlite"
steps:
  - seq: 1
    source: "shell-user"
    target: "atuin-cli"
    label: "Shell hook calls 'atuin history start <command>'"
    sync_async: "sync"
    notes: "Hot path — must be fast. Skips database initialization."

  - seq: 2
    source: "atuin-cli"
    target: "client-history-store"
    label: "Create history entry with command, cwd, hostname, session"
    sync_async: "sync"

  - seq: 3
    source: "client-history-store"
    target: "local-sqlite"
    label: "INSERT history record"
    sync_async: "sync"
    protocol: "sqlite"

  - seq: 4
    source: "shell-user"
    target: "atuin-cli"
    label: "Shell hook calls 'atuin history end <id> --exit <code> --duration <ms>'"
    sync_async: "sync"
    notes: "Hot path — must be fast."

  - seq: 5
    source: "atuin-cli"
    target: "client-history-store"
    label: "Update history entry with exit code and duration"
    sync_async: "sync"

  - seq: 6
    source: "client-history-store"
    target: "local-sqlite"
    label: "UPDATE history record"
    sync_async: "sync"
    protocol: "sqlite"

notes:
  - "'history start' and 'history end' are hot paths that skip database initialization for latency."
  - "When the daemon is running, shell hooks route through the daemon's gRPC interface instead of directly spawning CLI processes."

```

### architecture/views/sequence-sync.yaml

```yaml
view_type: "sequence"
title: "Record Sync (V2)"
description: "Bidirectional sync flow for encrypted records between client and server."
participants:
  - ref: "atuin-cli"
  - ref: "client-sync"
  - ref: "client-record-store"
  - ref: "client-encryption"
  - ref: "client-api"
  - ref: "atuin-sync-server"
steps:
  - seq: 1
    source: "atuin-cli"
    target: "client-sync"
    label: "Trigger sync"
    sync_async: "sync"

  - seq: 2
    source: "client-sync"
    target: "client-record-store"
    label: "Get local record status (host, tag, idx)"
    sync_async: "sync"

  - seq: 3
    source: "client-sync"
    target: "client-api"
    label: "Get remote record status"
    sync_async: "sync"

  - seq: 4
    source: "client-api"
    target: "atuin-sync-server"
    label: "GET /api/v0/record/status"
    sync_async: "sync"
    protocol: "https"

  - seq: 5
    source: "client-sync"
    target: "client-sync"
    label: "Compute diff (uploads and downloads)"
    sync_async: "sync"

  - seq: 6
    source: "client-sync"
    target: "client-record-store"
    label: "Fetch local records to upload"
    sync_async: "sync"

  - seq: 7
    source: "client-sync"
    target: "client-encryption"
    label: "Encrypt records with envelope encryption (PASETO V4)"
    sync_async: "sync"

  - seq: 8
    source: "client-sync"
    target: "client-api"
    label: "Upload encrypted records"
    sync_async: "sync"

  - seq: 9
    source: "client-api"
    target: "atuin-sync-server"
    label: "POST /api/v0/record"
    sync_async: "sync"
    protocol: "https"

  - seq: 10
    source: "client-sync"
    target: "client-api"
    label: "Download missing records from server"
    sync_async: "sync"

  - seq: 11
    source: "client-api"
    target: "atuin-sync-server"
    label: "GET /api/v0/record/next"
    sync_async: "sync"
    protocol: "https"

  - seq: 12
    source: "client-sync"
    target: "client-encryption"
    label: "Decrypt downloaded records"
    sync_async: "sync"

  - seq: 13
    source: "client-sync"
    target: "client-record-store"
    label: "Store decrypted records locally"
    sync_async: "sync"

notes:
  - "The server never sees plaintext — all encryption/decryption happens client-side."
  - "Sync is bidirectional: the client computes a diff and then both uploads and downloads."
  - "V1 legacy sync is a separate code path for direct history entry sync, being phased out."

```

### architecture/views/system-context.yaml

```yaml
view_type: "system_context"
title: "Atuin - System Context"
description: "High-level view of Atuin and its external dependencies."
elements:
  - ref: "atuin-system"
  - ref: "shell-user"
  - ref: "atuin-sync-server"
  - ref: "postgres"
relationships:
  - ref: "rel-user-cli"
  - ref: "rel-client-server"
  - ref: "rel-server-postgres"
notes:
  - "The sync server is optional — Atuin works fully offline with local SQLite."
  - "The OIDC issuer and telemetry collector are omitted as they are not relevant at this level."

```
