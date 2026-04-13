---
name: run-architecture-eval
description: Run a repeatable eval round for the architect-discover skill. Use this when you want to evaluate a new version of the skill on a fresh codebase, get subagent review of the generated architecture artifacts, reflect on the run, and optionally apply improvements to architect-discover after user approval.
---

Use this skill to run a full eval loop against a real repository. The goal is consistent evaluation of `architect-discover`, not ad hoc repo exploration.

## Outcome

For each eval round, produce:

- `evals/architect-discover/roundX_<repo>/architecture/`: generated architecture artifacts
- `evals/architect-discover/roundX_<repo>/diagram-prompt.md`: bundled upload file for Claude Imagine interactive diagram generation
- `evals/architect-discover/roundX_<repo>/subagent_feedback.md`: summary of fresh subagent review
- `evals/architect-discover/roundX_<repo>/scores.yaml`: quantitative scores per the scoring rubric
- `evals/architect-discover/roundX_<repo>/reflections.md`: answers to the two reflection questions

The target repository under test must live under `evals/repos/<repo>/` as a git submodule.

Do not write generated architecture files inside the repository under test.

## Hard Rules

- Always compute the next round number before naming outputs.
- Always store evaluation outputs in `evals/architect-discover/roundX_<repo>/`.
- Always keep the repository under test separate from eval outputs.
- Always use `architect-discover` to produce the architecture artifacts.
- Always get review from a fresh subagent before finalizing the round.
- Always score the output using the scoring rubric before writing reflections.
- Always pause after writing reflections and ask the user whether to implement improvements to `architect-discover`.
- Do not implement improvements to `architect-discover` unless the user explicitly says yes.

## Naming Rules

Determine `X` by scanning existing round output directories directly under `evals/` and extracting the leading integer from directory names matching `round(\d+)(?:_|$)`.

Examples:

- `evals/architect-discover/round1_rundler/` counts as round `1`
- `evals/architect-discover/round2/` counts as round `2`

Use the next highest round number for both:

- `evals/architect-discover/roundX_<repo>/`

Normalize `<repo>` to a simple slug based on the repository name.

## Repo Selection Rules

**Primary source: use the eval catalog.** Read `evals/catalog.yaml` for pre-vetted repositories with known architectural properties. Prefer repos that have NOT been evaluated yet (`eval_rounds: []`). This eliminates the browsing step and ensures consistent, reproducible repo selection.

**When to go off-catalog:** Only if the user explicitly requests a specific repo or all catalog entries have been evaluated. In that case, apply the selection criteria below.

Selection criteria (for off-catalog repos):

- popular on GitHub by stars
- well-written and non-trivial
- architecturally interesting
- no more than `2x` the size of `evals/repos/rundler` after filtering out low-signal files

Prefer:

- service-oriented backends
- modular monoliths
- infrastructure/control-plane systems
- developer tools with clear runtime roles

Avoid:

- toy repos
- generated SDKs
- frontend-only repos unless the architecture is unusually strong
- giant framework repos or kernels that will explode token use

Use a two-stage size heuristic:

1. Cheap pre-filter before checkout:
   - skip repos that are obviously huge by category: kernels, browsers, language runtimes, giant framework monorepos, platform ecosystems
   - skip repos whose tree shape suggests very high token cost
   - prefer repos that feel like one system, product, or control plane rather than an ecosystem
2. Hard cutoff after checkout:
   - compare filtered source file count against `evals/repos/rundler`
   - use:
     - `rg --files <repo> -g '!**/.git/**' -g '!**/node_modules/**' -g '!**/dist/**' -g '!**/build/**' -g '!**/target/**' -g '!**/vendor/**' -g '!**/third_party/**' -g '!**/coverage/**' | wc -l`
   - hard reject above `2x` Rundler
   - soft reject above `1.5x` Rundler unless the architecture looks unusually clean and high-value

Do not use GitHub repo size in MB, commit count, or raw unfiltered file count as the primary token-cost heuristic.

