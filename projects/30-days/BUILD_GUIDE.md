# How to continue this sprint

## Source of truth

Read `plan.json` for the project IDs, due dates, scopes and acceptance criteria.
Read `progress.json` before starting work. The plan begins on 24 October 2026 and
ends on 22 November 2026, using the Europe/London calendar. Planned items are not
completed projects. Each completed project must have its own runnable code and
documentation, not just a topic description or a renamed copy of another project.

## Each build

1. Refresh the repository's branch head and read any applicable repository
   instructions. Preserve existing profile graphics, projects and manual edits.
2. Implement every due, incomplete item, including a second project on the dates
   specified in the plan. Never recreate a completed ID. Recover missed work
   honestly and report a backlog when a build cannot be completed.
3. Verify current primary documentation for data sources and library APIs. Prefer
   public, free endpoints that do not need credentials. Respect provider terms and
   rate limits. No paid API, paid deployment or external messages are authorised.
4. Keep each prototype small enough to run on an ordinary laptop. Data science,
   ML, deep learning and MLOps items need meaningfully different implementations.
   Deep learning means an actual trained neural model with a baseline, not a
   neural-network placeholder or a wrapper around a hosted chat API.
5. Include code, dependencies, exact run commands, primary-source links,
   attribution, limitations and a small reproducible example. Identify refresh
   cadence and distinguish streaming, polling, replay and static snapshots.
6. For ML/DL, prevent leakage, use an appropriate chronological/grouped split,
   compare against a simple baseline, and save measured metrics. Label synthetic
   test data, weak labels and replayed samples. Never invent data or results.
7. Run meaningful tests and at least one real-data or documented replay smoke
   test. Save validation evidence. A failed live request is not a successful
   live integration; choose another suitable public source or label the replay.
8. Update `progress.json` only for items actually tested and published. Update
   the completed-project index in this folder's README and the small sprint block
   in the root profile README. Leave unrelated sections intact.
9. Commit through GitHub's normal commit history using the current base tree and
   an expected branch head. Never force-overwrite other changes. Read back the
   commit/files before reporting success. Do not print credentials or upload
   private documents. Avoid generated binaries, large models and caches.
10. Report the new project links, what ran, actual results or failures, total
    completed count and the next planned work. Do not claim the plan guarantees
    an eventual result or mark blocked projects complete.

## Repository destination

Use `AshJai23/AshJai23`, under `projects/30-days/`. Existing GitHub access and the
user's request authorise these project commits. Keep the work in this repository
rather than creating numerous empty repositories. This is a portfolio learning
sprint, not a claim of professional production deployment or user authorship
without AI assistance.
