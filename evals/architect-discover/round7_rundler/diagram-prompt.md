# Diagram Prompt Bundle — round7_rundler
## Agent Instruction: Execute the Prompt Below Exactly
If this file is uploaded without any user-typed prompt, treat the prompt in the code block below as the full instruction and execute it directly.
```text
You are a senior architecture visualization engineer.

Build a single self-contained interactive architecture diagram for **Rundler** from the provided files.

Output requirements:
1) Return one HTML file with inline CSS and inline JavaScript only.
2) Support drill-down navigation across the provided static views:
   - System Context
   - Container View
   - Component Views
   - Deployment View
3) Sequence diagrams are disabled in the main drill-down surface unless explicitly requested.
4) Include breadcrumb navigation and a back affordance.
5) Single-click opens a details panel with name, type, technology, description, owned data, and confidence.
6) Drill-down should preserve exact element and relationship IDs from the source artifacts.
7) Implement Comment Mode with target metadata on nodes and edges.
8) Do not invent elements, relationships, or claims not present in the provided files.
9) Do not render confidence labels directly on the diagram canvas.
10) Person nodes must render as padded rectangular cards rather than large pictogram silhouettes.
11) Relationship strokes should stay visually subtle, with larger invisible hit targets for interaction.
```

## Virtual Directory Tree

```text
round7_rundler/
  architecture/
    manifest.yaml
    model.yaml
    summary.md
    views/
      system-context.yaml
      container.yaml
      component-rundler-rpc.yaml
      component-rundler-pool.yaml
      component-rundler-builder.yaml
      deployment.yaml
```

## File Contents

### architecture/manifest.yaml

```yaml
version: 2
system_name: "Rundler"
generated_by_skill: "architect-discover"
mode: "initial"
evidence_basis: "code"
repo_archetype: "service_oriented_backend"
modeling_style:
  primary: "C4"
  supplemental:
    - "Sequence"
    - "Deployment"
scope:
  in_scope:
    - "evals/repos/rundler/bin/rundler/"
    - "evals/repos/rundler/crates/rpc/"
    - "evals/repos/rundler/crates/pool/"
    - "evals/repos/rundler/crates/builder/"
    - "evals/repos/rundler/crates/signer/"
    - "evals/repos/rundler/crates/types/"
    - "evals/repos/rundler/docs/architecture/"
    - "evals/repos/rundler/test/spec-tests/remote/docker-compose.yml"
  out_of_scope:
    - "Alchemy production control plane and traffic management layers not defined in this repo"
    - "Future P2P mempool and roadmap work that is mentioned in docs but not modeled as a current runtime boundary"
    - "Spec-test harness internals outside the concrete remote deployment example"
audiences:
  - "new_hires"
  - "pms"
  - "senior_architects"
artifacts:
  - id: "model"
    path: "architecture/model.yaml"
    type: "canonical_model"
    status: "complete"
  - id: "view-system-context"
    path: "architecture/views/system-context.yaml"
    type: "system_context"
    status: "complete"
  - id: "view-container"
    path: "architecture/views/container.yaml"
    type: "container"
    status: "complete"
  - id: "view-component-rundler-rpc"
    path: "architecture/views/component-rundler-rpc.yaml"
    type: "component"
    status: "complete"
  - id: "view-component-rundler-pool"
    path: "architecture/views/component-rundler-pool.yaml"
    type: "component"
    status: "complete"
  - id: "view-component-rundler-builder"
    path: "architecture/views/component-rundler-builder.yaml"
    type: "component"
    status: "complete"
  - id: "view-sequence-user-operation-ingest"
    path: "architecture/views/sequence-user-operation-ingest.yaml"
    type: "sequence"
    status: "complete"
  - id: "view-sequence-bundle-construction-and-submission"
    path: "architecture/views/sequence-bundle-construction-and-submission.yaml"
    type: "sequence"
    status: "complete"
  - id: "view-deployment"
    path: "architecture/views/deployment.yaml"
    type: "deployment"
    status: "complete"
  - id: "summary"
    path: "architecture/summary.md"
    type: "summary"
    status: "complete"
assumptions:
  - text: "The stable runtime architecture is the RPC, Pool, and Builder task split; `node` and `backend` are deployment modes that collocate those same roles rather than separate containers."
    confidence: "confirmed"
  - text: "AWS KMS, Redis key leasing, and private relay integrations are optional runtime dependencies because the code gates them behind signer and sender configuration."
    confidence: "confirmed"
  - text: "The remote spec-test docker compose is the strongest concrete deployment evidence for split-process operation available in the repo."
    confidence: "confirmed"
unknowns:
  - "The production topology used by Alchemy outside the repo is not described beyond high-level README language."
  - "The README entry point support section still lists v0.6 and v0.7 only, while current code paths also encode v0.8 and v0.9 support."
overall_summary: "Rundler is an ERC-4337 bundler backend implemented as a Rust workspace with three primary runtime roles: RPC, Pool, and Builder. Those roles can run integrated in one process or split across processes that communicate over local handles or gRPC. The Pool owns the live user operation lifecycle state, while the Builder owns bundle execution state and optional signer infrastructure integrations."
```

### architecture/model.yaml