If a chosen candidate exceeds the size limit after inspection, discard it and choose another one. If you already added it as a submodule for the current round, remove that just-added submodule before continuing.

## Workflow

### 1. Compute round metadata

Before touching a candidate repo:

- find the next round number from existing `evals/architect-discover/round*` directories
- compute the Rundler baseline using the filtered `rg --files` count defined in this skill

Do not create the round output directory until the repository slug is known.

### 2. Find a candidate repository

Use browsing to find a GitHub repository that fits the selection rules.

For the final candidate, confirm:

- star level is meaningfully high relative to alternatives
- architecture looks interesting from README, docs, and repo layout
- pre-filter signals suggest the repo is not excessively large

After choosing the final candidate, create:

- `evals/architect-discover/roundX_<repo>/`

ALWAYS create this directory as soon as you choose the repo name.

### 3. Add the repository as a submodule

Add the repository under:

- `evals/repos/<repo>/`

Use a normal git submodule flow. If the repo already exists under `evals/`, prefer choosing a different repo for broader eval coverage unless the user explicitly wants a repeat.

### 4. Verify repo size

After checkout, compare candidate size to `evals/repos/rundler` using the filtered source-file count:

- `rg --files evals/repos/<repo> -g '!**/.git/**' -g '!**/node_modules/**' -g '!**/dist/**' -g '!**/build/**' -g '!**/target/**' -g '!**/vendor/**' -g '!**/third_party/**' -g '!**/coverage/**' | wc -l`

Decision rule:

- accept at or below `1.5x` Rundler
- above `1.5x`, only continue if the repo is unusually strong architecturally and still below `2x`
- above `2x`, remove it and choose another candidate

### 5. Run architect

Invoke `architect-discover` on the repository under test.

Set the output path to:

- `evals/architect-discover/roundX_<repo>/architecture/`

Then invoke `architect-diagram-prompt` using the parent round folder as output root so it reads `architecture/` and writes:

- `evals/architect-discover/roundX_<repo>/diagram-prompt.md`

**Do not skip diagram prompt generation.** During eval runs, invoke `architect-diagram-prompt` after `architect-discover` so every round includes `diagram-prompt.md` for visualization feedback.

Required bundled output path:

- `evals/architect-discover/roundX_<repo>/diagram-prompt.md`

`diagram-prompt.md` must be upload-ready for zero-text user flows. The file must include a top section with this exact heading:

- `## Agent Instruction: Execute the Prompt Below Exactly`

Immediately below the heading, include an explicit instruction that if the file is uploaded with no user-typed prompt, the agent should treat the embedded prompt as the full instruction and execute it directly.

Keep the exploration scope limited to the repository under test. Do not explore unrelated directories except:

- the target repo under `evals/repos/<repo>/`
- the round output directory under `evals/architect-discover/roundX_<repo>/`
- the skill files being evaluated if and only if the user later approves improvements

### 6. Spawn a fresh subagent for review

Spawn a fresh subagent with minimal context. Do not leak your conclusions. The subagent must be **skill-aware** — it reviews against the skill's own contract, not just general architecture sense.

Give it:

- the repository-under-test path
- the generated architecture output path
- the skill's output contract and rules (extracted from `skills/architect-discover/SKILL.md`)
- the scoring rubric (from `skills/run-architecture-eval/references/scoring-rubric.md`)
- the ground truth file if one exists (from `evals/ground-truth/<repo>.yaml`)

Use a prompt equivalent to:

