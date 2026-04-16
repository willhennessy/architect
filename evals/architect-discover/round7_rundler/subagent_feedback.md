# Review Report

Note: this round uses a reviewer-style self-audit in lieu of a delegated fresh subagent review. The architecture outputs were reviewed against the Rundler ground truth and the `architect-discover` contract, but no separate spawned reviewer was used in this thread.

## Findings

### Medium

1. `architecture/model.yaml`: The model only captures the shared `rundler-sim` behavior narratively rather than as an explicit canonical element or stronger cross-cutting note. Ground truth calls out simulation as a recurring source of mistakes because RPC, Pool, and Builder all depend on it, so this round still understates that coupling.

### Low

2. `architecture/summary.md`: The README versus code drift on supported entry point versions is recorded as an unknown, but the summary could call the conflict out more explicitly. Current code references v0.8 and v0.9 support paths in addition to the README’s v0.6 and v0.7 statement, and that mismatch is easy for future readers to miss.

3. `diagram.html` generation path: The generated Rundler artifacts were renderable, but only through the HTML renderer fallback. The production SVG fragment generator currently crashes on arbitrary repos because `skills/architect-diagram/scripts/generate-svg-fragments.py` is still wired to DocSign-specific IDs like `person-doc-sender`. That is a real regression in the discover-to-diagram handoff.

## Strong Areas

- The repo archetype is correctly modeled as `service_oriented_backend`, not `modular_monolith`.
- The container view preserves the three key runtime roles: RPC, Pool, and Builder.
- Pool is correctly modeled as the system of record for live user operation lifecycle state.
- RPC correctly retains its direct dependency on the EVM node for gas estimation, rather than being reduced to a thin proxy.
- Optional AWS KMS, Redis key leasing, and private relay integrations are kept as optional externals rather than core containers.

## Recommended Changes

- Make the shared simulation dependency more explicit in the canonical model or in stronger component-view notes.
- Upgrade the summary’s docs-versus-code support matrix note from a quiet unknown to a clearer conflict callout.
- Fix `generate-svg-fragments.py` so it derives layouts from view contents instead of hardcoded DocSign IDs; otherwise Discover cannot complete the intended rich diagram handoff on arbitrary repos.

## Unresolved Disagreements Or Unknowns

- None on the core runtime shape. The biggest remaining issue is the diagram fragment generator regression, which affects rendering quality and automation parity more than the underlying Rundler architecture model.
