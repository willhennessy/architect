# Architect-Plan Grading Rubric (Three Lanes)

This rubric is mandatory for each run in every case.

## Lane A — Contract correctness (must-pass, binary)

All checks must pass:

1. output conforms to `skills/references/architecture-contract.md`
2. `generated_by_skill: architect-plan`
3. `evidence_basis: plan`
4. `architecture_state` rules respected:
   - starts as `proposed`
   - changes to `approved` only after explicit user approval
5. no dangling IDs in views or relationships

If any Lane A check fails, run is contract-fail.

## Lane B — Semantic quality (scored)

Score each dimension 1–5:

1. scope and boundary correctness
2. data ownership + system-of-record clarity
3. workflow/sequence correctness
4. rationale quality (constraints + tradeoffs)
5. uncertainty handling (unknowns vs hallucinations)

Calculations:

- `semantic_raw_total = sum(dimensions)` (max 25)
- `semantic_score_40 = semantic_raw_total * 40 / 25` (max 40)

## Lane C — Steering loop quality

Evaluate:

1. asks for targeted engineer feedback
2. revisions incorporate feedback
3. stable IDs preserved for unchanged architecture
4. rounds-to-approval tracked and reasonable

Track these outputs:

- `feedback_incorporation_success_rate` (0-100)
- `unchanged_id_churn_pct` (0-100)
- `rounds_to_approval` (integer)
- `critical_hallucinations` (integer)

## Required grading output format (`grading.json`)

```json
{
  "lane_a_contract": {
    "passed": true,
    "checks": [
      { "name": "schema_conformance", "passed": true, "evidence": "..." },
      { "name": "generated_by_skill", "passed": true, "evidence": "..." },
      { "name": "evidence_basis_plan", "passed": true, "evidence": "..." },
      { "name": "architecture_state_rules", "passed": true, "evidence": "..." },
      { "name": "no_dangling_ids", "passed": true, "evidence": "..." }
    ]
  },
  "lane_b_semantic": {
    "scores": {
      "scope_boundary_correctness": 1,
      "data_ownership_sor_clarity": 1,
      "workflow_sequence_correctness": 1,
      "rationale_quality": 1,
      "uncertainty_handling": 1
    },
    "semantic_raw_total": 5,
    "semantic_score_40": 8.0,
    "evidence_notes": []
  },
  "lane_c_steering_loop": {
    "asks_targeted_feedback": false,
    "feedback_incorporation_success_rate": 0,
    "unchanged_id_churn_pct": 0,
    "rounds_to_approval": 0,
    "critical_hallucinations": 0,
    "evidence_notes": []
  },
  "gate_readiness": {
    "contract_pass_100": false,
    "critical_hallucinations_zero": false,
    "avg_semantic_gte_32_of_40": false,
    "feedback_incorp_gte_80": false,
    "id_churn_lte_10": false,
    "median_rounds_lte_3": false
  }
}
```

## Promotion gates (iteration-level)

Promote only if all are true:

- contract pass: 100%
- critical hallucinations: 0
- average semantic score: >= 32/40
- feedback incorporation success: >= 80%
- unchanged-element ID churn: <= 10%
- median rounds to approval: <= 3
