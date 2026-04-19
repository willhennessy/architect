---
name: run-architecture-eval
description: Run a repeatable eval round for the architect-init skill. Use this when you want to evaluate a new version of the skill on a fresh codebase, get subagent review of the generated architecture artifacts, reflect on the run, and optionally apply improvements to architect-init after user approval.
---

Use this skill to run a full eval loop against a real repository. The goal is consistent evaluation of `architect-init`, not ad hoc repo exploration.

## Outcome

For each eval round, produce:

- `evals/architect-init/roundX_<repo>/architecture/`: generated architecture artifacts
- `evals/architect-init/roundX_<repo>/architecture/diagram.html`: primary interactive HTML architecture diagram (with Comment Mode)
- `evals/architect-init/roundX_<repo>/architecture/diagram-prompt.md`: secondary Claude Imagine upload bundle
- `evals/architect-init/roundX_<repo>/subagent_feedback.md`: summary of fresh subagent review
- `evals/architect-init/roundX_<repo>/scores.yaml`: quantitative scores per the scoring rubric
- `evals/architect-init/roundX_<repo>/reflections.md`: answers to the two reflection questions

The target repository under test must live under `evals/repos/<repo>/` as a local eval cache prepared on demand with `./scripts/ensure-eval-repo.sh`. Do not commit those cached repos.

Do not write generated architecture files inside the repository under test.

## Hard Rules

- Always compute the next round number before naming outputs.
- Always store evaluation outputs in `evals/architect-init/roundX_<repo>/`.
- Always keep the repository under test separate from eval outputs.
- Always use `architect-init` to produce the architecture artifacts.
- Always get review from a fresh subagent before finalizing the round.
- Always score the output using the scoring rubric before writing reflections.
- Always pause after writing reflections and ask the user whether to implement improvements to `architect-init`.
- Do not implement improvements to `architect-init` unless the user explicitly says yes.

## Naming Rules

Determine `X` by scanning existing round output directories directly under `evals/` and extracting the leading integer from directory names matching `round(\d+)(?:_|$)`.

Examples:

- `evals/architect-init/round1_rundler/` counts as round `1`
- `evals/architect-init/round2/` counts as round `2`

Use the next highest round number for both:

- `evals/architect-init/roundX_<repo>/`

Normalize `<repo>` to a simple slug based on the repository name.

## Repo Selection Rules

**Primary source: use the eval catalog.** Read `evals/catalog.yaml` for pre-vetted repositories with known architectural properties. Prefer repos that have NOT been evaluated yet (`eval_rounds: []`). This eliminates the browsing step and ensures consistent, reproducible repo selection.

**When to go off-catalog:** Only if the user explicitly requests a specific repo or all catalog entries have been evaluated. In that case, apply the selection criteria below.

Selection criteria (for off-catalog repos):

- popular on GitHub by stars
- well-written and non-trivial
- architecturally interesting
- no more than `2x` the size of the local Rundler eval cache at `evals/repos/rundler` after filtering out low-signal files

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
   - use `./scripts/eval-source-file-count.sh <repo>`
   - hard reject above `2x` Rundler
   - soft reject above `1.5x` Rundler unless the architecture looks unusually clean and high-value

Do not use GitHub repo size in MB, commit count, or raw unfiltered file count as the primary token-cost heuristic.

If a chosen candidate exceeds the size limit after inspection, discard it and choose another one. If you just fetched a throwaway cache for that candidate, you may delete it before continuing, but do not mutate a reusable cache you still care about.

## Workflow

### 1. Compute round metadata

Before touching a candidate repo:

- find the next round number from existing `evals/architect-init/round*` directories
- ensure the Rundler baseline cache exists with `./scripts/ensure-eval-repo.sh --repo-url https://github.com/alchemyplatform/rundler.git --slug rundler`
- compute the Rundler baseline with `./scripts/eval-source-file-count.sh evals/repos/rundler`

Do not create the round output directory until the repository slug is known.

### 2. Find a candidate repository

Use browsing to find a GitHub repository that fits the selection rules.

For the final candidate, confirm:

- star level is meaningfully high relative to alternatives
- architecture looks interesting from README, docs, and repo layout
- pre-filter signals suggest the repo is not excessively large

After choosing the final candidate, create:

- `evals/architect-init/roundX_<repo>/`

ALWAYS create this directory as soon as you choose the repo name.

### 3. Fetch the repository into the local eval cache

Fetch the repository under:

- `evals/repos/<repo>/`

Use `./scripts/ensure-eval-repo.sh --repo-url <repo-url> --slug <repo>` for GitHub repos, or `./scripts/ensure-eval-repo.sh --repo-path <local-path> --slug <repo>` for a local checkout. The helper intentionally clones without recursing into nested git submodules so the eval cache stays lightweight and does not pollute the public marketplace clone path.

If the repo already exists in the cache, reuse it unless the user explicitly wants a fresh clone or a refresh.

### 4. Verify repo size

After checkout, compare candidate size to `evals/repos/rundler` using the filtered source-file count:

- `./scripts/eval-source-file-count.sh evals/repos/<repo>`

Decision rule:

- accept at or below `1.5x` Rundler
- above `1.5x`, only continue if the repo is unusually strong architecturally and still below `2x`
- above `2x`, remove it and choose another candidate