```yaml
version: 2
system_name: "Rundler"
repo_archetype: "service_oriented_backend"
elements:
  - id: "dapp-user"
    name: "DApp / Wallet User"
    aliases:
      - "AA client"
    kind: "person"
    c4_level: "context"
    description: "External client that submits ERC-4337 user operations and polls for status."
    responsibility: "Send user operations to Rundler and consume bundler responses."
    technology: ""
    owned_data: []
    system_of_record: []
    runtime_boundary: "external"
    deployable: false
    external: true
    source_paths:
      - "README.md"
      - "docs/architecture/rpc.md"
    tags:
      - "external-actor"
    confidence: "confirmed"
    evidence_ids:
      - "ev-readme"
      - "ev-rpc-doc"

  - id: "bundler-operator"
    name: "Bundler Operator"
    aliases:
      - "Rundler admin"
    kind: "person"
    c4_level: "context"
    description: "Human operator running, configuring, and debugging Rundler deployments."
    responsibility: "Configure runtime mode, inspect state, and trigger admin or debug flows."
    technology: ""
    owned_data: []
    system_of_record: []
    runtime_boundary: "external"
    deployable: false
    external: true
    source_paths:
      - "bin/rundler/src/cli/mod.rs"
      - "docs/architecture/rpc.md"
    tags:
      - "external-actor"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-mod"
      - "ev-rpc-doc"

  - id: "rundler"
    name: "Rundler"
    aliases:
      - "Rust Bundler"
    kind: "software_system"
    c4_level: "context"
    description: "ERC-4337 bundler backend that validates, pools, bundles, and submits user operations on EVM chains."
    responsibility: "Provide bundler APIs, manage local mempool state, and turn accepted user operations into submitted bundle transactions."
    technology: "Rust"
    owned_data:
      - "user_operation_lifecycle"
      - "bundle_submission_lifecycle"
    system_of_record:
      - "user_operation_lifecycle"
      - "bundle_submission_lifecycle"
    runtime_boundary: "process"
    deployable: true
    external: false
    source_paths:
      - "README.md"
      - "docs/architecture/README.md"
      - "bin/rundler/src/cli/mod.rs"
    tags:
      - "erc-4337"
      - "bundler"
    confidence: "confirmed"
    evidence_ids:
      - "ev-readme"
      - "ev-arch-readme"
      - "ev-cli-mod"

  - id: "evm-json-rpc-node"
    name: "EVM JSON-RPC Node"
    aliases:
      - "execution client"
    kind: "external_system"
    c4_level: "context"
    description: "External EVM node used for chain state reads, simulation, receipts, and transaction submission."
    responsibility: "Expose chain data and transaction RPCs consumed by Rundler runtime tasks."
    technology: "JSON-RPC over HTTP(S)"
    owned_data:
      - "chain_state"
      - "transaction_receipts"
    system_of_record:
      - "chain_state"
      - "transaction_receipts"
    runtime_boundary: "external"
    deployable: false
    external: true
    source_paths:
      - "bin/rundler/src/cli/rpc.rs"
      - "bin/rundler/src/cli/pool.rs"
      - "bin/rundler/src/cli/builder.rs"
      - "test/spec-tests/remote/docker-compose.yml"
    tags:
      - "required"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-rpc"
      - "ev-cli-pool"
      - "ev-cli-builder"
      - "ev-remote-compose"

  - id: "entrypoint-contract"
    name: "EntryPoint Contract"
    aliases:
      - "ERC-4337 EntryPoint"
    kind: "external_system"
    c4_level: "context"
    description: "On-chain ERC-4337 EntryPoint contract that validates and executes bundle transactions."
    responsibility: "Execute handleOps-style bundle transactions against supported entry point versions."
    technology: "EVM smart contract"
    owned_data:
      - "onchain_user_operation_execution"
    system_of_record:
      - "onchain_user_operation_execution"
    runtime_boundary: "external"
    deployable: false
    external: true
    source_paths:
      - "crates/types/src/chain.rs"
      - "crates/builder/proto/builder/builder.proto"
    tags:
      - "required"
    confidence: "confirmed"
    evidence_ids:
      - "ev-chain-types"
      - "ev-builder-proto"

  - id: "private-transaction-relay"
    name: "Private Transaction Relay"
    aliases:
      - "Flashbots Protect"
      - "Bloxroute"
    kind: "external_system"
    c4_level: "context"
    description: "Optional private transaction submission backend used by configured builder sender implementations."
    responsibility: "Accept private bundle submission requests for supported chains and sender types."
    technology: "HTTPS"
    owned_data: []
    system_of_record: []
    runtime_boundary: "external"
    deployable: false
    external: true
    source_paths:
      - "bin/rundler/src/cli/builder.rs"
      - "docs/architecture/builder.md"
      - "crates/builder/src/sender/flashbots.rs"
    tags:
      - "optional"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-builder"
      - "ev-builder-doc"
      - "ev-builder-flashbots"

  - id: "aws-kms"
    name: "AWS KMS"
    aliases: []
    kind: "external_system"
    c4_level: "context"
    description: "Optional managed signer backend for builder transaction signing."
    responsibility: "Hold signing keys and produce signatures when KMS-backed signing is enabled."
    technology: "AWS KMS API"
    owned_data:
      - "kms_signing_keys"
    system_of_record:
      - "kms_signing_keys"
    runtime_boundary: "external"
    deployable: false
    external: true
    source_paths:
      - "bin/rundler/src/cli/signer.rs"
      - "crates/signer/src/aws.rs"
      - "docs/architecture/builder.md"
    tags:
      - "optional"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-signer"
      - "ev-signer-aws"
      - "ev-builder-doc"

  - id: "rundler-rpc"
    name: "Rundler RPC"
    aliases:
      - "RPC Server"
    kind: "container"
    c4_level: "container"
    description: "JSON-RPC edge service exposing eth_, debug_, rundler_, and admin namespaces plus health checks."
    responsibility: "Receive user-facing and operator-facing API requests, route work to Pool and Builder, and perform gas estimation against chain data."
    technology: "Rust / jsonrpsee"
    owned_data: []
    system_of_record: []
    runtime_boundary: "process"
    deployable: true
    external: false
    source_paths:
      - "bin/rundler/src/cli/rpc.rs"
      - "crates/rpc/src/lib.rs"
      - "docs/architecture/rpc.md"
    tags:
      - "edge"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-rpc"
      - "ev-rpc-lib"
      - "ev-rpc-doc"

  - id: "rundler-pool"
    name: "Rundler Pool"
    aliases:
      - "Mempool"
    kind: "container"
    c4_level: "container"
    description: "Stateful task that validates, stores, and updates pending user operations per entry point."
    responsibility: "Own the live mempool, track reputation and paymaster state, and reconcile state on block updates and reorgs."
    technology: "Rust / tonic + tokio"
    owned_data:
      - "user_operations_mempool"
      - "entity_reputation"
      - "paymaster_balances"
      - "mined_user_operation_cache"
    system_of_record:
      - "user_operation_lifecycle"
      - "entity_reputation"
      - "paymaster_balance_tracking"
    runtime_boundary: "process"
    deployable: true
    external: false
    source_paths:
      - "bin/rundler/src/cli/pool.rs"
      - "crates/pool/src/lib.rs"
      - "docs/architecture/pool.md"
    tags:
      - "stateful"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-pool"
      - "ev-pool-lib"
      - "ev-pool-doc"

  - id: "rundler-builder"
    name: "Rundler Builder"
    aliases: []
    kind: "container"
    c4_level: "container"
    description: "Worker-oriented task that assigns work, builds bundles, signs transactions, submits them, and tracks outcomes."
    responsibility: "Turn eligible user operations into bundle transactions and manage the full submission lifecycle."
    technology: "Rust / tonic + tokio"
    owned_data:
      - "worker_assignments"
      - "pending_bundle_state"
    system_of_record:
      - "bundle_submission_lifecycle"
      - "worker_assignments"
    runtime_boundary: "process"
    deployable: true
    external: false
    source_paths:
      - "bin/rundler/src/cli/builder.rs"
      - "crates/builder/src/lib.rs"
      - "docs/architecture/builder.md"
    tags:
      - "worker"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-builder"
      - "ev-builder-lib"
      - "ev-builder-doc"

  - id: "redis-lock-store"
    name: "Redis Lock Store"
    aliases:
      - "Redis"
    kind: "cache"
    c4_level: "container"
    description: "Optional external lock store used only for KMS signer key leasing."
    responsibility: "Lease KMS keys to a single signer worker at a time to avoid nonce collisions."
    technology: "Redis"
    owned_data:
      - "kms_signer_leases"
    system_of_record:
      - "kms_signer_leases"
    runtime_boundary: "data_store"
    deployable: false
    external: true
    source_paths:
      - "bin/rundler/src/cli/signer.rs"
      - "crates/signer/src/lib.rs"
      - "crates/signer/src/aws.rs"
    tags:
      - "optional"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-signer"
      - "ev-signer-lib"
      - "ev-signer-aws"

  - id: "rpc-eth-api"
    name: "RPC Eth API"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Implements ERC-4337 eth_ RPC methods including sendUserOperation and estimateUserOperationGas."
    responsibility: "Handle standard user-operation methods and delegate entry point specific work."
    technology: "Rust"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "rundler-rpc"
    source_paths:
      - "crates/rpc/src/eth/server.rs"
      - "crates/rpc/src/eth/mod.rs"
    tags: []
    confidence: "confirmed"
    evidence_ids:
      - "ev-rpc-eth-server"
      - "ev-rpc-eth-mod"

  - id: "rpc-rundler-api"
    name: "RPC Rundler API"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Implements Rundler-specific RPC methods such as gas price guidance, dropLocalUserOperation, and delegation status."
    responsibility: "Expose Rundler-only operational APIs on top of shared runtime state."
    technology: "Rust"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "rundler-rpc"
    source_paths:
      - "crates/rpc/src/rundler.rs"
    tags: []
    confidence: "confirmed"
    evidence_ids:
      - "ev-rpc-rundler"

  - id: "rpc-debug-admin-api"
    name: "RPC Debug/Admin API"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Implements debug_ and admin_ control paths that inspect and mutate Pool and Builder runtime state."
    responsibility: "Trigger debug bundles, clear state, set tracking, and dump operational internals."
    technology: "Rust"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "rundler-rpc"
    source_paths:
      - "crates/rpc/src/debug.rs"
      - "crates/rpc/src/admin.rs"
    tags: []
    confidence: "confirmed"
    evidence_ids:
      - "ev-rpc-debug"
      - "ev-rpc-admin"

  - id: "rpc-entrypoint-router"
    name: "RPC Entry Point Router"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Routes RPC requests by entry point address and version and wires gas estimators to the right runtime dependencies."
    responsibility: "Dispatch user-operation requests to version-aware handlers and chain-backed estimation paths."
    technology: "Rust"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "rundler-rpc"
    source_paths:
      - "crates/rpc/src/eth/router.rs"
      - "crates/rpc/src/task.rs"
    tags: []
    confidence: "confirmed"
    evidence_ids:
      - "ev-rpc-router"
      - "ev-rpc-task"

  - id: "pool-server"
    name: "Pool Server"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Local and remote server facade that receives RPC and Builder requests for pool operations."
    responsibility: "Expose Pool capabilities over in-process handles or gRPC."
    technology: "Rust / tonic"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "rundler-pool"
    source_paths:
      - "crates/pool/src/server/mod.rs"
      - "crates/pool/src/server/remote/client.rs"
    tags: []
    confidence: "confirmed"
    evidence_ids:
      - "ev-pool-server"
      - "ev-pool-remote-client"

  - id: "pool-chain-tracker"
    name: "Pool Chain Tracker"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Chain polling and reorg tracker that updates Pool state from new blocks and mined or unmined user operations."
    responsibility: "Watch chain progression and reconcile mempool state with on-chain execution."
    technology: "Rust"
    owned_data:
      - "mined_user_operation_cache"
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "rundler-pool"
    source_paths:
      - "crates/pool/src/chain.rs"
      - "docs/architecture/pool.md"
    tags: []
    confidence: "confirmed"
    evidence_ids:
      - "ev-pool-chain"
      - "ev-pool-doc"

  - id: "pool-mempool"
    name: "Pool Mempool Core"
    aliases:
      - "UO Pool"
    kind: "component"
    c4_level: "component"
    description: "Per-entry-point in-memory user operation pool that runs prechecks, simulation, admission, and eviction logic."
    responsibility: "Own pending user operations and enforce acceptance and replacement rules."
    technology: "Rust"
    owned_data:
      - "user_operations_mempool"
    system_of_record:
      - "user_operation_lifecycle"
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "rundler-pool"
    source_paths:
      - "crates/pool/src/mempool/uo_pool.rs"
      - "docs/architecture/pool.md"
    tags: []
    confidence: "confirmed"
    evidence_ids:
      - "ev-pool-uo-pool"
      - "ev-pool-doc"

  - id: "pool-reputation-manager"
    name: "Pool Reputation Manager"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Tracks ERC-4337 entity reputation and allowlist or blocklist overrides."
    responsibility: "Maintain throttling and banning state used during Pool admission."
    technology: "Rust"
    owned_data:
      - "entity_reputation"
    system_of_record:
      - "entity_reputation"
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "rundler-pool"
    source_paths:
      - "crates/pool/src/mempool/reputation.rs"
      - "docs/architecture/pool.md"
    tags: []
    confidence: "confirmed"
    evidence_ids:
      - "ev-pool-reputation"
      - "ev-pool-doc"

  - id: "pool-paymaster-tracker"
    name: "Pool Paymaster Tracker"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Tracks confirmed and pending paymaster balances as part of mempool admission and reconciliation."
    responsibility: "Maintain paymaster balance metadata used to accept or reject pending user operations."
    technology: "Rust"
    owned_data:
      - "paymaster_balances"
    system_of_record:
      - "paymaster_balance_tracking"
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "rundler-pool"
    source_paths:
      - "crates/pool/src/mempool/paymaster.rs"
      - "docs/architecture/pool.md"
    tags: []
    confidence: "confirmed"
    evidence_ids:
      - "ev-pool-paymaster"
      - "ev-pool-doc"

  - id: "builder-assigner"
    name: "Builder Assigner"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Coordinates worker selection, starvation prevention, and sender-level work assignment across entry points."
    responsibility: "Choose which entry point a worker should build for and avoid duplicate sender assignment across workers."
    technology: "Rust"
    owned_data:
      - "worker_assignments"
    system_of_record:
      - "worker_assignments"
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "rundler-builder"
    source_paths:
      - "crates/builder/src/assigner.rs"
      - "docs/architecture/builder.md"
    tags: []
    confidence: "confirmed"
    evidence_ids:
      - "ev-builder-assigner"
      - "ev-builder-doc"

  - id: "builder-bundle-proposer"
    name: "Builder Bundle Proposer"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Constructs candidate bundles by re-simulating operations, enforcing profitability, and preparing transactions."
    responsibility: "Turn assigned operations into a valid bundle candidate."
    technology: "Rust"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "rundler-builder"
    source_paths:
      - "crates/builder/src/bundle_proposer.rs"
      - "docs/architecture/builder.md"
    tags: []
    confidence: "confirmed"
    evidence_ids:
      - "ev-builder-proposer"
      - "ev-builder-doc"

  - id: "builder-bundle-sender-workers"
    name: "Builder Bundle Sender Workers"
    aliases:
      - "bundle sender state machine"
    kind: "component"
    c4_level: "component"
    description: "Worker state machines that build, submit, retry, and cancel bundle transactions."
    responsibility: "Drive the bundle submission lifecycle from trigger through mined, dropped, or cancelled outcomes."
    technology: "Rust"
    owned_data:
      - "pending_bundle_state"
    system_of_record:
      - "bundle_submission_lifecycle"
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "rundler-builder"
    source_paths:
      - "crates/builder/src/bundle_sender.rs"
      - "docs/architecture/builder.md"
    tags: []
    confidence: "confirmed"
    evidence_ids:
      - "ev-builder-bundle-sender"
      - "ev-builder-doc"

  - id: "builder-transaction-sender"
    name: "Builder Transaction Sender"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Pluggable submission backend for raw RPC, Flashbots, Bloxroute, and other transaction send modes."
    responsibility: "Submit or cancel bundle transactions through the configured transport."
    technology: "Rust"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "rundler-builder"
    source_paths:
      - "crates/builder/src/sender/flashbots.rs"
      - "crates/builder/src/sender/polygon_private.rs"
      - "bin/rundler/src/cli/builder.rs"
    tags: []
    confidence: "confirmed"
    evidence_ids:
      - "ev-builder-flashbots"
      - "ev-builder-polygon-private"
      - "ev-cli-builder"

  - id: "builder-signer-manager"
    name: "Builder Signer Manager"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Manages private-key, mnemonic, or KMS-backed transaction signers and optional key leasing."
    responsibility: "Provide signing capacity to builder workers and coordinate KMS key locking when enabled."
    technology: "Rust"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "rundler-builder"
    source_paths:
      - "crates/signer/src/lib.rs"
      - "crates/signer/src/aws.rs"
      - "bin/rundler/src/cli/signer.rs"
    tags: []
    confidence: "confirmed"
    evidence_ids:
      - "ev-signer-lib"
      - "ev-signer-aws"
      - "ev-cli-signer"

  - id: "deployment-rpc-host"
    name: "RPC Host"
    aliases: []
    kind: "deployment_node"
    c4_level: "deployment"
    description: "Runtime node hosting the split Rundler RPC task."
    responsibility: "Run the RPC process in distributed mode."
    technology: "Container host"
    owned_data: []
    system_of_record: []
    runtime_boundary: "network_zone"
    deployable: false
    external: false
    source_paths:
      - "test/spec-tests/remote/docker-compose.yml"
    tags: []
    confidence: "confirmed"
    evidence_ids:
      - "ev-remote-compose"

  - id: "deployment-pool-host"
    name: "Pool Host"
    aliases: []
    kind: "deployment_node"
    c4_level: "deployment"
    description: "Runtime node hosting the split Rundler Pool task."
    responsibility: "Run the Pool process in distributed mode."
    technology: "Container host"
    owned_data: []
    system_of_record: []
    runtime_boundary: "network_zone"
    deployable: false
    external: false
    source_paths:
      - "test/spec-tests/remote/docker-compose.yml"
    tags: []
    confidence: "confirmed"
    evidence_ids:
      - "ev-remote-compose"

  - id: "deployment-builder-host"
    name: "Builder Host"
    aliases: []
    kind: "deployment_node"
    c4_level: "deployment"
    description: "Runtime node hosting the split Rundler Builder task."
    responsibility: "Run the Builder process in distributed mode."
    technology: "Container host"
    owned_data: []
    system_of_record: []
    runtime_boundary: "network_zone"
    deployable: false
    external: false
    source_paths:
      - "test/spec-tests/remote/docker-compose.yml"
    tags: []
    confidence: "confirmed"
    evidence_ids:
      - "ev-remote-compose"

  - id: "deployment-redis-service"
    name: "Redis Service"
    aliases: []
    kind: "deployment_node"
    c4_level: "deployment"
    description: "Separate service boundary used when KMS key leasing is enabled."
    responsibility: "Host the Redis lock store used by KMS-backed signer sharing."
    technology: "Managed service or container"
    owned_data: []
    system_of_record: []
    runtime_boundary: "network_zone"
    deployable: false
    external: false
    source_paths:
      - "bin/rundler/src/cli/signer.rs"
      - "crates/signer/src/aws.rs"
    tags: []
    confidence: "strong_inference"
    evidence_ids:
      - "ev-cli-signer"
      - "ev-signer-aws"
relationships:
  - id: "dapp-user-calls-rundler"
    source_id: "dapp-user"
    target_id: "rundler"
    label: "Submits user operations and polls status"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "user_operations"
      - "status_queries"
    confidence: "confirmed"
    evidence_ids:
      - "ev-readme"
      - "ev-rpc-doc"

  - id: "bundler-operator-calls-rundler"
    source_id: "bundler-operator"
    target_id: "rundler"
    label: "Configures and debugs bundler state"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "human"
    protocol: "manual"
    data_objects:
      - "debug_commands"
      - "admin_commands"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-mod"
      - "ev-rpc-doc"

  - id: "rundler-calls-evm-json-rpc-node"
    source_id: "rundler"
    target_id: "evm-json-rpc-node"
    label: "Reads chain state, simulates, and submits transactions"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "chain_state"
      - "simulation_calls"
      - "bundle_transactions"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-rpc"
      - "ev-cli-pool"
      - "ev-cli-builder"

  - id: "rundler-submits-bundles-to-entrypoint-contract"
    source_id: "rundler"
    target_id: "entrypoint-contract"
    label: "Executes handleOps-style bundles on-chain"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "async"
    protocol: "n_a"
    data_objects:
      - "bundle_transactions"
    confidence: "confirmed"
    evidence_ids:
      - "ev-builder-proto"
      - "ev-builder-doc"

  - id: "rundler-calls-private-transaction-relay"
    source_id: "rundler"
    target_id: "private-transaction-relay"
    label: "Optionally submits bundles through private relays"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "bundle_transactions"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-builder"
      - "ev-builder-doc"
      - "ev-builder-flashbots"

  - id: "rundler-calls-aws-kms"
    source_id: "rundler"
    target_id: "aws-kms"
    label: "Optionally signs bundle transactions with KMS keys"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "signing_requests"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-signer"
      - "ev-signer-aws"

  - id: "dapp-user-calls-rundler-rpc"
    source_id: "dapp-user"
    target_id: "rundler-rpc"
    label: "Calls eth_ and rundler_ JSON-RPC methods"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "user_operations"
      - "gas_estimation_requests"
      - "status_queries"
    confidence: "confirmed"
    evidence_ids:
      - "ev-rpc-doc"
      - "ev-rpc-eth-server"
      - "ev-rpc-rundler"

  - id: "bundler-operator-calls-rundler-rpc"
    source_id: "bundler-operator"
    target_id: "rundler-rpc"
    label: "Calls debug_ and admin_ endpoints"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "debug_commands"
      - "state_dumps"
    confidence: "confirmed"
    evidence_ids:
      - "ev-rpc-doc"
      - "ev-rpc-debug"
      - "ev-rpc-admin"

  - id: "rundler-rpc-calls-rundler-pool"
    source_id: "rundler-rpc"
    target_id: "rundler-pool"
    label: "Forwards user operation submission and state queries"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: ""
    data_objects:
      - "user_operations"
      - "pool_queries"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-rpc"
      - "ev-rpc-doc"
      - "ev-pool-remote-client"

  - id: "rundler-rpc-calls-rundler-builder"
    source_id: "rundler-rpc"
    target_id: "rundler-builder"
    label: "Triggers debug bundling and builder control paths"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: ""
    data_objects:
      - "debug_bundle_commands"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-rpc"
      - "ev-rpc-doc"

  - id: "rundler-rpc-calls-evm-json-rpc-node"
    source_id: "rundler-rpc"
    target_id: "evm-json-rpc-node"
    label: "Runs gas estimation and receipt lookups against chain data"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "gas_estimation_requests"
      - "user_operation_receipts"
    confidence: "confirmed"
    evidence_ids:
      - "ev-rpc-task"
      - "ev-rpc-router"
      - "ev-rpc-doc"

  - id: "rundler-pool-calls-evm-json-rpc-node"
    source_id: "rundler-pool"
    target_id: "evm-json-rpc-node"
    label: "Simulates operations and tracks chain updates"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "debug_trace_calls"
      - "block_updates"
      - "mined_user_operations"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-pool"
      - "ev-pool-doc"
      - "ev-pool-chain"

  - id: "rundler-builder-calls-rundler-pool"
    source_id: "rundler-builder"
    target_id: "rundler-pool"
    label: "Fetches eligible operations and reports failures"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: ""
    data_objects:
      - "best_operations_requests"
      - "rejected_user_operations"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-builder"
      - "ev-builder-doc"

  - id: "rundler-pool-publishes-to-rundler-builder"
    source_id: "rundler-pool"
    target_id: "rundler-builder"
    label: "Publishes new block and mempool update signals"
    interaction_type: "publishes"
    directionality: "unidirectional"
    sync_async: "async"
    protocol: ""
    data_objects:
      - "block_update_events"
      - "pool_events"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-node"
      - "ev-builder-doc"

  - id: "rundler-builder-calls-evm-json-rpc-node"
    source_id: "rundler-builder"
    target_id: "evm-json-rpc-node"
    label: "Re-simulates bundles and submits transactions"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "bundle_simulation_requests"
      - "bundle_transactions"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-builder"
      - "ev-builder-doc"

  - id: "rundler-builder-submits-bundles-to-entrypoint-contract"
    source_id: "rundler-builder"
    target_id: "entrypoint-contract"
    label: "Submits bundle transactions that execute EntryPoint logic"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "async"
    protocol: "n_a"
    data_objects:
      - "bundle_transactions"
    confidence: "confirmed"
    evidence_ids:
      - "ev-builder-doc"
      - "ev-builder-proto"

  - id: "rundler-builder-calls-private-transaction-relay"
    source_id: "rundler-builder"
    target_id: "private-transaction-relay"
    label: "Uses private transaction sender implementations when configured"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "bundle_transactions"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-builder"
      - "ev-builder-flashbots"
      - "ev-builder-polygon-private"

  - id: "rundler-builder-calls-aws-kms"
    source_id: "rundler-builder"
    target_id: "aws-kms"
    label: "Uses KMS-backed signer implementations when enabled"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "signing_requests"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-signer"
      - "ev-signer-aws"

  - id: "rundler-builder-calls-redis-lock-store"
    source_id: "rundler-builder"
    target_id: "redis-lock-store"
    label: "Leases KMS keys to signer workers"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "n_a"
    data_objects:
      - "kms_signer_leases"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-signer"
      - "ev-signer-lib"
      - "ev-signer-aws"

  - id: "rpc-eth-api-calls-rpc-entrypoint-router"
    source_id: "rpc-eth-api"
    target_id: "rpc-entrypoint-router"
    label: "Routes user operation methods by entry point"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "eth_sendUserOperation"
      - "eth_estimateUserOperationGas"
    confidence: "confirmed"
    evidence_ids:
      - "ev-rpc-eth-server"
      - "ev-rpc-router"

  - id: "rpc-rundler-api-calls-rpc-entrypoint-router"
    source_id: "rpc-rundler-api"
    target_id: "rpc-entrypoint-router"
    label: "Routes entry point aware Rundler queries"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "rundler_status_queries"
    confidence: "strong_inference"
    evidence_ids:
      - "ev-rpc-rundler"
      - "ev-rpc-router"

  - id: "rpc-entrypoint-router-calls-rundler-pool"
    source_id: "rpc-entrypoint-router"
    target_id: "rundler-pool"
    label: "Delegates addOperation and pool-backed queries"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "user_operations"
      - "pool_queries"
    confidence: "confirmed"
    evidence_ids:
      - "ev-rpc-router"
      - "ev-rpc-doc"

  - id: "rpc-eth-api-calls-evm-json-rpc-node"
    source_id: "rpc-eth-api"
    target_id: "evm-json-rpc-node"
    label: "Uses gas estimator against chain state"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "gas_estimation_requests"
    confidence: "confirmed"
    evidence_ids:
      - "ev-rpc-task"
      - "ev-rpc-router"
      - "ev-rpc-eth-server"

  - id: "rpc-debug-admin-api-calls-rundler-builder"
    source_id: "rpc-debug-admin-api"
    target_id: "rundler-builder"
    label: "Triggers immediate bundles and bundling mode changes"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "debug_bundle_commands"
    confidence: "confirmed"
    evidence_ids:
      - "ev-rpc-debug"

  - id: "rpc-debug-admin-api-calls-rundler-pool"
    source_id: "rpc-debug-admin-api"
    target_id: "rundler-pool"
    label: "Dumps or clears mempool and reputation state"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "mempool_debug_commands"
    confidence: "confirmed"
    evidence_ids:
      - "ev-rpc-debug"
      - "ev-rpc-admin"

  - id: "pool-server-calls-pool-mempool"
    source_id: "pool-server"
    target_id: "pool-mempool"
    label: "Executes pool RPCs against mempool core"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "user_operations"
      - "best_operations_requests"
    confidence: "confirmed"
    evidence_ids:
      - "ev-pool-server"
      - "ev-pool-uo-pool"

  - id: "pool-mempool-calls-pool-reputation-manager"
    source_id: "pool-mempool"
    target_id: "pool-reputation-manager"
    label: "Checks and updates entity reputation during admission"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "entity_reputation"
    confidence: "confirmed"
    evidence_ids:
      - "ev-pool-uo-pool"
      - "ev-pool-reputation"

  - id: "pool-mempool-calls-pool-paymaster-tracker"
    source_id: "pool-mempool"
    target_id: "pool-paymaster-tracker"
    label: "Checks and updates paymaster balances during admission"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "paymaster_balances"
    confidence: "confirmed"
    evidence_ids:
      - "ev-pool-uo-pool"
      - "ev-pool-paymaster"

  - id: "pool-chain-tracker-calls-evm-json-rpc-node"
    source_id: "pool-chain-tracker"
    target_id: "evm-json-rpc-node"
    label: "Polls blocks and decodes mined or unmined operations"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "block_updates"
      - "transaction_receipts"
    confidence: "confirmed"
    evidence_ids:
      - "ev-pool-chain"
      - "ev-pool-doc"

  - id: "pool-chain-tracker-updates-pool-mempool"
    source_id: "pool-chain-tracker"
    target_id: "pool-mempool"
    label: "Applies mined and reorg-derived state updates"
    interaction_type: "triggers"
    directionality: "unidirectional"
    sync_async: "async"
    protocol: "in_process"
    data_objects:
      - "mined_user_operation_cache"
      - "reorg_updates"
    confidence: "confirmed"
    evidence_ids:
      - "ev-pool-chain"
      - "ev-pool-doc"

  - id: "builder-bundle-sender-workers-calls-builder-assigner"
    source_id: "builder-bundle-sender-workers"
    target_id: "builder-assigner"
    label: "Requests entry point and worker assignment"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "worker_assignments"
    confidence: "confirmed"
    evidence_ids:
      - "ev-builder-bundle-sender"
      - "ev-builder-assigner"

  - id: "builder-assigner-calls-rundler-pool"
    source_id: "builder-assigner"
    target_id: "rundler-pool"
    label: "Queries pool for eligible operations by shard and filter"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "best_operations_requests"
    confidence: "confirmed"
    evidence_ids:
      - "ev-builder-doc"
      - "ev-cli-builder"

  - id: "builder-bundle-sender-workers-calls-builder-bundle-proposer"
    source_id: "builder-bundle-sender-workers"
    target_id: "builder-bundle-proposer"
    label: "Builds bundle candidates from assigned operations"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "candidate_user_operations"
    confidence: "confirmed"
    evidence_ids:
      - "ev-builder-bundle-sender"
      - "ev-builder-proposer"

  - id: "builder-bundle-proposer-calls-rundler-pool"
    source_id: "builder-bundle-proposer"
    target_id: "rundler-pool"
    label: "Fetches operations and reports invalid bundle candidates"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "candidate_user_operations"
      - "rejected_user_operations"
    confidence: "confirmed"
    evidence_ids:
      - "ev-builder-doc"
      - "ev-cli-builder"

  - id: "builder-bundle-proposer-calls-evm-json-rpc-node"
    source_id: "builder-bundle-proposer"
    target_id: "evm-json-rpc-node"
    label: "Re-simulates and validates bundle candidates"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "bundle_simulation_requests"
    confidence: "confirmed"
    evidence_ids:
      - "ev-builder-doc"
      - "ev-builder-proposer"

  - id: "builder-bundle-sender-workers-calls-builder-signer-manager"
    source_id: "builder-bundle-sender-workers"
    target_id: "builder-signer-manager"
    label: "Requests signatures for bundle transactions"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "signing_requests"
    confidence: "confirmed"
    evidence_ids:
      - "ev-builder-doc"
      - "ev-signer-lib"

  - id: "builder-bundle-sender-workers-calls-builder-transaction-sender"
    source_id: "builder-bundle-sender-workers"
    target_id: "builder-transaction-sender"
    label: "Submits, retries, or cancels bundle transactions"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects:
      - "bundle_transactions"
      - "cancellation_requests"
    confidence: "confirmed"
    evidence_ids:
      - "ev-builder-bundle-sender"
      - "ev-builder-doc"

  - id: "builder-transaction-sender-calls-evm-json-rpc-node"
    source_id: "builder-transaction-sender"
    target_id: "evm-json-rpc-node"
    label: "Sends raw or conditional bundle transactions"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "bundle_transactions"
    confidence: "confirmed"
    evidence_ids:
      - "ev-cli-builder"
      - "ev-builder-doc"

  - id: "builder-transaction-sender-calls-private-transaction-relay"
    source_id: "builder-transaction-sender"
    target_id: "private-transaction-relay"
    label: "Uses private relay implementations when configured"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "https"
    data_objects:
      - "bundle_transactions"
    confidence: "confirmed"
    evidence_ids:
      - "ev-builder-flashbots"
      - "ev-builder-polygon-private"
evidence:
  - id: "ev-readme"
    path: "README.md"
    kind: "doc"
    strength: "medium"
    reason: "Describes Rundler as a modular ERC-4337 bundler with split RPC, Pool, and Builder roles."
  - id: "ev-arch-readme"
    path: "docs/architecture/README.md"
    kind: "doc"
    strength: "high"
    reason: "Explains the three main tasks and their communication paths."
  - id: "ev-cli-mod"
    path: "bin/rundler/src/cli/mod.rs"
    kind: "runtime_entrypoint"
    strength: "high"
    reason: "Defines node, rpc, pool, builder, admin, and backend modes and spawns tasks for each."
  - id: "ev-cli-node"
    path: "bin/rundler/src/cli/node/mod.rs"
    kind: "runtime_entrypoint"
    strength: "high"
    reason: "Shows integrated mode wiring Pool, Builder, and RPC together with local handles and event channels."
  - id: "ev-cli-backend"
    path: "bin/rundler/src/cli/backend.rs"
    kind: "runtime_entrypoint"
    strength: "high"
    reason: "Shows backend mode collocating Pool and Builder while exposing their gRPC endpoints."
  - id: "ev-cli-rpc"
    path: "bin/rundler/src/cli/rpc.rs"
    kind: "runtime_entrypoint"
    strength: "high"
    reason: "Shows RPC depending on remote Pool and Builder clients and the chain RPC URL."
  - id: "ev-cli-pool"
    path: "bin/rundler/src/cli/pool.rs"
    kind: "runtime_entrypoint"
    strength: "high"
    reason: "Shows Pool configuration for chain polling, mempool, paymaster, and reputation tracking."
  - id: "ev-cli-builder"
    path: "bin/rundler/src/cli/builder.rs"
    kind: "runtime_entrypoint"
    strength: "high"
    reason: "Shows Builder sender backends, remote Pool dependency, and signing configuration."
  - id: "ev-cli-signer"
    path: "bin/rundler/src/cli/signer.rs"
    kind: "runtime_entrypoint"
    strength: "high"
    reason: "Shows KMS and Redis-backed signer configuration and leasing options."
  - id: "ev-rpc-lib"
    path: "crates/rpc/src/lib.rs"
    kind: "code_path"
    strength: "medium"
    reason: "Defines the RPC namespaces exposed by the Rundler RPC crate."
  - id: "ev-rpc-task"
    path: "crates/rpc/src/task.rs"
    kind: "code_path"
    strength: "high"
    reason: "Wires gas estimators and route-specific dependencies for the RPC runtime."
  - id: "ev-rpc-eth-mod"
    path: "crates/rpc/src/eth/mod.rs"
    kind: "code_path"
    strength: "medium"
    reason: "Defines the eth_ RPC surface including sendUserOperation and estimateUserOperationGas."
  - id: "ev-rpc-eth-server"
    path: "crates/rpc/src/eth/server.rs"
    kind: "code_path"
    strength: "high"
    reason: "Implements eth_ methods and delegates entry point aware handling."
  - id: "ev-rpc-router"
    path: "crates/rpc/src/eth/router.rs"
    kind: "code_path"
    strength: "high"
    reason: "Routes requests by entry point and uses chain-backed estimation paths."
  - id: "ev-rpc-debug"
    path: "crates/rpc/src/debug.rs"
    kind: "code_path"
    strength: "high"
    reason: "Implements debug endpoints that directly manipulate Pool and Builder state."
  - id: "ev-rpc-admin"
    path: "crates/rpc/src/admin.rs"
    kind: "code_path"
    strength: "high"
    reason: "Implements admin endpoints for state clearing and tracking updates."
  - id: "ev-rpc-rundler"
    path: "crates/rpc/src/rundler.rs"
    kind: "code_path"
    strength: "high"
    reason: "Implements Rundler-specific operational APIs and delegation status endpoints."
  - id: "ev-rpc-doc"
    path: "docs/architecture/rpc.md"
    kind: "doc"
    strength: "high"
    reason: "Documents RPC namespaces and their interaction with Pool and Builder."
  - id: "ev-pool-lib"
    path: "crates/pool/src/lib.rs"
    kind: "code_path"
    strength: "medium"
    reason: "Defines Pool task structure and server surfaces."
  - id: "ev-pool-doc"
    path: "docs/architecture/pool.md"
    kind: "doc"
    strength: "high"
    reason: "Documents simulation, reputation, paymaster tracking, and reorg behavior."
  - id: "ev-pool-chain"
    path: "crates/pool/src/chain.rs"
    kind: "code_path"
    strength: "high"
    reason: "Implements chain tracking, block updates, and reorg-driven pool reconciliation."
  - id: "ev-pool-server"
    path: "crates/pool/src/server/mod.rs"
    kind: "code_path"
    strength: "medium"
    reason: "Defines the Pool server boundary and local versus remote surfaces."
  - id: "ev-pool-remote-client"
    path: "crates/pool/src/server/remote/client.rs"
    kind: "code_path"
    strength: "high"
    reason: "Shows remote Pool client behavior for split deployments."
  - id: "ev-pool-uo-pool"
    path: "crates/pool/src/mempool/uo_pool.rs"
    kind: "code_path"
    strength: "high"
    reason: "Implements the in-memory user operation pool and admission logic."
  - id: "ev-pool-reputation"
    path: "crates/pool/src/mempool/reputation.rs"
    kind: "code_path"
    strength: "medium"
    reason: "Implements reputation tracking and entity throttling."
  - id: "ev-pool-paymaster"
    path: "crates/pool/src/mempool/paymaster.rs"
    kind: "code_path"
    strength: "high"
    reason: "Implements paymaster balance tracking used during admission and reconciliation."
  - id: "ev-builder-lib"
    path: "crates/builder/src/lib.rs"
    kind: "code_path"
    strength: "medium"
    reason: "Defines Builder components including assigner, proposer, sender, and server boundaries."
  - id: "ev-builder-doc"
    path: "docs/architecture/builder.md"
    kind: "doc"
    strength: "high"
    reason: "Documents worker assignment, proposer flow, signer management, and sender state machine."
  - id: "ev-builder-assigner"
    path: "crates/builder/src/assigner.rs"
    kind: "code_path"
    strength: "medium"
    reason: "Implements worker assignment and starvation prevention."
  - id: "ev-builder-proposer"
    path: "crates/builder/src/bundle_proposer.rs"
    kind: "code_path"
    strength: "high"
    reason: "Implements bundle construction, filtering, and re-simulation."
  - id: "ev-builder-bundle-sender"
    path: "crates/builder/src/bundle_sender.rs"
    kind: "code_path"
    strength: "high"
    reason: "Implements the bundle sender state machine for submission, retry, and cancellation."
  - id: "ev-builder-flashbots"
    path: "crates/builder/src/sender/flashbots.rs"
    kind: "code_path"
    strength: "high"
    reason: "Implements the private relay sender path for Flashbots."
  - id: "ev-builder-polygon-private"
    path: "crates/builder/src/sender/polygon_private.rs"
    kind: "code_path"
    strength: "medium"
    reason: "Implements an alternate private transaction sender path."
  - id: "ev-builder-proto"
    path: "crates/builder/proto/builder/builder.proto"
    kind: "api_schema"
    strength: "medium"
    reason: "Documents builder APIs and references bundle execution through handleOps."
  - id: "ev-signer-lib"
    path: "crates/signer/src/lib.rs"
    kind: "code_path"
    strength: "high"
    reason: "Implements signer manager composition and Redis-backed KMS locking."
  - id: "ev-signer-aws"
    path: "crates/signer/src/aws.rs"
    kind: "code_path"
    strength: "high"
    reason: "Implements AWS KMS signing and Redis lock manager integration."
  - id: "ev-chain-types"
    path: "crates/types/src/chain.rs"
    kind: "code_path"
    strength: "high"
    reason: "Defines supported entry point addresses and chain capabilities including flashbots flags."
  - id: "ev-remote-compose"
    path: "test/spec-tests/remote/docker-compose.yml"
    kind: "deploy_config"
    strength: "high"
    reason: "Shows a concrete split deployment with separate pool, builder, and RPC services."
unknowns:
  - "The repo documents alternative mempools and future P2P support, but those are not modeled as separate current runtime containers."
  - "The public production gateway, load balancer, and monitoring topology around Rundler are not defined here."
assumptions:
  - text: "The same logical RPC, Pool, and Builder containers remain the correct runtime units in both integrated and split deployment modes."
    confidence: "confirmed"
  - text: "Redis is only relevant when KMS locking is enabled and is therefore modeled as optional external cache infrastructure."
    confidence: "confirmed"
```

