---
name: run-plan-eval
description: Run repeatable planning-mode evals for architect-plan using an iteration workspace pattern with with_skill vs baseline runs, three-lane grading (contract, semantic, steering-loop), and explicit promotion gates.
---

Use this skill to evaluate `architect-plan` quality and regressions in a structured way.

## Outcome

For each iteration, produce:

- `evals/architect-plan/iteration-N/eval-<case-slug>/with_skill/*`
- `evals/architect-plan/iteration-N/eval-<case-slug>/without_skill/*` (iteration 1) or `old_skill/*` (iteration 2+)
- `evals/architect-plan/iteration-N/feedback.json`
- `evals/architect-plan/iteration-N/benchmark.json`

## Required references

Read these before running:

- [references/workspace-pattern.md](references/workspace-pattern.md)
- [references/grading-rubric.md](references/grading-rubric.md)

## Hard rules

- Always grade in three lanes:
  - Lane A: contract correctness (must-pass)
  - Lane B: semantic quality
  - Lane C: steering-loop quality
- Always run per-case comparisons:
  - iteration 1: `with_skill` vs `without_skill`
  - iteration 2+: `with_skill` vs `old_skill`
- Always capture timing for each run (`total_tokens`, `duration_ms`).
- Always aggregate iteration metrics into `benchmark.json`.
- Never promote skill changes unless all promotion gates pass.

## Workflow

### 1) Prepare iteration workspace

- Read `evals/architect-plan/evals.json`.
- Create next workspace using the iteration pattern.
- If needed, initialize with:
  - `python3 evals/architect-plan/scripts/init_iteration.py`

### 2) Execute per-case runs in isolated context

For each test case:

- run **with** `architect-plan` and save outputs to `with_skill/outputs/`
- run baseline variant and save to `without_skill/outputs/` (or `old_skill/outputs/`)
- capture timing in both run folders as `timing.json`
- capture transcript notes in both run folders as `transcript.md`

### 3) Grade each run in three lanes

Write `grading.json` per run using the rubric.

- Lane A (contract) is binary and must include explicit pass/fail evidence.
- Lane B (semantic) scores 5 dimensions (1–5 each) and normalized total /40.
- Lane C (steering loop) scores targeted feedback behavior and revision quality.

### 4) Human review

- Review outputs + grading evidence.
- Add actionable notes to `iteration-N/feedback.json`.

### 5) Aggregate

- Aggregate case-level grading + timing into `iteration-N/benchmark.json`.
- Use:
  - `python3 evals/architect-plan/scripts/aggregate_benchmark.py --iteration evals/architect-plan/iteration-N`

### 6) Gate promotion

Promotion gates (all required):

- contract pass: 100%
- critical hallucinations: 0
- average semantic score: >= 32/40
- feedback incorporation success: >= 80%
- unchanged-element ID churn: <= 10%
- median rounds to approval: <= 3

If any gate fails, do not promote; record failure reasons and iterate.

### 7) Iterate

- Apply changes to `architect-plan`.
- Run next iteration in `iteration-(N+1)`.
- Compare deltas vs prior iteration.

## Completion standard

An eval iteration is complete only when:

1. all test cases have both comparison runs
2. all runs have `timing.json` and `grading.json`
3. iteration-level `feedback.json` and `benchmark.json` exist
4. promotion decision is explicit with gate-by-gate status
