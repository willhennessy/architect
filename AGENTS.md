# AGENTS.md (Repo-local)

This file is for fresh agents working specifically in the `architect` repo.

## Mission

Help Will evolve Architect quickly while preserving:

1. artifact contract correctness
2. test/prod behavior parity
3. demo quality for diagrams

---

## First 10 minutes checklist

1. Read:
   - `README.md`
   - `skills/references/architecture-contract.md`
   - relevant skill `SKILL.md` files for the task
2. Identify scope:
   - plan/discover logic?
   - diagram/rendering logic?
   - eval harness only?
3. Run one baseline regression:

```bash
./scripts/run-docsign-test.sh
```

4. Confirm where outputs were written:
- `evals/manual-docsign-tests/run-XXX/`
- `evals/manual-docsign-tests/diagram-<n>.html`

---

## Canonical skills and responsibilities

- `architect-plan`: requirements -> architecture artifacts
- `architect-discover`: repo -> architecture artifacts
- `architect-diagram`: artifacts -> `diagram.html`
- `architect-diagram-prompt`: artifacts -> `diagram-prompt.md` (explicit only)

Do not silently merge skill responsibilities. Keep boundaries clear.

---

## Test protocol (important)

Use the fixed DocSign prompt test harness for fast regressions:

```bash
./scripts/run-docsign-test.sh
```

Harness behavior:
- isolated run directory per test
- detects whether `architect-plan` changed
  - if yes: regenerate architecture artifacts
  - if no: reuse prior architecture artifacts and rerender diagram only
- emits numbered `diagram-<n>.html`

This protocol is required to reduce token/time usage and keep comparisons meaningful.

The harness must call production diagram generation scripts (not harness-only rendering forks).

---

## Messaging/output requirement

After each manual DocSign test run, send the numbered HTML diagram file back in chat.

Pattern:
- `diagram-1.html`, `diagram-2.html`, ...

Do not skip this step.

---

## Contract and quality gates

### Always preserve
- stable IDs for unchanged concepts
- no invented entities/relationships outside available evidence
- explicit unknowns/assumptions

### Plan quality checks (when touching plan flow)
- decision coverage check
- container decomposition policy check
- semantic diff gate

### Diagram quality checks
- validate generated `diagram.html` with diagram validator before reporting success
- keep interaction metadata intact (`data-element-id`, `data-relationship-id`)
- node card header geometry is split across production SVG generation and browser-side normalization
- if you change header band height, header label alignment, or person-card header layout, update both `skills/architect-diagram/scripts/generate-svg-fragments.py` and `skills/architect-diagram/templates/diagram-app.html` (`ensureNodeHeaderShape` / `simplifyPersonNodeGroup`) to avoid drift

---

## Test/prod parity rule

If you improve layout/style in a harness helper script, either:

1. promote the same behavior into production skill flow, or
2. clearly mark it as harness-only and call out parity risk.

Prefer option (1).

---

## When making changes

1. Make small focused edits.
2. Rerun `./scripts/run-docsign-test.sh`.
3. Verify output visually (at least system-context + container views).
4. Commit with clear message.
5. Push when Will asks or when the workflow requires immediate validation.

---

## Common commands

```bash
# repo status
git status --short --branch

# run fixed regression test
./scripts/run-docsign-test.sh

# isolated manual run
./scripts/new-manual-eval.sh --repo-url <url> --name <run-name>

# python syntax checks
python3 -m py_compile <script.py>
```

---

## Non-goals

- Do not add heavy abstractions unless needed.
- Do not optimize for generic beauty at the expense of deterministic, testable behavior.
- Do not change prompt/skill boundaries without updating both README + this file.
