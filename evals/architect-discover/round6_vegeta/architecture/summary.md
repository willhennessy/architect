# Vegeta — Architecture Summary

## System Overview

Vegeta is an HTTP load testing system with dual surfaces:
1. A CLI binary for command-line workflows (`attack`, `report`, `plot`, `encode`, `dump`)
2. A Go library (`github.com/tsenart/vegeta/v12/lib`) for embedding load testing directly in code.

The architecture is intentionally UNIX-composable. Attack results are streamed and encoded so downstream commands can consume them through pipes.

## Archetype

**Library package.**

This repo is best modeled as a library-first package with a CLI wrapper. The core architecture lives in `lib/`, while top-level command files are orchestration wrappers.

## Core Components

- **Attacker**: HTTP execution engine with worker pool and transport tuning.
- **Pacer**: Rate control strategy interface (constant, linear, sine patterns).
- **Targeter**: Request blueprint provider (method, URL, headers, body).
- **Results Codec**: Stream serialization (gob/CSV/JSON) for composable pipelines.
- **Metrics Engine**: Aggregation (latency percentiles, throughput, status distribution).
- **Reporters**: Output formatters (text/json/histogram/HDR histogram).
- **Plot Engine**: Interactive HTML plotting with downsampling support.
- **Prometheus Metrics**: Optional live metrics endpoint.
- **DNS Resolver**: Cached DNS lookups to reduce measurement distortion.

## Key Architectural Decisions

### 1) Rate control is a first-class abstraction
The Pacer interface separates request scheduling from HTTP execution, which prevents coordinated omission and keeps load generation mathematically explicit.

### 2) Streaming result pipeline
Results are encoded as a stream and consumed by reporting/plotting stages. This enables `vegeta attack | vegeta report` and `vegeta attack | vegeta plot` without intermediate storage requirements.

### 3) CLI/library parity
The CLI and library share the same core engine. The command layer mostly maps flags to library options.

### 4) Observability as optional extension
Prometheus integration is not required for core operation, but can be enabled for real-time metrics export.

## Data Ownership

- **Attack results** are the primary domain data object.
- Results are transient during execution but can be persisted via encoded output streams.
- Vegeta does not own target service state; it only observes response metrics.

## Critical Workflow

1. Operator starts `vegeta attack` with rate and duration.
2. CLI creates Attacker and configures Pacer and Targeter.
3. Attacker resolves hostnames, sends HTTP requests to target service.
4. Results are emitted and encoded as a stream.
5. `vegeta report` decodes stream, aggregates metrics, renders output.

## Strengths of Architecture

- Clean separation of concerns in the library.
- Strong composability for shell workflows.
- Minimal coupling between rate control, execution, and reporting.
- Small codebase with high conceptual clarity.

## Unknowns

- Whether `internal/cmd/echosrv` is intended purely as internal test tooling or user-facing helper.
