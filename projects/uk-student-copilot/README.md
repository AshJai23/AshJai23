# UK Student Copilot

A runnable, source-grounded support assistant for international students in the
UK. It helps visitors find a useful next step about student work, post-study
plans, tenancy deposits, Council Tax and suspicious payment demands.

**Status:** tested local prototype with real CPU LLM inference and real GOV.UK
source requests. Not publicly deployed, legally reviewed or operated for real
users. This is an additional user-requested project, outside the 44-project
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
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --no-access-log --limit-concurrency 8
```

Open **http://127.0.0.1:8000**. API documentation is at `/docs`. No API key or
account is needed. The first supported question downloads the pinned public
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
2. **Route:** a lexical baseline finds supported topics. A real local LLM
   proposes one of six labels by constrained next-token scoring. It may order
   tied matching topics, but cannot add an unsupported source or write advice.
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
python evaluate.py
python smoke.py --mode live --output outputs/live-smoke.json
python smoke.py --mode replay --output outputs/replay-smoke.json
# Optional front-end DOM checks; Node.js 20+:
npm install
npm test
```

`evaluate.py` requires the real local model and raises an error if it cannot run;
it never substitutes mock model results. Its 24 author-written questions are a
development smoke set, not a representative held-out benchmark. This project
uses an existing pretrained model; **no local training/fine-tuning took place**.

Actual evidence:

- [Validation log](examples/validation.txt): executed checks and their limits.
- [Routing evaluation](examples/routing-evaluation.json): raw LLM, lexical and
  guarded routes, timings, model revision and every question/result.
- [Live smoke run](examples/live-smoke.json): real source requests and local LLM
  responses through the web API, plus operational metrics.
- [Localhost HTTP smoke](examples/http-smoke.json): a real Uvicorn server and
  HTTP requests, with explicit replay sources and actual local model inference.
- [Real source snapshot](examples/source_snapshot.json): reproducible replay,
  captured with timestamps; no synthetic fallback data.
- [Initial model trial](examples/initial-small-model-evaluation.json): poor
  SmolLM2-135M results retained honestly as development evidence.

The test suite uses the saved real snapshot and explicit failure/changed-content
fixtures. DOM checks mock HTTP with the saved real smoke responses. They do not
establish visual layout, screen-reader or cross-browser correctness.

Measured on the 24 development questions: the raw small Qwen model selected the
expected topic **8/24** times, versus **24/24** for the lexical baseline and
guarded workflow. Median measured model-call time was **878 ms**, with **10.6 s**
for the first call in that evaluation (weights already cached). These questions
were used during prompt development, so these are smoke results, not held-out
accuracy. The LLM did not improve on the baseline and is not ready for unrestricted
answer generation. It remains constrained to a topic proposal. No local model
training took place; the six prompt examples are not gradient training.

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
LLM cannot add sources, so unfamiliar wording may be rejected. Reviewed hashes
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