### architecture/summary.md

```md
# Architecture Summary

## System Purpose
Rundler is an ERC-4337 bundler backend that accepts user operations over JSON-RPC, validates and stores them in a local mempool, and turns accepted operations into signed bundle transactions on supported EVM chains. The repo is built so the same logical runtime roles can run integrated in one process or split across separate services.

## Repo Archetype
`service_oriented_backend` because the repo defines distinct RPC, Pool, and Builder runtime roles, explicit remote task contracts, and concrete split deployment evidence in the spec-test compose setup.

## Primary Containers or Modules
- `Rundler RPC`: JSON-RPC edge that exposes eth_, debug_, rundler_, and admin APIs and performs chain-backed gas estimation.
- `Rundler Pool`: Stateful mempool owner that validates operations, tracks reorgs, and maintains reputation and paymaster state.
- `Rundler Builder`: Worker-oriented bundle execution service that assigns work, builds bundles, signs transactions, submits them, and tracks outcomes.

## Critical Flows
- `User operation ingest`: RPC receives a user operation, routes it into Pool, and Pool simulates it against the EVM node before admitting it into the live mempool.
- `Bundle construction and submission`: Pool publishes new-block signals, Builder fetches eligible operations, re-simulates them, signs the bundle, submits it, and feeds failures back into Pool.

## Key Decisions
- [DEC-001] Model Rundler as a service-oriented backend instead of a modular monolith because RPC, Pool, and Builder are explicit runtime roles with split deployment support. | covers: rundler-rpc,rundler-pool,rundler-builder,view-container,view-deployment
- [DEC-002] Treat `node` and `backend` as deployment modes, not separate containers, because they collocate existing roles instead of introducing new responsibilities. | covers: rundler-rpc,rundler-pool,rundler-builder,view-deployment
- [DEC-003] Keep Pool as the system of record for user operation lifecycle because its mempool core, reputation manager, and paymaster tracker own the durable in-process decision state. | covers: rundler-pool,pool-mempool,pool-reputation-manager,pool-paymaster-tracker,sequence-user-operation-ingest
- [DEC-004] Model AWS KMS, Redis key leasing, and private relays as optional external dependencies because Builder only uses them through configuration-gated signer and sender paths. | covers: aws-kms,redis-lock-store,private-transaction-relay,rundler-builder-calls-aws-kms,rundler-builder-calls-private-transaction-relay,rundler-builder-calls-redis-lock-store

## Data Ownership Notes
- `user_operation_lifecycle`: Pool is the system of record through the in-memory mempool and its mined-op reconciliation logic.
- `entity_reputation`: Pool Reputation Manager owns throttling and allowlist or blocklist state.
- `paymaster_balance_tracking`: Pool Paymaster Tracker owns pending and confirmed paymaster balance metadata used during admission.
- `bundle_submission_lifecycle`: Builder owns pending bundle state, retries, cancellations, and worker assignment coordination.
- `kms_signer_leases`: Redis is the system of record only when KMS-backed signing with key locking is enabled.

## Major Risks or Unknowns
- The repo does not define a durable database for Pool or Builder state, so the model treats those ownership boundaries as process-local.
- The README entry point support section appears stale relative to current code that also references v0.8 and v0.9 entry point versions.
- The production deployment topology around Rundler outside this repo is not specified.

## Recommended Next Reads
- `README.md`: product framing, modularity goals, and runtime modes
- `docs/architecture/README.md`: top-level RPC, Pool, and Builder overview
- `docs/architecture/rpc.md`: API surface and control paths
- `docs/architecture/pool.md`: validation, chain tracking, and state ownership
- `docs/architecture/builder.md`: assigner, proposer, signer, sender, and state machine behavior
- `test/spec-tests/remote/docker-compose.yml`: concrete split deployment topology

## Artifact Index
- `architecture/model.yaml`: canonical architecture model
- `architecture/views/system-context.yaml`: system context view
- `architecture/views/container.yaml`: container view
- `architecture/views/component-rundler-rpc.yaml`: RPC component view
- `architecture/views/component-rundler-pool.yaml`: Pool component view
- `architecture/views/component-rundler-builder.yaml`: Builder component view
- `architecture/views/sequence-user-operation-ingest.yaml`: user operation ingest sequence
- `architecture/views/sequence-bundle-construction-and-submission.yaml`: bundle construction and submission sequence
- `architecture/views/deployment.yaml`: deployment view
```

