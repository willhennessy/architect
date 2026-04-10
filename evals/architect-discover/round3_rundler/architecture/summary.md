# Architecture Summary

## System Purpose

Rundler is a high-performance ERC-4337 bundler written in Rust, built and operated by Alchemy. It accepts user operations from DApps/wallets via JSON-RPC, validates and pools them in an in-memory mempool, constructs profitable bundles, and submits them as transactions to EVM-compatible blockchains via the EntryPoint smart contract.

## Repo Archetype

**Modular monolith.** A single Rust workspace produces one binary (`rundler`) with multiple CLI subcommands that can run all tasks in one process (`node` mode) or split them into separate processes communicating via gRPC (`rpc`, `pool`, `builder`, `backend` modes). The crate structure mirrors the runtime task boundaries.

## Primary Containers or Modules

- **RPC Server** (`crates/rpc/`): JSON-RPC API implementing eth\_, debug\_, rundler\_, and admin\_ namespaces. Performs gas estimation via simulation against the EVM node. Horizontally scalable in distributed mode.
- **Pool / Mempool** (`crates/pool/`): Validates and stores pending user operations. Tracks chain state, handles reorgs, manages entity reputation. Stateful.
- **Builder** (`crates/builder/`): Constructs bundles from pooled UOs, signs and submits transactions, tracks mining status. Runs a state machine (Building -> Pending -> Cancelling -> CancelPending) per worker. Stateful.
- **Simulation Engine** (`crates/sim/`): Prechecks and simulates user operations via debug\_traceCall per ERC-4337 rules. Used by Pool during admission and Builder during 2nd simulation.
- **Signer Manager** (`crates/signer/`): Manages transaction signing keys. Supports local private key, BIP-39 mnemonic, and AWS KMS with Redis-based key leasing for distributed setups.
- **Provider** (`crates/provider/`): Abstraction layer over EVM JSON-RPC nodes using the alloy library. Handles fee estimation, DA gas oracles, and EntryPoint contract interactions.

## Critical Flows

- **User Operation Submission** (`eth_sendUserOperation`): DApp -> RPC -> Pool (precheck + simulate via EVM node) -> accept or reject. This is the primary ingress path.
- **Gas Estimation** (`eth_estimateUserOperationGas`): DApp -> RPC -> Simulation Engine (binary search via debug\_traceCall against EVM node) -> return gas estimates. RPC calls the sim crate directly, bypassing the Pool.
- **Bundle Building and Submission**: Pool emits block event -> Builder worker requests assignment -> fetches UOs -> re-simulates -> constructs bundle -> signs -> submits transaction -> tracks until mined. This is the core value-creation loop that gets UOs on-chain.

## Data Ownership Notes

- **User Operation Mempool**: Owned by the Pool task. In-memory, non-persistent.
- **Entity Reputation**: Owned by the Pool task. Tracks per ERC-4337 spec.
- **Mined UO Cache**: Owned by the Pool task. Used for reorg handling up to configurable depth.
- **Pending Bundle State**: Owned by Builder task per-worker. Tracks in-flight transactions.
- **Blockchain State**: External, owned by the EVM full node.
- **Signing Keys**: External, owned by AWS KMS (production) or local config (development).

## Major Risks or Unknowns

- P2P mempool protocol is referenced as future work but not yet implemented. This means Rundler currently operates as a standalone bundler without mempool sharing.
- The `aws-sdk-s3` dependency in the binary crate is used for loading JSON config files from S3 buckets (see `bin/rundler/src/cli/json.rs`).
- Exact production deployment topology at Alchemy is not documented in the open-source repo.
- Redis is a hard dependency only when using AWS KMS signing with multiple workers; this coupling is not immediately obvious from the top-level architecture.

## Recommended Next Reads

- `docs/architecture/README.md`: Official architecture overview with task communication patterns.
- `docs/architecture/builder.md`: Detailed builder state machine, signer sharing, transaction sender plugins.
- `docs/architecture/pool.md`: Mempool simulation, reputation, chain tracking.
- `bin/rundler/src/cli/mod.rs`: CLI entrypoint showing all deployment modes and configuration.
- `bin/rundler/src/cli/node/mod.rs`: How all three tasks are wired together in monolithic mode.

## Artifact Index

- `architecture/model.yaml`: Canonical architecture model with all elements, relationships, and evidence.
- `architecture/views/system-context.yaml`: External actors and systems.
- `architecture/views/container.yaml`: Core tasks and communication patterns.
- `architecture/views/component-pool.yaml`: Pool task internal components.
- `architecture/views/component-builder.yaml`: Builder task internal components.
- `architecture/views/sequence-submit-userop.yaml`: UO submission flow.
- `architecture/views/sequence-bundle-building.yaml`: Bundle building and submission flow.
- `architecture/views/sequence-gas-estimation.yaml`: Gas estimation flow from RPC through simulation to EVM node.
- `architecture/views/deployment.yaml`: Docker deployment topology and modes.
- `architecture/manifest.yaml`: Artifact index and metadata.
