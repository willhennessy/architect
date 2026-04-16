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
