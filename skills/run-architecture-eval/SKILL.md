---
name: run-architecture-eval
description: Run a repeatable eval round for the generate-architecture skill. Use this when you want to evaluate a new version of the skill on a fresh codebase, get subagent review of the generated architecture artifacts, reflect on the run, and optionally apply improvements to generate-architecture after user approval.
---

Use this skill to run a full eval loop against a real repository. The goal is consistent evaluation of `generate-architecture`, not ad hoc repo exploration.

## Outcome

For each eval round, produce:

- `evals/roundX_<repo>/architecture/`: generated architecture artifacts
- `evals/roundX_<repo>/subagent_feedback.md`: summary of fresh subagent review
- `evals/roundX_<repo>/reflections.md`: answers to the two reflection questions

The target repository under test must live separately under `evals/<repo>/` as a git submodule.

Do not write generated architecture files inside the repository under test.

## Hard Rules

- Always compute the next round number before naming outputs.
- Always store evaluation outputs in `evals/roundX_<repo>/`.
- Always keep the repository under test separate from eval outputs.
- Always use `generate-architecture` to produce the architecture artifacts.
- Always get review from a fresh subagent before finalizing the round.
- Always pause after writing reflections and ask the user whether to implement improvements to `generate-architecture`.
- Do not implement improvements to `generate-architecture` unless the user explicitly says yes.

## Naming Rules

Determine `X` by scanning existing round output directories directly under `evals/` and extracting the leading integer from directory names matching `round(\d+)(?:_|$)`.

Examples:

- `evals/round1_rundler/` counts as round `1`
- `evals/round2/` counts as round `2`

Use the next highest round number for both:

- `evals/roundX_<repo>/`

Normalize `<repo>` to a simple slug based on the repository name.

## Repo Selection Rules

Choose a repository that is:

- popular on GitHub by stars
- well-written and non-trivial
- architecturally interesting
- no more than `2x` the size of `evals/repos/rundler` after filtering out low-signal files

Use browsing to find candidates. Favor repositories that expose meaningful runtime boundaries, data ownership boundaries, or deployment complexity.

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
   - skip repos whose tree shape suggests very high token cost:
     - many top-level packages or services
     - obvious `vendor/`, `third_party/`, `generated/`, `dist/`, or giant docs trees
     - many language ecosystems in one repo
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

- find the next round number from existing `evals/round*` directories
- compute the Rundler baseline using the filtered `rg --files` count defined in this skill

Do not create the round output directory until the repository slug is known.

### 2. Find a candidate repository

Use browsing to find a GitHub repository that fits the selection rules.

For the final candidate, confirm:

- star level is meaningfully high relative to alternatives
- architecture looks interesting from README, docs, and repo layout
- pre-filter signals suggest the repo is not excessively large

After choosing the final candidate, create:

- `evals/roundX_<repo>/`

ALWAYS create this directory as soon as you choose the repo name.

### 3. Add the repository as a submodule

Add the repository under:

- `evals/<repo>/`

Use a normal git submodule flow. If the repo already exists under `evals/`, prefer choosing a different repo for broader eval coverage unless the user explicitly wants a repeat.

### 4. Verify repo size

After checkout, compare candidate size to `evals/repos/rundler` using the filtered source-file count:

- `rg --files evals/<repo> -g '!**/.git/**' -g '!**/node_modules/**' -g '!**/dist/**' -g '!**/build/**' -g '!**/target/**' -g '!**/vendor/**' -g '!**/third_party/**' -g '!**/coverage/**' | wc -l`

Decision rule:

- accept at or below `1.5x` Rundler
- above `1.5x`, only continue if the repo is unusually strong architecturally and still below `2x`
- above `2x`, remove it and choose another candidate

### 5. Run generate-architecture

Invoke `generate-architecture` on the repository under test.

Set the output path to:

- `evals/roundX_<repo>/architecture/`

Keep the exploration scope limited to the repository under test. Do not explore unrelated directories except:

- the target repo under `evals/<repo>/`
- the round output directory under `evals/roundX_<repo>/`
- the skill files being evaluated if and only if the user later approves improvements

### 6. Spawn a fresh subagent for review

Spawn a fresh subagent with minimal context. Do not leak your conclusions. Give it:

- the repository-under-test path
- the generated architecture output path
- the instruction to review semantic quality rather than formatting

Use a prompt equivalent to:

> You are a staff engineer with deep expertise in system architecture. Review the semantic architecture representation files for the codebase at `<repo_path>` using the generated artifacts in `<architecture_path>`. Write a report focused on semantic correctness, abstraction discipline, data ownership modeling, critical workflow coverage, unsupported claims, and missing or misleading relationships. Order findings by severity and include concrete file references where possible.

Capture the subagent's output in:

- `evals/roundX_<repo>/subagent_feedback.md`

Summarize:

- major findings
- recommended changes
- any areas the subagent judged strong
- unresolved disagreements or unknowns

### 7. Apply the feedback

Review the subagent feedback yourself and update the generated architecture artifacts as needed.

Do not blindly apply feedback. Re-check against code and evidence.

If you disagree with a subagent suggestion, keep the existing model and record the disagreement in `subagent_feedback.md`.

### 8. Reflect

Answer both questions yourself:

1. `now that you’ve done this, what would you have done differently?`
2. `what improvements should we make to the generate-architecture skill in order to improve accuracy, efficiency, and comprehensiveness in future runs on other arbitrary software?`

Write the answers to:

- `evals/roundX_<repo>/reflections.md`

### 9. Pause and ask the user

After writing the files, stop and ask:

- print both reflection answers in the assistant response
- ask exactly: `Would you like me to implement these improvements to the skill?`

Do not continue automatically.

### 10. If the user says yes

Implement the approved improvements to:

- `skills/generate-architecture/`

Update companion metadata if needed.

### 11. If the user says no

Wait for further input.

## Validation Checklist

Before pausing for user input, verify:

- the target repo exists under `evals/<repo>/`
- the round output directory exists under `evals/roundX_<repo>/`
- `architecture/` exists inside the round output directory
- `subagent_feedback.md` exists
- `reflections.md` exists
- the generated architecture artifacts are not stored inside the repo under test
- the subagent used for review was fresh for that round

## Common Mistakes To Avoid

Do not:

- store architecture outputs inside `evals/<repo>/`
- skip either the pre-filter or the post-checkout size check against Rundler
- reuse stale subagent context
- ask the subagent to rubber-stamp your conclusions
- apply subagent feedback without checking code evidence
- skip writing `reflections.md` in the round directory
- implement skill improvements before the user answers yes
