# OpenFGA Architecture Summary

OpenFGA is best modeled here as a modular monolith built around the `openfga run` server path. The runtime is a single Go process that exposes gRPC natively, serves HTTP through an in-process grpc-gateway, and can optionally host a local playground UI on a separate listener. The same runtime also wires in logging, validation, tracing, metrics, authentication middleware, and an experimental AuthZEN surface when that feature flag is enabled.

The main architectural boundaries inside that process are:

- `API Surface`: transport handlers for gRPC, HTTP, and the optional playground.
- `Auth And Access Control`: request authentication plus optional recursive authorization against a dedicated access-control store.
- `Command Services`: transport-agnostic business logic that sequences request validation, model resolution, graph execution, and persistence.
- `Authorization Engines`: typesystem resolution, graph and modelgraph execution, planner usage, and shared cache coordination for `Check`, `ListObjects`, and `ListUsers`.
- `Datastore Adapters`: the persistence contract plus backend implementations for memory, Postgres, MySQL, and SQLite.

In persistent deployments, the configured SQL backend is the authoritative system of record for authorization stores, models, tuples, assertions, and tuple change history. In local or ephemeral deployments, the in-memory adapter keeps that same state inside the server process instead. The server also supports optional external integrations for OIDC token validation and OpenTelemetry export.

Two workflows dominate the runtime:

1. Store bootstrap: a caller creates a store, then publishes an authorization model that defines the store's policy vocabulary.
2. Permission evaluation: the server authenticates and authorizes the caller, hands the request to the command layer, resolves the active authorization model, reads tuples through storage wrappers, and returns an allow/deny decision. Depending on feature flags, this can run through the classic graph resolver or the weighted-graph path.
3. Tuple mutation: the server resolves the active model, authorizes the caller with that model context, validates tuple semantics and request options, and performs a transactional delete-then-insert write through the configured backend.

The main modeling choice in this round is to keep OpenFGA as one container, not three. Even though the runtime exposes multiple listeners and protocols, the repo starts them from one process and shares the same core server object, command layer, caches, planner, and datastore integration logic. That makes the API, auth, command, graph-evaluation, and persistence layers better represented as internal components than as separate deployable containers.
