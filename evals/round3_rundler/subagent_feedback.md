# Architecture Model Review: Rundler (Round 3)

## Overall Assessment

The model is a solid representation of Rundler's architecture. The core three-task structure (RPC, Pool, Builder) is correctly identified, C4 levels are mostly clean, and the major external systems are captured. Evidence linking is strong throughout. However, there are several meaningful gaps and inaccuracies that would mislead a new reader or architect.

Findings are ordered by severity.

---

## 1. Semantic Correctness

### SEVERITY: HIGH -- RPC has a direct dependency on Simulation Engine and EVM Node for gas estimation

The model claims RPC is stateless and only interacts with Pool and Builder. This is wrong. The RPC crate (`crates/rpc/Cargo.toml`) directly depends on `rundler-sim` and uses `GasEstimator` for `eth_estimateUserOperationGas`. The gas estimation flow goes RPC -> Simulation Engine -> EVM Node, bypassing Pool entirely.

**Evidence**: `crates/rpc/src/eth/router.rs` imports `rundler_sim::GasEstimator` (line 25). `crates/rpc/src/eth/api.rs` delegates to `self.router.estimate_gas(...)` (line 126-128), which calls the sim crate's gas estimator directly against the EVM node.

**Impact**: The model is missing a `rel-rpc-sim` relationship and a `rel-rpc-evm` relationship. The RPC container is NOT stateless in the way the summary claims -- it directly interacts with the EVM node for simulation. This is architecturally significant because it means RPC scaling requires EVM node capacity, not just Pool capacity.

### SEVERITY: HIGH -- EntryPoint contract versions are wrong

The model's `entrypoint-contract` element says "v0.6 and v0.7". The actual codebase supports v0.6, v0.7, v0.8, and v0.9. The `docs/architecture/entry_point.md` explicitly lists all four versions. The `crates/contracts/src/` directory contains `v0_6.rs`, `v0_7.rs`, `v0_8.rs`, and `v0_9.rs`.

**Evidence**: `docs/architecture/entry_point.md` lines 6-8, `crates/contracts/src/` directory listing.

**Impact**: Misleading for anyone trying to understand supported protocol versions. The evidence `ev-entrypoint-doc` is cited but appears to have been incompletely read.

### SEVERITY: MEDIUM -- Signature aggregation subsystem completely missing

The codebase has a substantial signature aggregation system (`crates/aggregators/bls/`, `crates/aggregators/pbh/`) with dedicated documentation (`docs/architecture/aggregators.md`). This is a first-class feature involving:
- A `SignatureAggregator` trait registered on `ChainSpec`
- BLS and PBH (World Chain Priority Blockspace for Humans) implementations
- Integration into Pool (signature validation on admission) and Builder (`handleAggregatedOps`)
- CLI flags for aggregator configuration (`bin/rundler/src/cli/aggregator.rs`)

**Evidence**: `docs/architecture/aggregators.md`, `crates/aggregators/bls/`, `crates/aggregators/pbh/`, `bin/rundler/src/cli/aggregator.rs`.

**Impact**: A significant architectural feature is completely unrepresented. Aggregation changes the bundle submission path (using `handleAggregatedOps` instead of `handleOps`) and adds offchain computation requirements.

### SEVERITY: MEDIUM -- Submission Proxy system missing

The codebase includes a `SubmissionProxy` trait (`crates/types/src/proxy.rs`) and implementations in `bin/rundler/src/cli/proxy.rs` (PassThrough, PBH). The Builder uses submission proxies to alter how bundles are submitted on-chain.

**Evidence**: `bin/rundler/src/cli/proxy.rs`, `crates/builder/src/bundle_proposer.rs` and `crates/builder/src/task.rs` both reference `SubmissionProxy`.

### SEVERITY: MEDIUM -- Transaction Tracker component missing from Builder

The Builder has a `TransactionTracker` (`crates/builder/src/transaction_tracker.rs`) that is distinct from the Bundle Sender. It manages pending transaction nonces, replacement fees, and detects mined/dropped transactions. The model collapses this into `builder-sender` but it is a separate concern with its own trait and mock.

**Evidence**: `crates/builder/src/transaction_tracker.rs` -- defines `TransactionTracker` trait, `TrackerState`, `TrackerUpdate` types. The `BundleSenderImpl` holds an `Option<T>` where `T: TransactionTracker`.

---

## 2. Abstraction Discipline

### SEVERITY: MEDIUM -- Signer Manager misplaced as a Builder component

The model places `builder-signer` (Signer Manager) as a component inside `builder-task` with `parent_id: "builder-task"`. However, `crates/signer/` is an independent workspace crate at the same level as `crates/pool/`, `crates/builder/`, etc. It is consumed by the Builder but is not architecturally inside it. The Admin CLI also directly uses the signer (`bin/rundler/src/cli/admin/` has fund-signers, defund-signers, list-signers commands).