### architecture/views/system-context.yaml

```yaml
version: 2
id: "system-context"
type: "system_context"
title: "Rundler System Context"
audience:
  - "new_hires"
  - "pms"
  - "senior_architects"
purpose: "Show who interacts with Rundler and which external systems materially affect current runtime behavior."
scope: "System-of-interest plus direct actors and external dependencies"
source_model: "architecture/model.yaml"
element_ids:
  - "dapp-user"
  - "bundler-operator"
  - "rundler"
  - "evm-json-rpc-node"
  - "entrypoint-contract"
  - "private-transaction-relay"
  - "aws-kms"
relationship_ids:
  - "dapp-user-calls-rundler"
  - "bundler-operator-calls-rundler"
  - "rundler-calls-evm-json-rpc-node"
  - "rundler-submits-bundles-to-entrypoint-contract"
  - "rundler-calls-private-transaction-relay"
  - "rundler-calls-aws-kms"
assumptions:
  - text: "Redis is omitted from system context because it only appears in KMS key leasing mode and is clearer in the container and deployment views."
    confidence: "strong_inference"
unknowns:
  - "The public gateway or load balancer in front of Rundler RPC is not defined in the repo."
notes:
  - "Rundler keeps the same logical system boundary whether tasks run in one process or as separate services."
```

