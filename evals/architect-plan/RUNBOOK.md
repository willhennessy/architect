# Architect-Plan Eval Runbook

## Purpose

Evaluate `architect-plan` with repeatable iterations, three-lane grading, and promotion gates.

## Files

- `evals.json`: test corpus and scripted feedback rounds
- `scripts/init_iteration.py`: scaffold next `iteration-N`
- `scripts/validate_contract.py`: lane A helper
- `scripts/aggregate_benchmark.py`: iteration benchmark + gate evaluation

## Typical flow

1. Initialize next iteration workspace:

```bash
python3 evals/architect-plan/scripts/init_iteration.py
```

2. For each case in `evals.json`, run:
   - `with_skill` (using `architect-plan`)
   - baseline (`without_skill` for iteration-1, then `old_skill`)

3. Save run artifacts under `iteration-N/eval-<slug>/<variant>/`:
   - `outputs/`
   - `timing.json`
   - `grading.json`
   - `transcript.md`

4. Fill `iteration-N/feedback.json` with human review notes.

5. Aggregate benchmark and gates:

```bash
python3 evals/architect-plan/scripts/aggregate_benchmark.py --iteration evals/architect-plan/iteration-N
```

6. Promote only when all gates pass in `benchmark.json`.