### 5. Run architect

Invoke `architect-init` on the repository under test.

Set the output path to:

- `evals/architect-init/roundX_<repo>/architecture/`

Then invoke `architect-diagram` using the parent round folder as output root so it reads `architecture/` and writes the primary output (prefer hybrid template + LLM SVG fragments; fallback to deterministic layout if fragments are missing):

- `evals/architect-init/roundX_<repo>/architecture/diagram.html` (primary, includes Comment Mode)

Then invoke `architect-diagram-prompt` on the same output root to generate:

- `evals/architect-init/roundX_<repo>/architecture/diagram-prompt.md` (secondary)

**Do not skip diagram generation.** During eval runs, invoke `architect-diagram` after `architect-init`, then invoke `architect-diagram-prompt` so every round includes both outputs for UX and Anthropic-facing evaluation.

`diagram-prompt.md` must remain upload-ready for zero-text user flows. The file must include a top section with this exact heading:

- `## Agent Instruction: Execute the Prompt Below Exactly`

Immediately below the heading, include an explicit instruction that if the file is uploaded with no user-typed prompt, the agent should treat the embedded prompt as the full instruction and execute it directly.

At the very end of `diagram-prompt.md`, require this one-line handoff instruction:

- `View the architecture diagram here: <fully_resolved_file_path>`

Where `<fully_resolved_file_path>` is the absolute path to `evals/architect-init/roundX_<repo>/architecture/diagram.html`.

Keep the exploration scope limited to the repository under test. Do not explore unrelated directories except:

- the target repo under `evals/repos/<repo>/`
- the round output directory under `evals/architect-init/roundX_<repo>/`
- the skill files being evaluated if and only if the user later approves improvements

### 6. Spawn a fresh subagent for review

Spawn a fresh subagent with minimal context. Do not leak your conclusions. The subagent must be **skill-aware** — it reviews against the skill's own contract, not just general architecture sense.

Give it:

- the repository-under-test path
- the generated architecture output path
- the skill's output contract and rules (extracted from `skills/architect-init/SKILL.md`)
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

- `evals/architect-init/roundX_<repo>/subagent_feedback.md`

Summarize:

- major findings
- recommended changes
- any areas the subagent judged strong
- unresolved disagreements or unknowns

### 7. Score the output

Extract the subagent's quantitative scores and write them to:

- `evals/architect-init/roundX_<repo>/scores.yaml`

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
2. `what improvements should we make to the architect-init skill in order to improve accuracy, efficiency, and comprehensiveness in future runs on other arbitrary software?`

Write the answers to:

- `evals/architect-init/roundX_<repo>/reflections.md`

### 10. Pause and ask the user

After writing the files, stop and ask:

- print the scores (total and per-dimension)
- print both reflection answers in the assistant response
- ask exactly: `Would you like me to implement these improvements to the skill?`

Do not continue automatically.

### 11. If the user says yes

Implement the approved improvements to:

- `skills/architect-init/`

Update companion metadata if needed.

After implementing improvements, update `evals/catalog.yaml` to record the eval round for the repo just evaluated.

### 12. If the user says no

Wait for further input.

## Validation Checklist

Before pausing for user input, verify:

- the target repo exists under `evals/repos/<repo>/`
- the round output directory exists under `evals/architect-init/roundX_<repo>/`
- `architecture/` exists inside the round output directory
- `architecture/diagram.html` exists as a single-file artifact, with no external dependencies beyond the approved Instrument Sans Google Fonts links when that typography path is used
- `scripts/validate-diagram-html.sh evals/architect-init/roundX_<repo>/architecture/diagram.html` passes
- `architecture/diagram.html` includes Comment Mode (`Comment` toggle, `C` shortcut, queued comments, submit modal with JSON handoff)
- relationship hit targets are selectable and carry `data-relationship-id` for edge comments
- any legend appears outside the architecture/system boundary region
- arrows avoid passing through node interiors; edge labels stay close and roughly parallel to edge direction
- confidence labels are not rendered on the diagram canvas (shown in details sidebar only)
- details sidebar is collapsed by default, auto-expands on node click, and includes manual collapse control
- `architecture/diagram-prompt.md` exists and includes:
  - the heading `## Agent Instruction: Execute the Prompt Below Exactly`
  - explicit zero-text upload execution instruction
  - prompt + virtual tree + full artifact contents
  - final line: `View the architecture diagram here: <fully_resolved_file_path>`
  - `<fully_resolved_file_path>` is absolute and points to `.../architecture/diagram.html`
- `subagent_feedback.md` exists
- `scores.yaml` exists and contains all 8 dimensions
- `reflections.md` exists
- the generated architecture artifacts are not stored inside the repo under test
- the subagent used for review was fresh for that round
- if ground truth exists, scores were validated against it
- the repository under test was fetched into the ignored local cache, not reintroduced as a committed git submodule

## Common Mistakes To Avoid

Do not:

- store architecture outputs inside `evals/repos/<repo>/`
- skip either the pre-filter or the post-checkout size check against Rundler
- assume `evals/repos/<repo>/` should be committed or wired up as a git submodule
- reuse stale subagent context
- ask the subagent to rubber-stamp your conclusions
- apply subagent feedback without checking code evidence
- skip writing `reflections.md` in the round directory
- implement skill improvements before the user answers yes
