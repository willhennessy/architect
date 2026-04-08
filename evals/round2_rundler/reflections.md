# Reflections

## 1. now that you’ve done this, what would you have done differently?

I would have done three things earlier.

First, I would have compared the previous round against the current repo docs and code before copying it forward. That would have surfaced the stale README-level entry point support and the missing round-numbering convention immediately, instead of discovering them mid-run.

Second, I would have run a targeted semantic consistency pass across the generated views before asking for review. The biggest reviewer finding was not a repo misunderstanding but an internal modeling inconsistency: the ingest sequence used a forward call relationship to represent a response edge. That is the kind of issue a cheap self-check should catch before subagent review.

Third, I would have inspected the Builder transport stack earlier. The repo has a clean `TransactionSender` abstraction, and I initially let the transaction tracker absorb too much responsibility. A quick pass over `crates/builder/src/sender/` before writing the component model would have led to a cleaner first draft.

## 2. what improvements should we make to the architect-discover skill in order to improve accuracy, efficiency, and comprehensiveness in future runs on other arbitrary software?

1. Add a mandatory reply-edge consistency check for sequence views.
The skill should explicitly verify that any sequence step using `relationship_id` matches the relationship direction in the canonical model. If a step is a response path, the skill should either reference a reverse relationship that exists in the model or omit `relationship_id` entirely.

2. Add a “transport adapter” discovery heuristic.
When a component appears to submit work externally, the skill should search for `sender`, `client`, `adapter`, `transport`, or similar abstractions before assigning external submission relationships. This would reduce the tendency to over-credit trackers, orchestrators, or controllers with transport responsibilities that are actually delegated.

3. Add a source-conflict rule that compares README claims against higher-evidence docs and runtime code.
In this repo, README support claims lagged behind `docs/architecture/entry_point.md` and the runtime code. The skill should explicitly reconcile these conflicts and record when lower-evidence docs are stale.

4. Add a path-sanity check for eval output manifests.
The generated manifest inherited an incorrect repo scope path (`evals/rundler` instead of `evals/repos/rundler`). The skill should verify that in-scope and out-of-scope paths match the actual repository-under-test path supplied by the user.

5. Add a “config-gated relationship” note rule.
If a path depends on enabled namespaces, feature flags, or optional integrations, the skill should add a note or assumption marking that path as conditional. This would make control-plane and debug flows more precise without needing a separate optional-relationship schema.

6. Standardize round-number discovery directly from existing round directories.
The eval workflow should derive the next round number from existing `evals/round*` directories instead of depending on any separate bookkeeping artifact. That keeps the process simpler and removes an unnecessary synchronization point.
