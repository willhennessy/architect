# Architect-Plan Eval Workspace Pattern

Use an iteration directory for each full eval pass.

## Root layout

```text
evals/architect-plan/
  evals.json
  files/
  scripts/
  iteration-1/
  iteration-2/
  ...
```

## Per-iteration layout

```text
iteration-N/
  eval-<case-slug>/
    with_skill/
      outputs/
      timing.json
      grading.json
      transcript.md
    without_skill/        # iteration-1 baseline
      outputs/
      timing.json
      grading.json
      transcript.md
    old_skill/            # iteration-2+ baseline (instead of without_skill)
      outputs/
      timing.json
      grading.json
      transcript.md
  feedback.json
  benchmark.json
  skill-snapshot/         # iteration-2+ only
```

Notes:

- Use `without_skill` only in iteration 1.
- Use `old_skill` in later iterations and keep a `skill-snapshot/` copy of the previous version.
- One `eval-<case-slug>/` directory per case in `evals.json`.

## Run isolation

Each run should start in a clean context:

- no state leakage from prior runs
- no evaluator conclusions included in generation prompt
- same test prompt for both with-skill and baseline variants

## Timing capture

Every run must include:

```json
{
  "total_tokens": 0,
  "duration_ms": 0
}
```

Store as `timing.json` in each run folder.
