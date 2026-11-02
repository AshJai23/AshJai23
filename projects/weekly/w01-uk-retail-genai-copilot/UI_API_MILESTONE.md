# Integrated local API and interface — 2 November 2026

**Implemented and exercised, not a weekly release or public website.** W01 now has a FastAPI web workspace and the actual bounded graph, hybrid retrieval and local pretrained generator in one request path. Model answer quality still fails the development examples; raw unsupported drafts are withheld.

## Run on Linux / WSL2, Python 3.12

From this project directory, in a virtual environment:

```bash
python -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-ai.txt -r requirements-api.txt
python -m unittest discover -s tests -v
python retail.py fetch
python retail.py build --evidence-dir evidence/local
python catalogue.py
python model_store.py embedding
python model_store.py llm
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python retrieval.py build
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --no-access-log
```

Omit `fetch` when its capture already exists; it intentionally refuses silent overwrite. Run commands from the project directory, not its parent. Existing modules use Unix resource reporting: native Windows is not exercised; use WSL2. Models and raw data stay ignored by Git. No account, Hugging Face token, hosted inference or paid service is needed.

**Only after starting Uvicorn on your computer**, open http://127.0.0.1:8000/ for the interface or http://127.0.0.1:8000/docs for API docs. This loopback address is not a deployed URL and will not open on another computer. Keep the process running; Ctrl+C stops it. If port 8000 is occupied, use `--port 8001` and open that port. No public server, external messages or permanent host was provisioned.

For a deliberate lightweight baseline, set `W01_RETRIEVAL=bm25 W01_GENERATION=off` before starting Uvicorn. Health explicitly reports this mode; missing models never silently activate a substitute model or fabricated data. Default startup is hybrid plus local generation. Failed setup returns HTTP 503 with coarse diagnostics. See the terminal and setup steps; no sensitive paths are returned in HTTP errors.

## Interface and architecture

`web/index.html` and `web/app.js` provide question entry, supported examples, interpreted scope, answer status, fixed SQL facts, source evidence, citation gate, tool trace and provenance. Generated text is not allowed to replace numerical values. Unsupported generated drafts are absent from the API/UI. An internal development validator deliberately captures real drafts into dated research evidence; the API has no audit flag.

`service.py` wraps the existing finite LangGraph without changing routing rules. A request performs at most one SQL/retrieval tool call and one optional bounded generation. Three evidence records maximum, 500-character questions, 8-KiB request bodies, fixed graph recursion limit and existing 80-token generation cap. CPU inference is serialised per process; overlapping requests receive 429/Retry-After. Use a single worker for this laptop prototype. LLMs have no shell, arbitrary SQL, network or messaging tools.

`api.py` exposes:

| Route | Purpose |
| --- | --- |
| GET / | Local web workspace |
| GET /assets/app.js | Fixed source asset; no arbitrary filesystem route |
| GET /v1/health | Readiness, actual source dates/counts, retrieval and generation mode |
| POST /v1/ask | Strict JSON: `{"question":"signed_value for United Kingdom"}` |
| GET /v1/metrics | In-memory completed-status counts and last 100 request latencies |

Errors omit submitted input values. UI renders text nodes, uses a same-origin CSP, and fetches no user-specified URL. Access logging is disabled in run commands; no question history/database is configured. LangSmith/LangChain tracing is explicitly disabled for local operation. Metrics contain no raw prompts/drafts. Requests/results remain in memory during processing; no authentication, rate-limit service or public production security assessment exists. The browser's 90-second timeout does not cancel already-running inference.

## Actual source and model execution

Fresh UCI capture: **2 November 2026, 19:57:08 UTC**, HTTP 200, **45,622,418 bytes**. SHA-256 matches prior source. Source observations remain **1 December 2009–9 December 2011**. Rebuilt **1,067,371 raw / 1,033,036 deduplicated rows**, with independent Decimal raw-total reconciliation. Build: **49.978 s**, peak process RSS **385.91 MiB**. No current merchant feed or ONS context was ingested.

Attribution: Chen, D. (2012), Online Retail II, UCI, DOI 10.24432/C5CG6D, CC BY 4.0. Dataset page and licence were rechecked; exact capture/checksums are in dated evidence. Public pseudonymous customer IDs and the full workbook are not redistributed here.

