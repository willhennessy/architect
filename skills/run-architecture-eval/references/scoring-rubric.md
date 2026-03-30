# Architecture Eval Scoring Rubric

Score each dimension 1-5. Compute the total (max 40). Track scores across rounds to measure skill improvement.

## Dimensions

### 1. Element Accuracy (1-5)

Are the identified elements (containers, components, external systems) correct?

| Score | Criteria |
|-------|----------|
| 5 | All elements match ground truth. No hallucinated elements. No missing elements. |
| 4 | 1 minor element missing or 1 element with wrong classification. No hallucinations. |
| 3 | 2-3 elements missing or misclassified. Or 1 hallucinated element. |
| 2 | Multiple missing elements AND hallucinated elements. Core structure partially wrong. |
| 1 | Fundamental misunderstanding of what the system is. Major elements missing or invented. |

### 2. Relationship Completeness (1-5)

Are the relationships between elements correctly identified with accurate direction, protocol, and sync/async classification?

| Score | Criteria |
|-------|----------|
| 5 | All critical relationships present. Direction, protocol, and sync/async correct. |
| 4 | All critical relationships present. 1-2 minor protocol or direction errors. |
| 3 | 1 critical relationship missing. Or 3+ minor errors in relationship metadata. |
| 2 | Multiple critical relationships missing. Several direction or protocol errors. |
| 1 | Relationship model is fundamentally wrong. Major paths missing or invented. |

### 3. Abstraction Discipline (1-5)

Does the output respect C4 level boundaries? Are containers, components, and code-level elements properly separated?

| Score | Criteria |
|-------|----------|
| 5 | Strict level separation. No mixed-level views. Correct element types at each level. |
| 4 | 1 minor level violation (e.g., a component appearing in a container view). |
| 3 | 2-3 level violations. Or a view that mixes two abstraction levels. |
| 2 | Systematic level confusion. Multiple views mix abstractions. |
| 1 | No meaningful abstraction discipline. Flat model without proper C4 layering. |

### 4. Data Ownership Coverage (1-5)

Are data ownership boundaries, systems of record, and state classification (owned/cached/derived/external) correctly identified?

| Score | Criteria |
|-------|----------|
| 5 | All persisted entities accounted for. SoR assignments correct. State types classified. No duplicate SoR claims. |
| 4 | 1 entity missing from ownership model. Or 1 ambiguous SoR assignment. |
| 3 | 2-3 entities missing. Or 1 incorrect SoR assignment. Or duplicate SoR without justification. |
| 2 | Major data ownership gaps. Multiple incorrect SoR claims. |
| 1 | Data ownership not meaningfully modeled. |

### 5. Workflow Coverage (1-5)

Are critical workflows (request paths, auth, business transactions, async processing, bootstrap) identified and correctly sequenced?

| Score | Criteria |
|-------|----------|
| 5 | All critical workflows present. Sequence steps match actual code execution order. |
| 4 | All critical workflows present. 1-2 minor ordering or participant errors. |
| 3 | 1 critical workflow missing. Or a workflow with incorrect step ordering. |
| 2 | Multiple critical workflows missing. Or workflows with fundamentally wrong sequences. |
| 1 | No meaningful workflow coverage. |

### 6. Evidence Discipline (1-5)

Does the output distinguish confirmed facts from inferences? Are confidence levels calibrated? Are unknowns recorded rather than invented?

| Score | Criteria |
|-------|----------|
| 5 | All claims have appropriate confidence. Unknowns explicitly recorded. No unsupported claims. |
| 4 | Most claims properly attributed. 1-2 weak inferences not flagged. |
| 3 | Several unsupported claims. Or confidence levels not meaningfully differentiated. |
| 2 | Many claims presented as confirmed without evidence. Unknowns silently omitted. |
| 1 | No evidence discipline. Everything presented as fact regardless of support. |

### 7. Archetype Fit (1-5)

Is the repo archetype correctly identified? Does the artifact set match the archetype defaults?

| Score | Criteria |
|-------|----------|
| 5 | Correct archetype. Artifact set matches archetype defaults. No over/under-production. |
| 4 | Correct archetype. 1 unnecessary view produced or 1 useful view missing. |
| 3 | Archetype debatable but defensible. Artifact set slightly mismatched. |
| 2 | Wrong archetype. Artifact set doesn't match what the repo actually is. |
| 1 | Fundamentally wrong archetype (e.g., calling a library a service-oriented backend). |

### 8. Efficiency (1-5)

Was the architecture discovered without excessive file reads, redundant passes, or unnecessary exploration?

| Score | Criteria |
|-------|----------|
| 5 | Minimal discovery passes. Targeted reads. No redundant exploration. |
| 4 | 1 unnecessary exploration pass. Mostly targeted. |
| 3 | Some redundant reads. 2-3 unnecessary exploration tangents. |
| 2 | Significant wasted effort. Many files read that didn't contribute to the model. |
| 1 | Sprawling, unfocused exploration. Most reads were unnecessary. |

## Scoring Output Format

```yaml
scores:
  element_accuracy: X
  relationship_completeness: X
  abstraction_discipline: X
  data_ownership_coverage: X
  workflow_coverage: X
  evidence_discipline: X
  archetype_fit: X
  efficiency: X
  total: XX  # out of 40
  notes:
    - "dimension: specific observation"
    - "dimension: specific observation"
```

## Comparison Across Rounds

When multiple rounds exist for the same repo or skill version, compare scores:

```yaml
comparison:
  previous_round: roundX
  previous_total: XX
  current_total: XX
  delta: +/-X
  improved: [dimensions that went up]
  regressed: [dimensions that went down]
  unchanged: [dimensions that stayed the same]
```

## Ground Truth Scoring

When a ground truth reference exists (in `evals/ground-truth/<repo>.yaml`), the reviewer MUST score against it rather than using subjective judgment alone. For each dimension, compare the generated output against the ground truth and assign the score based on divergence.
