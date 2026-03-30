# Atuin — Architecture Summary

## System Overview

Atuin is a shell history tool that replaces built-in shell history with a SQLite database. It records additional context (cwd, exit code, duration, hostname, session) and optionally syncs history across machines via an Atuin sync server with end-to-end encryption.

## Archetype

**Full-stack product.** The repo contains both the client-side tooling (CLI, daemon, client library) and the server-side sync infrastructure (HTTP server, database adapters). These deploy independently but share a Cargo workspace.

## Key Architectural Decisions

### Client/Server Split
The system has a clear client/server boundary. The client (CLI + daemon + client library) operates independently with local SQLite storage. The sync server is optional — Atuin works fully offline.

### Envelope Encryption (PASETO V4)
All synced data is encrypted client-side using envelope encryption. Each record gets a random content-encryption key (CEK) encrypted with the user's master key. The server stores only ciphertext and can never access plaintext history.

### Record Store Abstraction (V2 Sync)
The V2 sync protocol introduces a generic "record store" — all data types (history, KV, aliases, variables, scripts) share the same sync infrastructure using tagged records. This replaces the V1 protocol which synced history entries directly.

### Daemon for Low-Latency Shell Hooks
The `atuin-daemon` provides a background gRPC service over Unix socket. Shell hooks can record history without the CLI startup overhead. This is critical because `history start` and `history end` are hot paths that run on every command.

### Pluggable Server Database
The sync server supports both Postgres (production) and SQLite (self-hosted/dev) backends via a Database trait with separate crate implementations.

## Runtime Containers

| Container | Technology | Role |
|-----------|-----------|------|
| Atuin CLI | Rust / clap / ratatui | User-facing commands, TUI search, sync trigger |
| Atuin Daemon | Rust / tonic (gRPC) | Background service for low-latency shell hooks |
| Client Library | Rust / sqlx | Core logic: local DB, encryption, sync protocol |
| Local SQLite | SQLite (WAL) | Persistent local storage for all client data |
| Sync Server | Rust / axum | User mgmt, session auth, encrypted record sync |

## Data Ownership

| Data | Owner | System of Record |
|------|-------|-----------------|
| Shell history | Client Library / Local SQLite | Local SQLite (authoritative) |
| Encrypted sync records | Sync Server | Server database (Postgres/SQLite) |
| Encryption key | Client (local filesystem) | `~/.local/share/atuin/key` |
| User accounts & sessions | Sync Server | Server database |
| KV store, dotfiles, scripts | Client Library / Local SQLite | Local SQLite |

## Critical Workflows

1. **History Capture**: Shell hook → `atuin history start/end` → client library → local SQLite. Hot path, no DB init.
2. **Record Sync (V2)**: Client computes diff with server → encrypts local records → uploads → downloads remote records → decrypts → stores locally.
3. **Interactive Search**: User presses Ctrl-R → TUI renders → queries local SQLite with filters.

## Deployment Modes

- **Standalone (no sync)**: CLI + local SQLite only. No server needed.
- **Self-hosted sync**: CLI + sync server (Docker Compose with Postgres).
- **Hosted sync (atuin.sh)**: CLI syncs with the official hosted server.

## Unknowns

- Exact runtime interaction between V1 and V2 sync protocols — are they mutually exclusive?
- Whether the `atuin-ai` crate is actively used or experimental.
- Deployment topology of the hosted atuin.sh service.