### architecture/views/container.yaml

```yaml
version: 2
id: "container"
type: "container"
title: "Rundler Container View"
audience:
  - "new_hires"
  - "pms"
  - "senior_architects"
purpose: "Show Rundler's primary runtime roles, the state ownership boundary, and optional runtime integrations."
scope: "RPC, Pool, Builder, directly relevant actors, and material external systems"
source_model: "architecture/model.yaml"
element_ids:
  - "dapp-user"
  - "bundler-operator"
  - "rundler"
  - "rundler-rpc"
  - "rundler-pool"
  - "rundler-builder"
  - "evm-json-rpc-node"
  - "entrypoint-contract"
  - "private-transaction-relay"
  - "aws-kms"
  - "redis-lock-store"
relationship_ids:
  - "dapp-user-calls-rundler-rpc"
  - "bundler-operator-calls-rundler-rpc"
  - "rundler-rpc-calls-rundler-pool"
  - "rundler-rpc-calls-rundler-builder"
  - "rundler-rpc-calls-evm-json-rpc-node"
  - "rundler-pool-calls-evm-json-rpc-node"
  - "rundler-builder-calls-rundler-pool"
  - "rundler-pool-publishes-to-rundler-builder"
  - "rundler-builder-calls-evm-json-rpc-node"
  - "rundler-builder-submits-bundles-to-entrypoint-contract"
  - "rundler-builder-calls-private-transaction-relay"
  - "rundler-builder-calls-aws-kms"
  - "rundler-builder-calls-redis-lock-store"
assumptions:
  - text: "The container view models RPC, Pool, and Builder as the stable runtime roles even when `node` or `backend` collocate them."
    confidence: "confirmed"
unknowns:
  - "The repo does not define a durable database for pool or builder state beyond optional Redis key leasing."
notes:
  - "RPC to Pool and Builder uses local handles in integrated mode and gRPC in distributed mode."
  - "RPC is not modeled as a thin proxy because current code paths also perform chain-backed gas estimation."
```