Rebuilt index: **5,655 description documents + 10 project-contract paragraphs = 5,665 unique documents**, not 1,067,371 RAG documents. Corpus **2,213,419 bytes**; index **8,701,568 bytes**, 384-dimensional float32. Index build **19.270 s**, peak RSS **633.39 MiB**. Hybrid uses BM25 plus exact dense cosine reciprocal-rank fusion, k=60/top-50 candidates, then top three evidence records.

Pinned public ungated Apache-2.0 models were fetched with licence/revision checks:

- HuggingFaceTB/SmolLM2-135M-Instruct, `12fd25f77366fa6b3b4b768ec3050bf629380bac`.
- sentence-transformers/all-MiniLM-L6-v2, `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.

Safetensors, local-files-only inference, trust_remote_code=False, float32 CPU, two PyTorch threads, greedy decoding. No training or fine-tuning. Weights and full corpus/index are local ignored artifacts, not Git blobs. Dated manifests give file sizes/checksums and licences.

## Actual validation and negative results

**35 unit tests passed**, including nine new API/service contracts. JavaScript syntax and `pip check` passed. The five frozen **development integration probes** are AI-authored, not an unseen or independently reviewed quality benchmark. All five expected wiring/scope checks passed; these easy probes do not repair the first frozen 36/40 routing score. Routing code and original 40-task contract were not changed.

Three actual fresh generations ran inside the API workflow. **0/3 passed the strict answer gate**. The numeric model draft refused valid supplied evidence; the source-definition draft was misleading; the product draft invented material/durability details and reached its token cap. All were withheld. Numerical UI results remained fixed SQL; retrieved evidence remained visible. The literal-extract gate rejects unsupported wording but does not establish relevance, source truth or current applicability.

The UK signed invoice-line result was **15,986,060.3370**, covering **948,321 deduplicated lines**. A separate direct expression over the base table, not the service's metric helper/view, matched this value; country subtotals matched the overall total. This is historical signed invoice-line value, not profit or a forecast.

Measured request timings for three warm generation development probes: p50 **4.996 s**, nearest-rank p95 **6.289 s**, n=3. Startup **4.571 s** separately; peak combined process RSS **1,220.95 MiB**. This tiny sample is not a representative service p95 or laptop performance promise. A separate HTTP validation process ran concurrently, so CPU contention is possible. Linux x86_64, Python 3.12.14, nine visible CPUs, two inference threads; CPU model is not exposed. Full results/settings/tokens/drafts are saved.

A separate actual temporary Uvicorn HTTP run exercised the HTML, JavaScript, readiness and hybrid-generation question path: generation completed, draft rejected, evidence-only response. A separate explicit BM25/no-generation HTTP baseline also ran. Both servers stopped after their checks; no always-on/public service remains.

First validation attempt completed API work but failed while reading unavailable `/proc/cpuinfo` during report creation. Its log is retained. Hardware reporting was made tolerant, then validation reran without prompt/routing/model/gate tuning. Deprecation/CPU-info warnings are retained in logs, not hidden.

## Reproduce validation

After full setup:

```bash
python validate_api.py
python independent_controls.py
python smoke_http.py
python smoke_http.py --baseline
```

These scripts write dated 2 November development evidence. Use a separate output directory/review changes if repeating after publication; do not overwrite prior captures silently in Git. `independent_controls.py` reads the saved API probe before reconciling it. CI runs unit/source/frozen-regression checks and an explicit BM25/no-generation HTTP path; heavy fresh-model integration was run locally, not claimed as CI generation.

Remaining: four known route errors, full held-out retrieval/grounding evaluation, independent human review, graphical UI QA, local n8n execution, final monitoring/reproducibility and case study. W01 is **not complete**. Nine archived prototypes remain separate from the **0/3 weekly releases**.

Primary references: [UCI](https://archive.ics.uci.edu/dataset/502/online+retail+ii), [SmolLM2 model card](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct), [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/), [PyTorch CPU installation](https://pytorch.org/get-started/previous-versions/).
