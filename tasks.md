# Tasks

This file tracks the high-level tasks requested so far in chronological order. Completed tasks are marked done.

- [x] Write a thorough training document explaining how to operate as a senior software architect, including the architect role, core principles, tools and standards, architecture design timing, architecture change cadence, architecture change review process, and the C4 model.
- [x] Write the architecture training document to `architecture_training.md`.
- [x] Create a handbook for C4 diagrams in `c4_handbook.md`.
- [x] Create a handbook for reviewing PRs that change architecture in `architecture_pr_review_handbook.md`.
- [x] Describe the process for exploring a codebase for the first time, identifying key architectural components, and producing structured architecture diagrams for different audiences, including the modeling style selection and reasoning.
- [x] Turn the architecture discovery process into an explicit reusable agent skill that can inspect a codebase and emit structured text files representing architecture diagrams.
- [x] Create `tasks.md` and maintain a chronological list of high-level tasks, marking completed tasks as done.
- [x] Explain why YAML was chosen as the file format for the structured architecture diagram specs.
- [x] Research Structurizr using the official site and GitHub repositories, then write `structurizr.md` summarizing how it works, strengths, customer appeal, shortcomings, and actionable takeaways for our project.
- [x] Add a comparison section at the end of `structurizr.md` contrasting Structurizr with our current YAML-based architecture artifact approach, without replacing the existing content.
- [x] Revise the architecture-generation skill based on feedback by hardening the ontology and output contract, adding a canonical model plus derived views, update/diff mode, repo-archetype branching, stricter C4 rules, stronger data ownership fields, and saving the key lessons to memory.
- [x] Explain whether the saved architecture-skill lessons belong in `AGENTS.md` or should remain in memory and skill-specific files.
- [x] Create `AGENTS.md` with the durable repo-wide subset of the architecture-artifact lessons.