### architecture/views/component-rundler-rpc.yaml

```yaml
version: 2
id: "component-rundler-rpc"
type: "component"
title: "Rundler RPC Components"
audience:
  - "new_hires"
  - "senior_architects"
purpose: "Show how the RPC task splits user-facing, debug, and entry point routing responsibilities."
scope: "Internal modules inside Rundler RPC plus direct dependencies needed for context"
source_model: "architecture/model.yaml"
parent_container_id: "rundler-rpc"
element_ids:
  - "rpc-eth-api"
  - "rpc-rundler-api"
  - "rpc-debug-admin-api"
  - "rpc-entrypoint-router"
  - "rundler-pool"
  - "rundler-builder"
  - "evm-json-rpc-node"
relationship_ids:
  - "rpc-eth-api-calls-rpc-entrypoint-router"
  - "rpc-rundler-api-calls-rpc-entrypoint-router"
  - "rpc-entrypoint-router-calls-rundler-pool"
  - "rpc-eth-api-calls-evm-json-rpc-node"
  - "rpc-debug-admin-api-calls-rundler-builder"
  - "rpc-debug-admin-api-calls-rundler-pool"
assumptions:
  - text: "The router is the clearest place to represent entry point version dispatch and shared gas estimator wiring."
    confidence: "confirmed"
unknowns:
  - "The exact internal split between receipt/event reads and status-oriented Rundler APIs may evolve as RPC surface area grows."
notes:
  - "The debug and admin component is combined here because both modules drive operational state mutation paths into Pool and Builder."
```

