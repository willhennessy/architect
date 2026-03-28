# Reflections — Round 3 (Rundler)

## 1. What would I have done differently?

**Explored RPC dependencies earlier.** The biggest miss — RPC's direct dependency on the sim crate for gas estimation — would have been caught if discovery pass 1 had included checking `Cargo.toml` dependencies for each core task crate, not just entrypoints and deployment files. I relied too heavily on architectural docs (`docs/architecture/rpc.md`) which describe RPC as a thin routing layer, when the code tells a different story. The evidence hierarchy says runtime > docs, and I violated that for the RPC container.

**Checked contract version files directly.** The EntryPoint version error (v0.6/v0.7 vs v0.6-v0.9) came from trusting `docs/architecture/entry_point.md` without cross-checking the actual contract bindings in `crates/contracts/src/`. A 30-second `ls` would have caught this. When the model claims version support, the source of truth is the code, not docs.

**Been more systematic about shared crate usage.** The simulation engine being used by RPC, Pool, AND Builder is architecturally significant. The discovery workflow should explicitly ask: "which crates are depended on by multiple task crates?" This cross-cutting dependency analysis would have surfaced the sim crate's shared nature and led to better modeling from the start.

**Scoped the model boundary more explicitly.** I didn't decide upfront whether plugin/extension mechanisms (aggregators, submission proxies) were in-scope. This led to them being silently omitted rather than explicitly excluded. The modeling ledger should have a `plugin_mechanisms` field to force this decision.

## 2. What improvements should we make to generate-architecture?

### A. Add a cross-cutting dependency analysis step

After identifying the core runtime units (step 6), add a step that checks which internal crates/modules are consumed by multiple runtime units. For Rust, this means checking `Cargo.toml` dependencies across task crates. For other ecosystems, check import graphs across service boundaries. This catches shared infrastructure that crosses container boundaries.

**Where to add:** Between steps 6 and 7 (after identifying canonical elements, before identifying relationships).

### B. Mandate code-level verification of version/capability claims

When the model claims specific version support, protocol compatibility, or feature coverage, the skill should require verification against code — not just docs. Add to the evidence hierarchy section: "Version and capability claims must be verified against code artifacts (contract files, feature flags, protocol definitions), not documentation alone."

### C. Add `plugin_mechanisms` to the modeling ledger

The ledger should include a field for identified plugin/extension systems (e.g., aggregators, custom senders, submission proxies) with an explicit in-scope/out-of-scope decision for each. This prevents silent omission.

### D. Add a dependency cross-check to the validation step

Step 12 (validation) should include: "For each container, verify its declared relationships against its actual code dependencies. Flag any dependency on another container's internal module that isn't represented as a relationship." This would catch RPC -> sim -> EVM.

### E. Strengthen the "RPC/API gateway" archetype handling

API/RPC containers are frequently modeled as "stateless thin proxies" based on their primary role. The skill should specifically warn against this assumption and require checking whether the API layer performs computation (validation, estimation, transformation) beyond routing. Add a note in the discovery workflow: "API containers often perform more work than docs suggest. Check their dependencies to verify."

### F. Sequence view selection heuristic

The skill says to create sequence views "only for critical workflows" but doesn't help identify which workflows are critical. Add guidance: "For service-oriented backends and modular monoliths, always consider: (1) the primary write path, (2) the primary read/query path, (3) background/async processing, and (4) any path that involves external system dependencies not visible in the container view." Gas estimation would have been caught by heuristic (4).
