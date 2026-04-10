# Reflections — Round 6 (Vegeta)

## 1. What would I have done differently?

**Modeled result sinks explicitly.** Vegeta's pipeline design depends on result streams flowing through stdout/files. I captured encoding and decoding but not sink boundaries. For a tool designed around UNIX composability, those boundaries matter.

**Added a second sequence for observability.** Prometheus integration is optional but first-class enough to deserve a dedicated sequence view for attacks with `-prometheus-addr`.

**Documented the library-as-container tradeoff upfront.** I intentionally modeled `vegeta-library` as a container to make architecture explicit, but the stricter C4 interpretation would treat it as components under CLI. I should have called out this decision earlier in the summary/manifest notes.

## 2. What improvements should we make to the architect-discover skill?

### A. Add explicit guidance for library_package repo modeling

The current skill says library packages should prefer component/module views over container views, but it doesn't clarify how to handle repos with both CLI wrappers and a substantial library. Add a decision rule:
- If CLI is thin and library contains core architecture, model both and call the tradeoff.
- If library is minimal helper code, keep only CLI container + components.

### B. Add support for non-system data sinks in workflows

For CLI/pipeline tools, outputs often flow to stdout/files/streams rather than persistent services. Add optional modeling guidance for sink boundaries (stdout, file, pipe) when they are architecturally central.

### C. Add an "optional workflow" annotation pattern

The skill already handles optional externals, but workflows should also support optional labels. For example: "Prometheus scrape flow (optional, flag-gated)."

### D. Strengthen data ownership checks for transient pipelines

Data ownership rules are currently storage-centric. For stream-processing systems, add guidance to classify:
- transient in-memory stream data
- persisted artifacts (if any)
- externally observed metrics (telemetry)

This helps avoid under-scoring data ownership on tools that don't have traditional databases.