### architecture/views/component-rundler-pool.yaml

```yaml
version: 2
id: "component-rundler-pool"
type: "component"
title: "Rundler Pool Components"
audience:
  - "new_hires"
  - "senior_architects"
purpose: "Show where Pool owns user operation lifecycle state and how chain tracking updates that state."
scope: "Internal modules inside Rundler Pool plus direct dependencies needed for context"
source_model: "architecture/model.yaml"
parent_container_id: "rundler-pool"
element_ids:
  - "pool-server"
  - "pool-chain-tracker"
  - "pool-mempool"
  - "pool-reputation-manager"
  - "pool-paymaster-tracker"
  - "evm-json-rpc-node"
relationship_ids:
  - "pool-server-calls-pool-mempool"
  - "pool-mempool-calls-pool-reputation-manager"
  - "pool-mempool-calls-pool-paymaster-tracker"
  - "pool-chain-tracker-calls-evm-json-rpc-node"
  - "pool-chain-tracker-updates-pool-mempool"
assumptions:
  - text: "Simulation logic is cross-cutting across RPC, Pool, and Builder, but Pool is the strongest ownership boundary for the persisted user operation lifecycle state."
    confidence: "strong_inference"
unknowns:
  - "The repo does not define a durable backing store for the mempool, reputation, or paymaster state."
notes:
  - "Pool server may be local or remote, but the mempool state it fronts remains the same logical ownership boundary."
```

