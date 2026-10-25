# Operating the prototype

This is a tested local application, not an operated public service. No real users,
uptime SLA, university partnership or professional support is claimed. Docker
configuration is supplied; check the validation log for whether Docker ran.

## Start and check

Use the README installation commands. Default binding is localhost. Keep the
single process: caches, rate limits and the model lock are process-local. The
Docker port is also bound to 127.0.0.1 on the host. Do not expose this prototype
directly on a public IP.

- `GET /healthz`: process status, explicit live/replay mode and whether the LLM
  is enabled/loaded. This is liveness, not a guarantee that the provider works.
- `GET /metrics`: Prometheus-style numeric counters over locally retained
  requests, source problems, latency sum and feedback. No external monitoring
  account is needed. These operational endpoints have no authentication and
  must stay private.
- Every answer gets a random support reference. A user can give that reference
  to the operator. There is no external email, ticket or message integration.
- Helpful/not-helpful feedback stores only reference plus boolean in SQLite.
  Questions, answers, IP addresses and personal identifiers are not persisted.
  A few common identifier patterns are rejected; this is not comprehensive PII
  detection. Do not enter sensitive data. Disable proxy access/body logging
  before any future deployment. LangSmith/LangChain tracing is disabled in code.

## Source failure or change

At most two of five fixed GOV.UK Content API resources are consulted per question.
Successful fetches are cached for 15 minutes; failed ones for 60 seconds. No
polling runs while the app is closed. No tight retries. The API can lag changes;
always follow its official page before acting.

The source must have its expected base path, a nonempty body, no withdrawal
notice, required anchor phrases, AND the same extracted-text SHA-256 as the
reviewed version. A changed hash withholds the summary even if anchors remain.
This deliberately reduces availability when a guide changes. It does not prove
that a reviewed summary is legally exhaustive or that the upstream is correct.

For `review_required`, compare the official page and JSON with
`examples/source_snapshot.json`. Review the summary and its scope with a
qualified content reviewer. Update code, tests and `reviewed_sources.json` only
after that review. `sources.py --capture` does NOT automatically approve new
hashes. For unavailable sources, retain official links and handoff text; do not
substitute a fabricated answer or silently use the replay fixture.

The Content API sometimes resolves a chapter to a parent guide. Council Tax's
expected base path is `/council-tax`; the visitor link still opens its student
chapter. Publisher `public_updated_at` is displayed as received; it is distinct
from retrieval time and is not treated as proof of freshness.

## Model outage or poor routing

The pinned Apache-2.0 Qwen2.5-0.5B-Instruct model runs on CPU. It proposes one
topic using constrained next-token scoring, not an open-ended chat answer. A
transparent lexical guard controls the supported topics and stops unknown
questions; the LLM may only order tied matching topics. A failed model load is
labelled `baseline_fallback`. `LLM_ENABLED=0` explicitly runs baseline mode.

Small models can route badly. The checked-in smoke evaluation compares raw LLM,
lexical baseline and guarded routing; it is not a representative held-out user
study. Do not claim this model outperforms the baseline or is legally accurate.

## Public pilot requirements

Before recruiting users: get university/student feedback; independently review
content and accessibility; choose free/approved hosting capacity and inference;
add TLS, authenticated operations access, shared rate limiting and model-load
budgets; define retention and a privacy notice; run load and recovery tests;
set source/fallback/latency alerts; review logs for sensitive data; create an
operator rota and incident contact; test backups and rollback. A deployment
alone does not establish production experience.

Rollback is a normal Git revert to a tested commit. Re-run tests and a source
smoke test before restart. SQLite and downloaded model cache are separate from
source control; no model weights or private data belong in GitHub.
