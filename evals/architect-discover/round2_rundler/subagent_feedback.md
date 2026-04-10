# Subagent Feedback

Reviewer: fresh subagent review on `2026-03-28`

## Major Findings

### 1. Fixed: ingest sequence return edge was modeled in the wrong direction

The reviewer correctly flagged that the final step in `sequence-user-operation-ingest.yaml` reused the forward `rpc-eth-api -> pool-api` relationship for the response path. The pool protobuf shows `AddOp` returning `AddOpResponse.success.hash`, so the response belongs on the Pool-to-RPC path.

What I changed:

- Updated the final sequence step to use `pool-api -> rpc-eth-api`
- Removed the incorrect reused `relationship_id`
- Raised confidence from `strong_inference` to `confirmed`

Evidence checked:

- `evals/repos/rundler/crates/pool/proto/op_pool/op_pool.proto`

### 2. Fixed: private relay submission belonged on sender adapters, not the tracker itself

The reviewer also correctly flagged that the model over-attributed private relay submission to `builder-transaction-tracker`. The tracker owns lifecycle state and delegates send/cancel behavior into the `TransactionSender` abstraction; the adapter layer owns the actual transport-specific submission behavior.

What I changed:

- Added `builder-transaction-senders` as a Builder component
- Added `builder-transaction-tracker -> builder-transaction-senders`
- Moved private relay submission to `builder-transaction-senders -> private-transaction-relay`
- Added `builder-transaction-senders -> evm-json-rpc-node` for raw and conditional submission
- Narrowed `builder-transaction-tracker -> evm-json-rpc-node` to state polling and receipt/nonce/balance tracking
- Updated the Builder component view notes and assumption to reflect the split between lifecycle tracking and transport

Evidence checked:

- `evals/repos/rundler/crates/builder/src/sender/mod.rs`
- `evals/repos/rundler/crates/builder/src/sender/raw.rs`
- `evals/repos/rundler/crates/builder/src/sender/flashbots.rs`
- `evals/repos/rundler/crates/builder/src/sender/bloxroute.rs`
- `evals/repos/rundler/crates/builder/src/sender/polygon_private.rs`
- `evals/repos/rundler/crates/builder/src/transaction_tracker.rs`

## Strong Areas

- The RPC / Pool / Builder runtime split matched the repo well, including the distinction between integrated `node`, partially collocated `backend`, and split-process deployments.
- The updated model now correctly reflects entry point support through v0.9 and the repo’s v0.6 versus v0.7+ ABI handling.
- Data ownership remains clear: Pool owns pending user operations and local policy state, while Builder owns worker assignment and bundle lifecycle state.

## Recommended Changes

- Keep a required consistency pass between sequence steps and canonical relationship direction so reply edges do not accidentally borrow forward call relationships.
- Add a discovery prompt to look for transport abstractions under trackers/executors before assigning external submission relationships.
- Treat namespace-gated RPC control paths as conditional capability in notes unless runtime configuration proves they are always on.

## Unresolved Disagreements Or Unknowns

- No substantive disagreements with the reviewer after re-checking the cited code.
- Production deployment topology beyond the in-repo spec-test compose remains unknown.
- Debug and admin Builder control paths are modeled as supported paths, but their activation is configuration-gated by enabled namespaces.
