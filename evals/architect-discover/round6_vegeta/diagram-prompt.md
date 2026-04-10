# Diagram Prompt Bundle — round6_vegeta

## Agent Instruction: Execute the Prompt Below Exactly

If this file is uploaded without any user-typed prompt, treat the prompt in the code block below as the full instruction and execute it directly.

```text
You are a senior Go engineer and interactive visualization designer.

Build a single interactive architecture diagram for **Vegeta** from the provided files.

Output requirements:
1) Return one self-contained HTML file (inline CSS + inline JavaScript, no external dependencies).
2) The diagram must support progressive drill-down navigation:
   - Level 1: System Context
   - Level 2: Container View
   - Level 3: Component View
   - Level 4: Code Detail (only if code-level data exists; otherwise show detail panel)
3) Show a breadcrumb at the top at all times:
   - Format: `Vegeta > <Container> > <Component>`
   - Each segment is clickable to navigate back
   - Include a Back button
4) Click behavior:
   - Single click: open detail panel (name, type, tech, description, responsibilities, owned_data, confidence)
   - Expand icon or double click: drill down to child level
5) Visual behavior:
   - Clickable nodes must look clickable (hover + affordance)
   - Non-expandable nodes must not look clickable
   - Smooth transition between levels
   - Consistent color families by type (container, external system, datastore, component)
6) Relationship behavior:
   - Render only relationships relevant to current level
   - Label edges with interaction/description and protocol when available
   - If endpoint is outside current view, show simplified edge reference node at boundary
7) Sequence views:
   - Do NOT mix sequence flows into drill-down graph
   - Put sequence views in a separate tab/panel
8) Data integrity:
   - Use only facts from provided files (`model.yaml`, `manifest.yaml`, `views/*.yaml`, `summary.md`)
   - Do not invent elements or relationships

Known container set (for validation): Vegeta CLI, Vegeta Library

Now generate the interactive diagram HTML.
```

## View-to-Level Mapping

| View File | Drill-down Level |
|---|---|
| views/component-library.yaml | Component |
| views/container.yaml | Container |
| views/sequence-attack-report.yaml | Sequence (separate tab/panel) |
| views/system-context.yaml | System Context |

## Virtual Directory Tree

```text
round6_vegeta/
  architecture/
    manifest.yaml
    model.yaml
    summary.md
    views/
      component-library.yaml
      container.yaml
      sequence-attack-report.yaml
      system-context.yaml
```

## File Contents

### architecture/manifest.yaml

```yaml
skill_version: "1.0"
repo: "tsenart/vegeta"
repo_path: "evals/repos/vegeta"
output_path: "evals/architect-discover/round6_vegeta/architecture"
extraction_mode: "initial"
archetype: "library_package"
audiences:
  - "backend engineers"
  - "performance engineers"
  - "SREs"
artifacts:
  - path: "model.yaml"
    type: "canonical_model"
  - path: "views/system-context.yaml"
    type: "system_context_view"
  - path: "views/container.yaml"
    type: "container_view"
  - path: "views/component-library.yaml"
    type: "component_view"
    parent: "vegeta-library"
  - path: "views/sequence-attack-report.yaml"
    type: "sequence_view"
  - path: "summary.md"
    type: "summary"
scope:
  in_scope:
    - "evals/repos/vegeta/main.go"
    - "evals/repos/vegeta/*.go"
    - "evals/repos/vegeta/lib/"
    - "evals/repos/vegeta/internal/resolver/"
    - "evals/repos/vegeta/go.mod"
  out_of_scope:
    - "evals/repos/vegeta/README.md (except for context framing)"
    - "evals/repos/vegeta/assets/"
    - "evals/repos/vegeta/scripts/"

```

### architecture/model.yaml

```yaml
version: 2
system_name: "Vegeta"
repo_archetype: "library_package"
elements:
  # === Context-level ===
  - id: "vegeta-system"
    name: "Vegeta"
    aliases: ["vegeta load tester"]
    kind: "software_system"
    c4_level: "context"
    description: "Versatile HTTP load testing tool usable as both a CLI and a Go library. Designed for constant request rate testing with UNIX composability."
    responsibility: "Execute HTTP load tests at controlled rates, collect results, compute metrics, generate reports and plots."
    technology: "Go"
    owned_data: ["attack_results"]
    system_of_record: ["attack_results"]
    runtime_boundary: "process"
    deployable: true
    external: false
    parent_id: ""
    source_paths: ["main.go", "lib/"]
    tags: ["load-testing", "http", "benchmarking"]
    confidence: "confirmed"
    evidence_ids: ["ev-readme", "ev-main"]

  - id: "operator"
    name: "Developer / SRE"
    aliases: []
    kind: "person"
    c4_level: "context"
    description: "Engineer running load tests against HTTP services."
    responsibility: "Define targets, configure attack parameters, analyze results."
    technology: ""
    owned_data: []
    system_of_record: []
    runtime_boundary: "external"
    deployable: false
    external: true
    parent_id: ""
    source_paths: []
    tags: []
    confidence: "confirmed"
    evidence_ids: ["ev-readme"]

  - id: "target-service"
    name: "Target HTTP Service"
    aliases: ["SUT", "system under test"]
    kind: "external_system"
    c4_level: "context"
    description: "The HTTP service being load tested."
    responsibility: "Respond to HTTP requests from Vegeta."
    technology: "HTTP/HTTPS"
    owned_data: []
    system_of_record: []
    runtime_boundary: "external"
    deployable: false
    external: true
    parent_id: ""
    source_paths: []
    tags: ["target"]
    confidence: "confirmed"
    evidence_ids: ["ev-readme", "ev-attack"]

  - id: "prometheus"
    name: "Prometheus"
    aliases: []
    kind: "external_system"
    c4_level: "context"
    description: "Optional metrics scraping endpoint for real-time attack monitoring."
    responsibility: "Scrape Vegeta's Prometheus metrics endpoint during an attack."
    technology: "Prometheus"
    owned_data: []
    system_of_record: []
    runtime_boundary: "external"
    deployable: false
    external: true
    parent_id: ""
    source_paths: ["lib/prom/"]
    tags: ["monitoring", "optional"]
    confidence: "confirmed"
    evidence_ids: ["ev-prom"]

  # === Container-level ===
  # Vegeta is a library_package, so there is one logical container:
  # the CLI binary that wraps the library. The library itself is not
  # a separate runtime unit — it's consumed in-process.

  - id: "vegeta-cli"
    name: "Vegeta CLI"
    aliases: []
    kind: "container"
    c4_level: "container"
    description: "Command-line interface with subcommands: attack, report, plot, encode, dump. Designed for UNIX pipe composition."
    responsibility: "Parse CLI arguments, orchestrate attack/report/plot workflows, handle I/O streams."
    technology: "Go / flag"
    owned_data: []
    system_of_record: []
    runtime_boundary: "process"
    deployable: true
    external: false
    parent_id: "vegeta-system"
    source_paths: ["main.go", "attack.go", "report.go", "plot.go", "encode.go", "dump.go"]
    tags: ["cli"]
    confidence: "confirmed"
    evidence_ids: ["ev-main"]

  - id: "vegeta-library"
    name: "Vegeta Library"
    aliases: ["vegeta/lib"]
    kind: "container"
    c4_level: "container"
    description: "Go library package (github.com/tsenart/vegeta/v12/lib) providing the core attack engine, result types, metrics computation, reporters, target parsing, and pacers. Designed for programmatic use."
    responsibility: "Core load testing engine: HTTP attack execution, result streaming, metrics aggregation, report generation."
    technology: "Go"
    owned_data: []
    system_of_record: []
    runtime_boundary: "library"
    deployable: false
    external: false
    parent_id: "vegeta-system"
    source_paths: ["lib/"]
    tags: ["library", "core"]
    confidence: "confirmed"
    evidence_ids: ["ev-readme", "ev-lib"]

  # === Component-level: Library ===
  - id: "attacker"
    name: "Attacker"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Core HTTP attack executor. Wraps an http.Client, manages worker pool, sends requests at the rate defined by a Pacer, and streams Results."
    responsibility: "Execute HTTP requests at controlled rates with configurable workers, connections, redirects, and TLS settings."
    technology: "Go / net/http"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "vegeta-library"
    source_paths: ["lib/attack.go"]
    tags: ["attack", "http-client"]
    confidence: "confirmed"
    evidence_ids: ["ev-attack"]

  - id: "pacer"
    name: "Pacer"
    aliases: ["rate limiter"]
    kind: "component"
    c4_level: "component"
    description: "Rate control interface. Determines the wait time between successive HTTP hits. Implementations include ConstantPacer (fixed rate), LinearPacer (ramping rate), and SinePacer (oscillating rate)."
    responsibility: "Control attack rate. Avoid Coordinated Omission by decoupling send rate from response latency."
    technology: "Go"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "vegeta-library"
    source_paths: ["lib/pacer.go"]
    tags: ["rate-control"]
    confidence: "confirmed"
    evidence_ids: ["ev-pacer"]

  - id: "targeter"
    name: "Targeter"
    aliases: ["target parser"]
    kind: "component"
    c4_level: "component"
    description: "Target definition and parsing. Supports HTTP format and JSON format. A Targeter is a function that produces Target values (method, URL, headers, body) for each request."
    responsibility: "Parse target definitions from files/stdin and supply targets to the Attacker."
    technology: "Go"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "vegeta-library"
    source_paths: ["lib/targets.go"]
    tags: ["targets"]
    confidence: "confirmed"
    evidence_ids: ["ev-targets"]

  - id: "results-codec"
    name: "Results Codec"
    aliases: ["encoder/decoder"]
    kind: "component"
    c4_level: "component"
    description: "Serialization layer for attack Results. Supports multiple formats: gob (binary, default), CSV, and JSON. Enables UNIX pipe composition between attack and report commands."
    responsibility: "Encode and decode Result streams for storage, piping, and format conversion."
    technology: "Go / encoding/gob, encoding/csv, encoding/json"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "vegeta-library"
    source_paths: ["lib/results.go"]
    tags: ["serialization"]
    confidence: "confirmed"
    evidence_ids: ["ev-results"]

  - id: "metrics-engine"
    name: "Metrics Engine"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Computes aggregate metrics from Result streams: latency percentiles (via t-digest), throughput, success rate, status code distribution, byte metrics."
    responsibility: "Aggregate Results into Metrics for reporting."
    technology: "Go / influxdata/tdigest"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "vegeta-library"
    source_paths: ["lib/metrics.go"]
    tags: ["metrics", "statistics"]
    confidence: "confirmed"
    evidence_ids: ["ev-metrics"]

  - id: "reporters"
    name: "Reporters"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Report generation from computed Metrics. Supports text, JSON, histogram, and HDR histogram output formats."
    responsibility: "Format and write metrics reports to output streams."
    technology: "Go"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "vegeta-library"
    source_paths: ["lib/reporters.go", "lib/histogram.go"]
    tags: ["reporting"]
    confidence: "confirmed"
    evidence_ids: ["ev-reporters"]

  - id: "plot-engine"
    name: "Plot Engine"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Generates interactive HTML plots from Result streams using embedded JavaScript assets. Includes LTTB downsampling for large datasets."
    responsibility: "Render attack results as interactive time series plots."
    technology: "Go / embedded HTML+JS"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "vegeta-library"
    source_paths: ["lib/plot/"]
    tags: ["visualization"]
    confidence: "confirmed"
    evidence_ids: ["ev-plot"]

  - id: "prom-metrics"
    name: "Prometheus Metrics"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Exposes attack metrics as Prometheus counters and histograms for real-time monitoring during an attack."
    responsibility: "Register and update Prometheus metrics from Results."
    technology: "Go / prometheus/client_golang"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "vegeta-library"
    source_paths: ["lib/prom/"]
    tags: ["prometheus", "monitoring"]
    confidence: "confirmed"
    evidence_ids: ["ev-prom"]

  - id: "dns-resolver"
    name: "DNS Resolver"
    aliases: []
    kind: "component"
    c4_level: "component"
    description: "Custom DNS resolver with caching (via dnscache) to avoid DNS latency affecting attack measurements."
    responsibility: "Resolve target hostnames with caching to keep DNS out of latency measurements."
    technology: "Go / rs/dnscache, miekg/dns"
    owned_data: []
    system_of_record: []
    runtime_boundary: "internal_module"
    deployable: false
    external: false
    parent_id: "vegeta-library"
    source_paths: ["internal/resolver/"]
    tags: ["dns"]
    confidence: "confirmed"
    evidence_ids: ["ev-resolver"]

relationships:
  # Context-level
  - id: "rel-operator-cli"
    source_id: "operator"
    target_id: "vegeta-cli"
    label: "Runs vegeta commands (attack, report, plot)"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "cli"
    data_objects: ["AttackConfig", "ResultsStream"]
    confidence: "confirmed"
    evidence_ids: ["ev-main"]

  - id: "rel-attacker-target"
    source_id: "attacker"
    target_id: "target-service"
    label: "Sends HTTP requests at controlled rate"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "http/https"
    data_objects: ["HTTPRequest", "HTTPResponse"]
    confidence: "confirmed"
    evidence_ids: ["ev-attack"]

  - id: "rel-prom-scrape"
    source_id: "prometheus"
    target_id: "prom-metrics"
    label: "Scrapes /metrics endpoint during attack"
    interaction_type: "calls"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "http"
    data_objects: ["PrometheusMetrics"]
    confidence: "confirmed"
    evidence_ids: ["ev-prom"]

  # CLI → Library
  - id: "rel-cli-library"
    source_id: "vegeta-cli"
    target_id: "vegeta-library"
    label: "Uses library for all attack, report, and plot operations"
    interaction_type: "uses"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects: []
    confidence: "confirmed"
    evidence_ids: ["ev-main", "ev-attack-cmd"]

  # Component-level (internal to library)
  - id: "rel-attacker-pacer"
    source_id: "attacker"
    target_id: "pacer"
    label: "Queries pacer for wait duration between hits"
    interaction_type: "uses"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects: ["Duration", "StopSignal"]
    confidence: "confirmed"
    evidence_ids: ["ev-attack", "ev-pacer"]

  - id: "rel-attacker-targeter"
    source_id: "attacker"
    target_id: "targeter"
    label: "Gets next Target for each request"
    interaction_type: "uses"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects: ["Target"]
    confidence: "confirmed"
    evidence_ids: ["ev-attack"]

  - id: "rel-attacker-resolver"
    source_id: "attacker"
    target_id: "dns-resolver"
    label: "Resolves target hostnames with caching"
    interaction_type: "uses"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects: ["Hostname", "IPAddress"]
    confidence: "confirmed"
    evidence_ids: ["ev-attack-cmd", "ev-resolver"]

  - id: "rel-metrics-results"
    source_id: "metrics-engine"
    target_id: "results-codec"
    label: "Reads decoded Results for aggregation"
    interaction_type: "uses"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects: ["Result"]
    confidence: "strong_inference"
    evidence_ids: ["ev-metrics"]

  - id: "rel-reporters-metrics"
    source_id: "reporters"
    target_id: "metrics-engine"
    label: "Reads computed Metrics for report generation"
    interaction_type: "uses"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects: ["Metrics"]
    confidence: "confirmed"
    evidence_ids: ["ev-reporters"]

  - id: "rel-plot-results"
    source_id: "plot-engine"
    target_id: "results-codec"
    label: "Reads decoded Results for plot generation"
    interaction_type: "uses"
    directionality: "unidirectional"
    sync_async: "sync"
    protocol: "in_process"
    data_objects: ["Result"]
    confidence: "strong_inference"
    evidence_ids: ["ev-plot"]

evidence:
  - id: "ev-readme"
    path: "README.md"
    kind: "doc"
    strength: "high"
    reason: "Describes Vegeta as a versatile HTTP load testing tool, CLI + library."

  - id: "ev-main"
    path: "main.go"
    kind: "runtime_entrypoint"
    strength: "high"
    reason: "CLI entrypoint with attack, report, plot, encode, dump commands."

  - id: "ev-attack"
    path: "lib/attack.go"
    kind: "code_path"
    strength: "high"
    reason: "Attacker struct with http.Client, worker pool, pacer integration."

  - id: "ev-attack-cmd"
    path: "attack.go"
    kind: "code_path"
    strength: "high"
    reason: "CLI attack command wiring: creates Attacker, Targeter, Pacer, DNS resolver."

  - id: "ev-pacer"
    path: "lib/pacer.go"
    kind: "code_path"
    strength: "high"
    reason: "Pacer interface with Constant, Linear, Sine implementations."

  - id: "ev-targets"
    path: "lib/targets.go"
    kind: "code_path"
    strength: "high"
    reason: "Target type and Targeter function type with HTTP and JSON format parsers."

  - id: "ev-results"
    path: "lib/results.go"
    kind: "code_path"
    strength: "high"
    reason: "Result type with gob/CSV/JSON encoders and decoders."

  - id: "ev-metrics"
    path: "lib/metrics.go"
    kind: "code_path"
    strength: "high"
    reason: "Metrics struct with latency percentiles, throughput, success rate."

  - id: "ev-reporters"
    path: "lib/reporters.go"
    kind: "code_path"
    strength: "high"
    reason: "Reporter function type with text, JSON, histogram implementations."

  - id: "ev-plot"
    path: "lib/plot/"
    kind: "directory_name"
    strength: "high"
    reason: "Plot package with embedded HTML/JS assets and LTTB downsampling."

  - id: "ev-prom"
    path: "lib/prom/"
    kind: "directory_name"
    strength: "high"
    reason: "Prometheus metrics package with histogram and counter registration."

  - id: "ev-resolver"
    path: "internal/resolver/"
    kind: "directory_name"
    strength: "high"
    reason: "Custom DNS resolver with caching via dnscache."

  - id: "ev-lib"
    path: "lib/"
    kind: "directory_name"
    strength: "high"
    reason: "Library package root — all core types and engines."

unknowns:
  - "Whether the echosrv internal command is used in testing or as a helper for users."

assumptions:
  - "The library is the primary public API surface — the CLI is a thin wrapper."
  - "The results-codec is the UNIX pipe boundary: attack produces gob-encoded results, report/plot consumes them."

```

### architecture/summary.md

```markdown
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

```

### architecture/views/component-library.yaml

```yaml
view_type: "component"
title: "Vegeta Library - Component View"
description: "Internal components of the vegeta/lib package."
parent_container: "vegeta-library"
elements:
  - ref: "attacker"
  - ref: "pacer"
  - ref: "targeter"
  - ref: "results-codec"
  - ref: "metrics-engine"
  - ref: "reporters"
  - ref: "plot-engine"
  - ref: "prom-metrics"
  - ref: "dns-resolver"
  - ref: "target-service"
  - ref: "prometheus"
relationships:
  - ref: "rel-attacker-pacer"
  - ref: "rel-attacker-targeter"
  - ref: "rel-attacker-resolver"
  - ref: "rel-attacker-target"
  - ref: "rel-metrics-results"
  - ref: "rel-reporters-metrics"
  - ref: "rel-plot-results"
  - ref: "rel-prom-scrape"
notes:
  - "The Attacker produces a channel of Results. Metrics, Reporters, and Plot consume Results."
  - "The Results Codec is the serialization boundary enabling UNIX pipe composition."
  - "The Pacer is the key architectural decision: it decouples send rate from response time, avoiding Coordinated Omission."

```

### architecture/views/container.yaml

```yaml
view_type: "container"
title: "Vegeta - Container View"
description: "The CLI binary and its core library."
elements:
  - ref: "vegeta-cli"
  - ref: "vegeta-library"
  - ref: "operator"
  - ref: "target-service"
  - ref: "prometheus"
relationships:
  - ref: "rel-operator-cli"
  - ref: "rel-cli-library"
  - ref: "rel-attacker-target"
  - ref: "rel-prom-scrape"
notes:
  - "The library is the primary public API. The CLI is a thin wrapper."
  - "Results flow as gob-encoded streams between CLI subcommands via UNIX pipes."

```

### architecture/views/sequence-attack-report.yaml

```yaml
view_type: "sequence"
title: "Attack → Report Pipeline"
description: "Typical CLI workflow: run attack, stream results, generate report."
participants:
  - ref: "operator"
  - ref: "vegeta-cli"
  - ref: "attacker"
  - ref: "pacer"
  - ref: "targeter"
  - ref: "dns-resolver"
  - ref: "target-service"
  - ref: "results-codec"
  - ref: "metrics-engine"
  - ref: "reporters"
steps:
  - seq: 1
    source: "operator"
    target: "vegeta-cli"
    label: "Run: vegeta attack -rate=... -duration=..."
    sync_async: "sync"

  - seq: 2
    source: "vegeta-cli"
    target: "attacker"
    label: "Create attacker with workers, timeouts, transport settings"
    sync_async: "sync"

  - seq: 3
    source: "attacker"
    target: "pacer"
    label: "Compute wait interval for next hit"
    sync_async: "sync"

  - seq: 4
    source: "attacker"
    target: "targeter"
    label: "Fetch next target request blueprint"
    sync_async: "sync"

  - seq: 5
    source: "attacker"
    target: "dns-resolver"
    label: "Resolve target hostname (cached)"
    sync_async: "sync"

  - seq: 6
    source: "attacker"
    target: "target-service"
    label: "Send HTTP request"
    sync_async: "sync"
    protocol: "http/https"

  - seq: 7
    source: "attacker"
    target: "results-codec"
    label: "Encode Result stream (gob by default)"
    sync_async: "sync"

  - seq: 8
    source: "operator"
    target: "vegeta-cli"
    label: "Pipe to report: vegeta report"
    sync_async: "sync"

  - seq: 9
    source: "vegeta-cli"
    target: "results-codec"
    label: "Decode Result stream"
    sync_async: "sync"

  - seq: 10
    source: "vegeta-cli"
    target: "metrics-engine"
    label: "Aggregate latency/throughput/error metrics"
    sync_async: "sync"

  - seq: 11
    source: "vegeta-cli"
    target: "reporters"
    label: "Render report output (text/json/histogram)"
    sync_async: "sync"

notes:
  - "UNIX composability is a core design pattern: attack output can be piped directly to report or plot."
  - "Pacer controls send rate independently of response latency to avoid coordinated omission bias."

```

### architecture/views/system-context.yaml

```yaml
view_type: "system_context"
title: "Vegeta - System Context"
description: "High-level view of Vegeta and its external interactions."
elements:
  - ref: "vegeta-system"
  - ref: "operator"
  - ref: "target-service"
  - ref: "prometheus"
relationships:
  - ref: "rel-operator-cli"
  - ref: "rel-attacker-target"
  - ref: "rel-prom-scrape"
notes:
  - "Prometheus integration is optional — only active when -prometheus-addr flag is set during attack."

```