While the Builder is the primary runtime consumer, the signer is better modeled as a shared infrastructure component or a separate container-level element, not a Builder-internal component.

### SEVERITY: MEDIUM -- Simulation Engine misplaced as Pool-only component

The model places `pool-simulation` as a component inside `pool-task`. But the `sim` crate (`crates/sim/`) is an independent workspace crate used by BOTH the Pool (for admission validation) and the RPC task (for gas estimation) and the Builder (for re-simulation). Placing it exclusively under Pool misrepresents its role.

**Evidence**: `crates/rpc/Cargo.toml` line 28: `rundler-sim.workspace = true`. `crates/builder/Cargo.toml` line 31: `rundler-sim.workspace = true`.

### SEVERITY: LOW -- Provider crate not represented

The `crates/provider/` crate is a significant abstraction layer (mentioned in the summary as "Provider") but has no element in the model. It wraps alloy, implements fee estimation, DA gas oracles, and EntryPoint contract interactions. It is used by nearly every other crate. While it could be argued this is a utility/library, it has more architectural significance than the Reputation Manager which IS modeled.

### SEVERITY: LOW -- Several crates omitted without explanation

The following crates exist but are not modeled or mentioned: `crates/types/`, `crates/task/`, `crates/utils/`, `crates/bindings/`. While these are arguably infrastructure/utility crates, `crates/task/` provides the gRPC and server abstractions used by both Pool and Builder servers, and `crates/types/` defines all the core domain types. At minimum they deserve mention in the summary or unknowns.

---

## 3. Data Ownership Modeling

### SEVERITY: MEDIUM -- Paymaster balance tracking not modeled

The Pool has a substantial `PaymasterTracker` subsystem (`crates/pool/src/mempool/paymaster.rs`) that tracks pending and confirmed paymaster deposit balances. This is state that the Pool owns and manages, distinct from the mempool and reputation data. It is not mentioned in `owned_data` for `pool-task`.

### SEVERITY: LOW -- Signer funding/balance state not modeled

The Signer Manager tracks signer balances and handles auto-funding via multicall3 (`crates/signer/src/funding.rs`). This is owned state (signer balances, funding thresholds) not captured in the model. The `KmsFunding` signing scheme is a distinct operational concern.

### SEVERITY: LOW -- "mined_uo_cache" correctly listed but confidence should be higher

The `mined_uo_cache` in `owned_data` for `pool-task` is accurate -- the chain tracker in `crates/pool/src/chain.rs` maintains this for reorg handling. Good catch.

---

## 4. Critical Workflow Coverage

### SEVERITY: HIGH -- Gas estimation flow missing

`eth_estimateUserOperationGas` is one of the most called RPC methods. The sequence views only cover `eth_sendUserOperation` and bundle building. The gas estimation flow (RPC -> Sim/GasEstimator -> EVM Node) is architecturally distinct from UO submission and deserves its own sequence view.

### SEVERITY: MEDIUM -- Chain reorg handling flow missing

The model mentions reorg handling in descriptions but no sequence view captures it. The chain tracker (`crates/pool/src/chain.rs`) detects reorgs, the pool removes mined ops that were reorged out, and re-validates them. This is a critical correctness flow.

### SEVERITY: MEDIUM -- Aggregated bundle submission flow missing

When signature aggregation is used, the bundle submission path differs: the Builder calls `handleAggregatedOps` instead of `handleOps`, and must perform offchain signature aggregation. This is a distinct critical flow not represented.

### SEVERITY: LOW -- Admin CLI operations not covered

The admin subcommand (fund-signers, defund-signers, list-signers) represents operational workflows. While not runtime-critical, they are important for operations.

---

## 5. Unsupported Claims

### SEVERITY: MEDIUM -- "Bloxroute" sender claim is imprecise

The model's `builder-tx-sender` description says it supports "Flashbots, and Bloxroute." The actual implementation in `crates/builder/src/sender/bloxroute.rs` is specifically `PolygonBloxrouteTransactionSender` -- it is Polygon-specific, not a general Bloxroute sender. There is also a `polygon_private.rs` sender that the model doesn't mention.

**Evidence**: `crates/builder/src/sender/bloxroute.rs` line 30: `pub(crate) struct PolygonBloxrouteTransactionSender<P>`.

### SEVERITY: LOW -- S3 dependency resolved (not truly unknown)

The unknowns list says "S3 dependency in bin/rundler Cargo.toml (aws-sdk-s3) - purpose unclear, possibly config loading." The purpose is clear from `bin/rundler/src/cli/json.rs`: it loads JSON config files from S3 buckets when the path starts with `s3://`. This should be documented as resolved, not unknown.

### SEVERITY: LOW -- "entity_reputation" as system_of_record for pool-task is debatable

The model lists `entity_reputation` in `system_of_record` implicitly via `user_operation_lifecycle`. Entity reputation is ephemeral, in-memory state that resets on restart. Calling the Pool the system of record for UO lifecycle is technically true during runtime, but the blockchain is the ultimate system of record for whether a UO was executed.