### architecture/views/component-rundler-builder.yaml

```yaml
version: 2
id: "component-rundler-builder"
type: "component"
title: "Rundler Builder Components"
audience:
  - "new_hires"
  - "senior_architects"
purpose: "Show how Builder assigns work, proposes bundles, signs them, and submits them through pluggable senders."
scope: "Internal modules inside Rundler Builder plus direct dependencies needed for context"
source_model: "architecture/model.yaml"
parent_container_id: "rundler-builder"
element_ids:
  - "builder-assigner"
  - "builder-bundle-proposer"
  - "builder-bundle-sender-workers"
  - "builder-transaction-sender"
  - "builder-signer-manager"
  - "rundler-pool"
  - "evm-json-rpc-node"
  - "private-transaction-relay"
relationship_ids:
  - "builder-bundle-sender-workers-calls-builder-assigner"
  - "builder-assigner-calls-rundler-pool"
  - "builder-bundle-sender-workers-calls-builder-bundle-proposer"
  - "builder-bundle-proposer-calls-rundler-pool"
  - "builder-bundle-proposer-calls-evm-json-rpc-node"
  - "builder-bundle-sender-workers-calls-builder-signer-manager"
  - "builder-bundle-sender-workers-calls-builder-transaction-sender"
  - "builder-transaction-sender-calls-evm-json-rpc-node"
  - "builder-transaction-sender-calls-private-transaction-relay"
assumptions:
  - text: "The shared signer pool is best modeled inside Builder because worker count and signer selection are builder-owned configuration decisions."
    confidence: "confirmed"
unknowns:
  - "Which sender backend is dominant in production is configuration dependent and not fixed by the repo."
notes:
  - "Redis and AWS KMS are omitted here to keep the component view focused on Builder flow; they remain visible at container level."
```

### architecture/views/deployment.yaml

```yaml
version: 2
id: "deployment"
type: "deployment"
title: "Rundler Distributed Deployment"
audience:
  - "new_hires"
  - "senior_architects"
purpose: "Show the split-process deployment shape that makes RPC, Pool, and Builder runtime boundaries explicit."
scope: "Distributed mode using separate RPC, Pool, and Builder hosts"
source_model: "architecture/model.yaml"
element_ids:
  - "rundler-rpc"
  - "rundler-pool"
  - "rundler-builder"
  - "redis-lock-store"
relationship_ids:
  - "rundler-rpc-calls-rundler-pool"
  - "rundler-rpc-calls-rundler-builder"
  - "rundler-builder-calls-rundler-pool"
  - "rundler-pool-publishes-to-rundler-builder"
  - "rundler-builder-calls-redis-lock-store"
deployment_node_ids:
  - "deployment-rpc-host"
  - "deployment-pool-host"
  - "deployment-builder-host"
  - "deployment-redis-service"
placement:
  - node_id: "deployment-rpc-host"
    element_id: "rundler-rpc"
  - node_id: "deployment-pool-host"
    element_id: "rundler-pool"
  - node_id: "deployment-builder-host"
    element_id: "rundler-builder"
  - node_id: "deployment-redis-service"
    element_id: "redis-lock-store"
assumptions:
  - text: "This view is grounded in the remote spec-test compose because it is the clearest concrete split deployment in the repo."
    confidence: "confirmed"
unknowns:
  - "The repo does not specify whether Redis is colocated with Builder or provided as managed infrastructure in production."
notes:
  - "Integrated `node` mode removes the remote boundaries by colocating RPC, Pool, and Builder in a single process."
  - "`backend` mode collocates Pool and Builder while keeping their gRPC APIs exposed to a separate RPC process."
```

View the architecture diagram here: /Users/will/.codex/worktrees/bccc/architect/evals/architect-discover/round7_rundler/diagram.html
