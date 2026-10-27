# UK Student Copilot

## Niche and address

UK international-student support using official GOV.UK sources. Live mode checks
source content when requested and uses a cache; this is not a continuous stream.
Training used labelled synthetic routing questions, not real student records.

**No public app website is deployed.** Start `python launch.py --mode live` after
installing the dependencies below, then open **http://127.0.0.1:8000** on that same
computer. Keep the server running; check the terminal if the address does not
open. A GitHub repository link opens code, not this application.

A separate `AshJai23/uk-student-copilot` repository is requested but has not yet
been created. Existing training evidence and code are preserved here.

A runnable, source-grounded support assistant for international students in the
UK. It helps visitors find a useful next step about student work, post-study
plans, tenancy deposits, Council Tax and suspicious payment demands.

**Status:** trained local-pilot prototype with a fitted Qwen-based routing head
and real GOV.UK source requests. It passed the saved local test gate. Not publicly
deployed, independently legally reviewed or operated for real users. This is an additional user-requested project, outside the 44-project
sprint; it does not increase that sprint's completed count.

## Try it

Python **3.12** was tested. From this directory:

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt -r requirements-llm.txt
python launch.py --mode live
```

Open **http://127.0.0.1:8000**. API documentation is at `/docs`. No API key or
account is needed. The first launch downloads the pinned public
Qwen2.5-0.5B-Instruct model (about 1 GB of weights plus tokenizer), then runs
locally. Allow several minutes and at least 4 GB available RAM. Subsequent
questions reuse it. No questions are sent to Hugging Face: it supplies model
files, not inference. Do not commit the downloaded model cache.

Try these questions:

- “What changes for the Graduate visa in 2027?”
- “Can I freelance while studying?”
- “How do I protect my rental deposit?” Select Scotland to see its scope warning.
- “I received a Council Tax bill.” Select Northern Ireland to see why this card
  does not apply there.
- “A caller claiming to be the Home Office demands a fine.”

For a lightweight source-navigation mode without an LLM:

```bash
# macOS/Linux; PowerShell: $env:LLM_ENABLED="0"
LLM_ENABLED=0 python -m uvicorn app:app --host 127.0.0.1 --port 8000 --no-access-log
```

This mode is explicitly labelled `baseline`, not an LLM answer. For an offline
replay of the saved real source responses, set `DATA_MODE=replay`. Replay is
labelled in every API response and in the interface; it is not current polling.

## What the agent does

LangGraph orchestrates four bounded steps:

1. **Guard:** reject a few common personal identifier patterns. This is not a
   comprehensive privacy filter; ask general questions only.
2. **Route:** a trained 10,758-parameter classifier uses frozen Qwen language
   features to propose one of six topics. Confidence of at least 0.90 and the
   matching saved local-pilot gate allow an official topic to be selected.
   Uncertain or failed model requests use the explicit keyword fallback. The
   model cannot invent source URLs or write immigration advice.
3. **Read:** fetch up to two fixed resources from the public GOV.UK Content API.
   Cache successes for 15 minutes and failures for 60 seconds. Check source
   identity, withdrawal, required phrases and the reviewed text SHA-256.
4. **Respond:** return reviewed summaries, practical action checklists, official
   links, retrieval/publisher dates, source status, explicit mode and a university
   adviser handoff. Withhold summaries when source checks fail.

This is a bounded LLM-assisted agent, not an autonomous immigration adviser or
general free-form RAG chatbot. It does not retrieve arbitrary websites, submit
forms, send messages, access university records or decide visa eligibility.
Its answers are source cards, not unreviewed generated legal text.

The checked Graduate guidance separates applications made by 31 December 2026
from those made from 1 January 2027. Work permission is deliberately not reduced
to a universal “20-hour rule”. Housing is nation-specific. Always read the
official source and ask an adviser about individual circumstances.

## Validate and inspect evidence

```bash
python -m unittest discover -s tests -v
python train_router.py --evaluate-test
python smoke.py --mode live --output outputs/live-smoke.json
python smoke.py --mode replay --output outputs/replay-smoke.json
# Optional front-end DOM checks; Node.js 20+:
npm install
npm test
```

`train_router.py --evaluate-test` loads the published trained head and evaluates
48 held-out authored questions; it fails if the model cannot run. To reproduce
training from the fixed data, run `python train_router.py` before evaluation.
That creates a new head, selects its epoch and confidence threshold on validation
only, and records timings and hashes. Never tune on the final test results.

Training used 144 AI-authored synthetic intent examples, 36 validation examples
and 48 test examples, with paired paraphrase families kept in separate splits.
These are not real student conversations or an independent human benchmark.
Only the classification head was fitted; **the base Qwen weights were frozen**.
Official immigration guidance remains fetched content, not model training data.
See [TRAINING.md](TRAINING.md) for measured results and launch limits.

Actual evidence:

- [Training validation log](examples/training-validation.txt): 35 tests, UI
  checks, measured fitting/evaluation, live source checks and launch evidence.
- [Earlier validation log](examples/validation.txt): historical checks and limits.
- [Routing evaluation](examples/routing-evaluation.json): raw LLM, lexical and
  guarded routes, timings, model revision and every question/result.
- [Trained live smoke run](examples/trained-live-smoke.json): current trained
  router with real source requests through the web API and operational metrics.
- [Training report](examples/training-report.json) and [held-out results](examples/heldout-evaluation.json): fitted parameters, epochs, losses, baselines and individual failures.
- [Earlier prompt-model live smoke](examples/live-smoke.json): retained historical evidence from before supervised training.
- [Trained launch HTTP smoke](examples/trained-http-smoke.json): the new launch
  command starts a real server; HTTP requests use the actual trained model and
  explicitly replayed source data.
- [Earlier localhost HTTP smoke](examples/http-smoke.json): retained historical
  server check from before supervised training.
- [Real source snapshot](examples/source_snapshot.json): reproducible replay,
  captured with timestamps; no synthetic fallback data.
- [Initial model trial](examples/initial-small-model-evaluation.json): poor
  SmolLM2-135M results retained honestly as development evidence.

The test suite uses the saved real snapshot and explicit failure/changed-content
fixtures. DOM checks mock HTTP with the saved real smoke responses. They do not
establish visual layout, screen-reader or cross-browser correctness.

The trained head scored **43/48 (89.6%)** on the held-out synthetic test, versus
**40/48 (83.3%)** for the lexical baseline. At the validation-chosen threshold,
**33/34 accepted proposals were correct (97.1%)**; it covered 85% of the 40
in-scope questions and falsely accepted none of the eight out-of-scope questions.
One high-confidence error remains: a postgraduate vacation/shift question was
routed to Graduate guidance rather than work guidance. This is not proof of
performance on real student questions or of immigration/legal accuracy.

The older 24-question prompt-model development results remain in
`examples/routing-evaluation.json`; they measure the previous untrained router
and must not be compared directly with the new held-out test as a controlled
before/after experiment.

## Monitoring, feedback and support

`/healthz` reports process/model state. `/metrics` exposes numeric request,
source-failure, duration and feedback counters. Each answer has a random support
reference. Visitors can mark an answer helpful or needing work; the local SQLite
database stores only metadata and boolean feedback, not questions, answers or IP
addresses. Entries older than 30 days are pruned when another request is saved.
LangSmith/LangChain tracing is disabled. See [OPERATIONS.md](OPERATIONS.md) for
source-review steps, failure handling, rollback and public-pilot requirements.

## Docker

```bash
docker compose up --build
# Open http://127.0.0.1:8000
docker compose down
```

Runs as a non-root user with local-only published port, a model cache and a
separate telemetry volume. Docker was not available in the build environment;
this configuration is supplied but **not claimed to have been built or run**.
No cloud deployment or paid service was created.

## Limits and useful next work

Coverage is five topics, English only, and no university-specific services. The
trained classifier selects only fixed source topics, so unfamiliar wording may
be rejected or fall back to keywords. Reviewed hashes
protect against silently serving outdated summaries but can suppress useful
answers after any source change. Source checks are not a legal audit. Public
guidance may lag policy; source timestamps are displayed exactly as supplied.
The app has no production authentication, distributed rate limiting, external
alerts, durable managed backups or established support coverage. It is not
emergency support or a landlord, job-listing or visa-fraud verifier.

Before serving real users, involve international students and a university
advice/content reviewer, run accessibility and load tests, review privacy and
hosting, add TLS/private operations access and agree an incident process. Do
not claim “production users” or a production SLA from this prototype.

## Sources, licences and attribution

Contains public sector information licensed under the **Open Government Licence
v3.0**. Summaries and the app are derived work, not endorsed by the UK government.
No GOV.UK logos, Crown assets or third-party images are copied.

- [GOV.UK Content API reference](https://content-api.publishing.service.gov.uk/reference.html)
- [Reuse GOV.UK content / OGL guidance](https://www.gov.uk/help/reuse-govuk-content)
- [Graduate visa](https://www.gov.uk/graduate-visa)
- [Student visa](https://www.gov.uk/student-visa)
- [Tenancy deposit protection](https://www.gov.uk/tenancy-deposit-protection)
- [Council Tax for full-time students](https://www.gov.uk/council-tax/discounts-for-full-time-students)
- [Home Office fraud guidance](https://www.gov.uk/government/publications/frauds-tricks-and-scams/fraud-tricks-and-scams)
- [Qwen2.5-0.5B-Instruct model card, Apache-2.0](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct)
- [Initial SmolLM2-135M-Instruct trial, Apache-2.0](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct)
- [LangGraph official Graph API documentation](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [FastAPI Docker deployment documentation](https://fastapi.tiangolo.com/deployment/docker/)

Prototype created with AI assistance for Ashlin Jayakumar's learning portfolio.
