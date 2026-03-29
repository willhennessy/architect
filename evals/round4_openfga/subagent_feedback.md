# Subagent Feedback

## Reviewers

- `019d3b06-48dc-73f1-afc3-cc619fe33f8f`
- `019d3b0e-f7b3-7331-8d48-cb5b8d872040`

## Major Findings

1. The first pass incorrectly assigned the same persisted authorization data to two different systems of record.
2. The first pass treated every datastore mode as an always-external SQL dependency, which was wrong for the in-process memory backend.
3. The first pass skipped the repo's documented command layer, which made the component model and sequences flatter than the code really is.
4. The tuple-write workflow was out of order: the handler resolves the typesystem before module-level write authorization.
5. The check workflow overstated what the request-scoped storage wrapper reads in the classic path.
6. Assertions were persisted in code but incompletely represented in the canonical state model.
7. The artifact set needed one more lifecycle workflow for store bootstrap and authorization-model publication.
8. A few protocol and optional-feature claims were too specific, especially around mixed HTTP/gRPC entry and experimental AuthZEN support.

## Recommended Changes

- Remove duplicate system-of-record claims from `openfga-system` and keep authoritative persistence with the backend that actually stores the data.
- Split persistence modeling into:
  - `persistent-state-backend` for Postgres/MySQL/SQLite
  - `in-memory-state-backend` for the process-local memory adapter
- Restore the `handler -> command -> graph/storage` layering by adding a `command-services` component and routing sequences through it.
- Reorder the tuple-write sequence to match `Write`: resolve typesystem first, then authorize, then execute the write command.
- Narrow the check sequence so request-scoped storage wrappers read tuples and cache metadata, not authorization models, in the classic path.
- Add assertions to the canonical persisted-state model.
- Add a bootstrap sequence covering `CreateStore` and `WriteAuthorizationModel`.
- Mark AuthZEN as experimental/optional and relax over-specific transport protocol labels where evidence supports multiple modes.

## Strengths Observed By Reviewers

- The repo clearly supports a one-container modular-monolith interpretation around `openfga run`.
- The internal split between transport, auth/access control, evaluation, and persistence is well supported by code.
- OIDC and telemetry were correctly treated as optional externals rather than mandatory runtime dependencies.

## Changes Applied After Review

- Updated the canonical model and summary to fix the system-of-record contradiction.
- Replaced the generic external datastore concept with explicit persistent and in-memory backend modeling.
- Added `command-services` to the canonical model and rewired the component view and sequence views through it.
- Corrected the tuple-write and check workflow details to match code evidence.
- Added assertions to persisted-state ownership where appropriate.
- Added `sequence-store-bootstrap.yaml` for the store creation and model-publication lifecycle.
- Softened transport and AuthZEN claims to match actual configuration-gated behavior.

## Unresolved Disagreements Or Unknowns

- No direct disagreements with the reviewers remained after rechecking against code.
- One modeling limitation remains intentional: there is still no deployment view because the repository documents multiple deployment shapes, but the codebase itself does not enforce one canonical production topology strongly enough to justify a single deployment artifact.
