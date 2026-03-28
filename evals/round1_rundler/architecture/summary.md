# Architecture Summary

## System Purpose
Rundler is an ERC-4337 bundler backend that accepts user operations over JSON-RPC, validates and stores them in a local mempool, and turns them into signed bundle transactions on supported EVM chains. The codebase is designed so the same runtime roles can either run together in one process or be split into independently scalable services.

## Repo Archetype
`service_oriented_backend` because the repo defines multiple concrete runtime roles (`rpc`, `pool`, `builder`, plus collocated `node` and `backend` modes), explicit remote contracts over gRPC, and a deployment example that runs those roles as separate services.

## Primary Containers or Modules
- `Rundler RPC`: JSON-RPC edge that exposes ERC-4337, Rundler-specific, debug, and admin APIs.
- `Rundler Pool`: Stateful mempool owner that validates user operations, tracks reorgs, and maintains local reputation and paymaster caches.
- `Rundler Builder`: Worker-oriented bundle execution service that assigns work, builds bundles, signs them, submits them, and tracks transaction outcomes.

## Critical Flows
- `User operation ingest`: RPC routes the request by entry point version, Pool simulates it against the chain, and accepted operations enter the per-entry-point mempool.
- `Bundle construction and submission`: Pool publishes new-head triggers, Builder assigns a worker, proposes and re-simulates a bundle, signs it, submits it, and feeds invalidation and pending-bundle updates back into Pool.

## Data Ownership Notes
- `Pending user operations`: Owned and system-of-record inside Pool's per-entry-point mempools.
- `Entity reputation state`: Owned and system-of-record inside Pool's reputation manager.
- `Paymaster balance cache`: Owned and system-of-record inside Pool's paymaster tracker.
- `Worker assignments and pending bundle transaction state`: Owned inside Builder.
- `KMS key lease locks`: Owned by Redis only when AWS KMS locking is enabled.

## Major Risks or Unknowns
- Pool and Builder state are modeled as process-local because the repo does not define a durable database for them.
- The exact production deployment topology outside the repo is unknown; the distributed docker compose is the strongest concrete deployment evidence here.
- P2P or alternative mempool support is discussed in docs and roadmap material but is not part of the current primary runtime architecture.

## Recommended Next Reads
- `README.md`: repo-level goals, runtime modes, and chain support
- `docs/architecture/README.md`: top-level explanation of RPC, Pool, and Builder coordination
- `docs/architecture/pool.md`: state ownership, reorg handling, and mempool behavior
- `docs/architecture/builder.md`: worker, proposer, assigner, signer, and sender behavior
- `docs/architecture/rpc.md`: RPC namespaces and cross-service control paths
- `test/spec-tests/remote/docker-compose.yml`: concrete distributed deployment example

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