> You are a staff engineer evaluating an automated architecture generation tool. Your job is to review the generated architecture artifacts AND score them quantitatively.
>
> **Repository under test:** `<repo_path>`
> **Generated artifacts:** `<architecture_path>`
>
> **Skill contract (the tool's own rules — check compliance):**
> - C4 boundary rules: System Context contains only the system of interest, people, and external systems. Container views contain only deployable/runtime units, datastores, queues, and relevant externals. Component views contain internal modules within exactly ONE container only.
> - Data ownership: Every container/component should declare owned_data and system_of_record. No entity should be assigned to multiple systems of record without explicit justification.
> - Evidence hierarchy (strongest to weakest): (1) Runtime/deploy reality, (2) Contract/state signals, (3) Behavioral code signals, (4) Documentation, (5) Naming-only signals.
> - Confidence levels must be used: confirmed, strong_inference, weak_inference.
> - Unknowns must be recorded, not invented.
> - Sequence view participants must exist in the canonical model.
> - Views must not mix C4 abstraction levels.
>
> **Ground truth reference (if provided):**
> <contents of evals/ground-truth/<repo>.yaml, or "No ground truth available for this repo.">
>
> **Scoring rubric:**
> <contents of skills/run-architecture-eval/references/scoring-rubric.md>
>
> **Your deliverable:**
> 1. A semantic review report: findings ordered by severity with concrete file references.
> 2. A quantitative score using the rubric (all 8 dimensions, 1-5 each, total out of 40).
> 3. For each score, cite specific evidence supporting the rating.
>
> Focus on: semantic correctness, abstraction discipline, data ownership modeling, critical workflow coverage, unsupported claims, missing or misleading relationships, and compliance with the skill's own rules.

Capture the subagent's output in:

- `evals/architect-discover/roundX_<repo>/subagent_feedback.md`

Summarize:

- major findings
- recommended changes
- any areas the subagent judged strong
- unresolved disagreements or unknowns

### 7. Score the output

Extract the subagent's quantitative scores and write them to:

- `evals/architect-discover/roundX_<repo>/scores.yaml`

Use the format defined in `skills/run-architecture-eval/references/scoring-rubric.md`.

If ground truth exists, validate the subagent's scores against it. If you disagree with any score by more than 1 point, override it with your own assessment and note the disagreement.

If previous rounds exist for the same repo or a different repo evaluated with the same skill version, include a comparison section showing score deltas.

### 8. Apply the feedback

Review the subagent feedback yourself and update the generated architecture artifacts as needed.

Do not blindly apply feedback. Re-check against code and evidence.

If you disagree with a subagent suggestion, keep the existing model and record the disagreement in `subagent_feedback.md`.

### 9. Reflect

Answer both questions yourself:

1. `now that you've done this, what would you have done differently?`
2. `what improvements should we make to the architect-discover skill in order to improve accuracy, efficiency, and comprehensiveness in future runs on other arbitrary software?`

Write the answers to:

- `evals/architect-discover/roundX_<repo>/reflections.md`

### 10. Pause and ask the user

After writing the files, stop and ask:

- print the scores (total and per-dimension)
- print both reflection answers in the assistant response
- ask exactly: `Would you like me to implement these improvements to the skill?`

Do not continue automatically.

### 11. If the user says yes

Implement the approved improvements to:

- `skills/architect-discover/`

Update companion metadata if needed.

After implementing improvements, update `evals/catalog.yaml` to record the eval round for the repo just evaluated.

### 12. If the user says no

Wait for further input.

## Validation Checklist

Before pausing for user input, verify:

- the target repo exists under `evals/repos/<repo>/`
- the round output directory exists under `evals/architect-discover/roundX_<repo>/`
- `architecture/` exists inside the round output directory
- `diagram-prompt.md` exists and includes:
  - the heading `## Agent Instruction: Execute the Prompt Below Exactly`
  - explicit zero-text upload execution instruction
  - prompt + virtual tree + full artifact contents
- `subagent_feedback.md` exists
- `scores.yaml` exists and contains all 8 dimensions
- `reflections.md` exists
- the generated architecture artifacts are not stored inside the repo under test
- the subagent used for review was fresh for that round
- if ground truth exists, scores were validated against it

## Common Mistakes To Avoid

Do not:

- store architecture outputs inside `evals/repos/<repo>/`
- skip either the pre-filter or the post-checkout size check against Rundler
- reuse stale subagent context
- ask the subagent to rubber-stamp your conclusions
- apply subagent feedback without checking code evidence
- skip writing `reflections.md` in the round directory
- implement skill improvements before the user answers yes