---

## 6. Missing or Misleading Relationships

### SEVERITY: HIGH -- RPC -> EVM Node relationship missing

As detailed in finding 1.1, RPC directly calls the EVM node for gas estimation via the sim crate. No relationship captures this.

### SEVERITY: MEDIUM -- Builder -> Simulation Engine relationship missing

The Builder re-simulates UOs during bundle construction (`crates/builder/Cargo.toml` depends on `rundler-sim`). The model captures this narratively in the bundle building sequence ("Re-simulate candidate UOs") but there is no structural relationship between the Builder and the Simulation Engine component. Since the sim engine is incorrectly placed as a Pool-only component, this cross-container dependency is invisible.

### SEVERITY: MEDIUM -- Pool -> Builder block subscription direction may be misleading

The model says `rel-builder-pool` is bidirectional with "Subscribes to block updates, fetches UOs for bundling, reports failed UOs." The `docs/architecture/README.md` says "The Builder subscribes to a stream of updates from the Pool." This is actually Pool pushing to Builder (pub/sub pattern), not Builder polling Pool. The relationship direction and interaction_type should reflect this.

### SEVERITY: LOW -- Redis protocol listed as "https"

`rel-signer-redis` lists protocol as "https". Redis uses its own protocol (RESP), typically over TCP. The `rslock` crate in `crates/signer/src/aws.rs` connects via Redis URI (line 128: `LockManager::new(vec![redis_url])`).

### SEVERITY: LOW -- `rel-builder-entrypoint` is indirect

The model shows Builder calling the EntryPoint contract directly. In reality, the Builder submits transactions to the EVM node which then execute against the EntryPoint contract. The Builder doesn't have a direct network connection to the EntryPoint -- it constructs calldata targeting the EntryPoint address and submits it via the EVM node's `eth_sendRawTransaction`. The current modeling makes it look like a separate network call.

---

## Summary of Findings by Severity

| Severity | Count | Key Issues |
|----------|-------|------------|
| HIGH | 4 | RPC->EVM gas estimation missing, EntryPoint versions wrong, aggregation subsystem missing, gas estimation sequence missing |
| MEDIUM | 9 | Submission proxy missing, transaction tracker missing, signer/sim misplaced, paymaster tracking unmodeled, reorg flow missing, Builder->Sim missing, block subscription direction, Bloxroute imprecise |
| LOW | 7 | Provider crate unmodeled, utility crates omitted, signer funding unmodeled, S3 resolved, Redis protocol wrong, EntryPoint relationship indirect, admin CLI uncovered |

---

## Evaluator Response to Findings

### Applied
- **EntryPoint versions** (HIGH): Fixed to v0.6-v0.9. Verified against `crates/contracts/src/`.
- **RPC -> EVM gas estimation** (HIGH): Added `rel-rpc-evm` relationship, updated RPC description, added evidence. Verified via `crates/rpc/Cargo.toml` dependency on `rundler-sim`.
- **Gas estimation sequence** (HIGH): Created `sequence-gas-estimation.yaml`.
- **Bloxroute description** (MEDIUM): Fixed to specify Polygon Bloxroute and Polygon private submission.
- **Paymaster balance tracking** (MEDIUM): Added `paymaster_balances` to pool-task owned_data.
- **Simulation shared usage** (MEDIUM): Updated pool-simulation description to note usage by RPC and Builder.
- **Redis protocol** (LOW): Fixed from "https" to blank.
- **S3 unknown resolved** (LOW): Removed from unknowns, noted as resolved.

### Not Applied (Disagreements)
- **Aggregation subsystem** (MEDIUM — downgraded from HIGH): Valid gap, but aggregation is a plugin/extension mechanism, not a core architectural boundary. The model correctly represents the core runtime architecture. Adding aggregators would require parallel modeling of all plugin mechanisms. Noted as a known gap but not added as model elements.
- **Signer misplaced as Builder component** (MEDIUM): The signer crate is independent, but at runtime it is exclusively consumed by Builder workers. Admin CLI fund-signers is an operational tool, not a runtime consumer. Keeping signer under Builder is a reasonable C4 abstraction.
- **Transaction Tracker as separate component** (MEDIUM): The tracker is tightly coupled to the Bundle Sender state machine. Modeling it separately would fragment a single workflow. The current abstraction (sender manages transaction lifecycle) is coherent.
- **Submission proxy** (MEDIUM): Plugin mechanism, not core architecture. Same reasoning as aggregators.
- **Provider crate** (LOW): Utility/library crate used everywhere. Not an architectural element — it's infrastructure plumbing.
- **Chain reorg sequence** (MEDIUM): Valid addition but lower priority. The chain tracker and reorg handling are described in element descriptions.
- **Builder -> EntryPoint indirectness** (LOW): All smart contract interactions are mediated by the EVM node. Modeling this as Builder -> EntryPoint is a standard C4 simplification. Adding the indirection would clutter every contract interaction.
