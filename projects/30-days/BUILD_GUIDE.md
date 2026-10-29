# Superseded daily build guide

**User revision, 29 October 2026:** the daily quota and old incomplete queue are
retired. Do not build IDs 10–44 on their former dates. Read the active
[weekly plan](../weekly/plan.json), [progress](../weekly/progress.json) and
[weekly build guide](../weekly/BUILD_GUIDE.md). Preserve the nine completed daily
projects and their evidence. The original runbook below is retained as history,
not as active execution instructions.

---

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

## Repository destination — updated user instruction, 27 October 2026

The user now requests **one separate, populated repository per project**. This
supersedes the earlier single-repository preference. `REPOSITORIES.json` records
requested names; pending names must never be presented as existing repositories.
The profile repository retains the plan/progress/index and original completed
folders until extraction is published and verified. Copying a completed project
does not count as a new ID. Include UK Student Copilot separately, outside 44.

Before extraction, fetch the exact current project tree, copy all code/data/test
evidence, fix project-root commands and relative links, include source commit
provenance, run its tests and replay from the new root, publish, then read back
the complete destination tree. Do not modify unrelated repositories or create
empty repositories for future items. Keep the old URLs working. If repository
creation is unavailable, report it as blocked rather than claim completion.

## UK sectors and data truth

Pending work must follow the revised scope, `uk_sector` and `niche` in plan.json:
retail, banking, technology, councils and NHS. Preserve completed non-UK results
with accurate labels; do not relabel Dublin as UK or NASA headlines as UK tech.
Consult [UK_DATA_POLICY.md](UK_DATA_POLICY.md) for candidate primary sources.
Verify the exact dataset, licence, endpoint and returned data when building;
a successful landing page check is not a working data integration. If enough
historical data is unavailable for the required model, block the item honestly.

Every README must lead with the niche, intended user/decision, exact geography,
source, observed/released/captured dates and cadence. Distinguish near-real-time
polling, delayed observations, periodically released aggregates, historical
replay and synthetic test/training fixtures. Show source age in the interface.
NHS monthly performance data is not a live queue. Bank/retail public aggregates
are not private transactions, card purchases or store inventory.

## Website and link checks

Label GitHub source, saved HTML report, local app and public website separately.
Publish a public website URL only after deployment and a successful public smoke
test. For a local app, give its exact command/port and say that 127.0.0.1 works
on the computer running it. Test required routes and error states. Check URLs,
redirects and expected content; report outages without inventing replacement
addresses. GitHub Pages cannot run a Python API or model server. Do not deploy
paid/always-on infrastructure. Changes still use normal Git history and readback.
