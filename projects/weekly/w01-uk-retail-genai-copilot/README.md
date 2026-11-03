# UK Retail GenAI Analytics Copilot — W01

**In progress; not a weekly release or public service.** The 5 November target is at risk because the small generator still produces no accepted retrieval answers. Nine archived prototypes remain separate from this programme's **0/3 weekly releases**.

On **3 November**, a frozen 64-case evaluation compared retrieval modes and actual local generation. For 40 AI-authored product paraphrases with noisy source-derived silver references, top-three reference hits were **dense 25/40, hybrid 17/40, BM25 3/40**. Eight new numerical answers matched independent SQL; eight observed unsupported requests abstained. **0/48 retrieval generations passed the strict answer gate** and were withheld. Do not interpret this as reliable generated-answer capability.

**[Read the quality report and reproducibility correction](QUALITY_EVALUATION.md)** · [Frozen contract/protocol](evaluation/QUALITY_PROTOCOL.md) · [Working case study](CASE_STUDY_DRAFT.md).

The original first routing result remains **36/40**. Four observed definition-versus-calculation failures were fixed using regression material; repeats now pass 40/40, not an unseen improvement. The new set has 48 product/country-family cases and 16 previously inspected regressions, reported separately. It is AI-authored, not independently human-reviewed.

## Start locally

Use Linux/WSL2 and Python 3.12 from this project directory. Existing resource reporting is Unix-specific; native Windows was not exercised.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-ai.txt -r requirements-api.txt
python -m unittest discover -s tests -v
python retail.py fetch
python retail.py build --evidence-dir data/local-evidence
python -c "import catalogue; catalogue.run(evidence='data/local-evidence')"
python model_store.py embedding
python model_store.py llm
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python retrieval.py build
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --no-access-log
```

Omit `fetch` if a capture exists; it refuses silent overwrite. Only after starting the process on your computer, open http://127.0.0.1:8000/ or http://127.0.0.1:8000/docs. These are local addresses, not deployed links. Keep the terminal running; Ctrl+C stops the server. No public or always-on host was provisioned. [API/interface runbook](UI_API_MILESTONE.md) records the previous integration milestone; its dated results remain historical.

To reproduce quality testing without changing published evidence, stop the server and run:

```bash
python validate_quality_contract.py
python run_quality_eval.py --check-only
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python run_quality_eval.py --out data/my-quality-run
# For a genuinely interrupted run only, unchanged inputs/environment:
python run_quality_eval.py --out data/my-quality-run --resume
```

Completed captures cannot be relabelled as fresh inference. The wrapper checks actual model asset hashes and environment/index identity. A source-binding mismatch must be reviewed, not bypassed by silently rewriting frozen references. Models, raw workbook, full corpus/index and local outputs stay ignored by Git.

## Actual data and scale

| Measure | Observed |
| --- | --- |
| Raw / deduplicated invoice rows | 1,067,371 / 1,033,036 |
| Exact duplicate rows removed | 34,335; an analysis policy, not proof of erroneous lines |
| Missing customer IDs retained | 235,151 deduplicated lines |
| Observation period | 1 December 2009–9 December 2011 |
| Latest source capture | 3 November 2026, HTTP 200; archive checksum unchanged |
| Indexed documents | 5,655 descriptions + 10 source-contract paragraphs |
| Corpus / vector bytes | 2,213,419 / 8,701,568 |
| Canonical workflow generation latency | n=56, p50 5.999 s, p95 7.009 s; selected development-host queries |
| Peak evaluator process RSS | 1,217.18 MiB; includes a second Retriever for ablations |

These are actual **historical UK-retailer transactions**, not current UK sales. Customer countries include locations outside the UK. Transaction rows are SQL data, not a million RAG documents. No costs, audited profit, current inventory, current demand or ONS context is available. Read [DATA_CONTRACT.md](DATA_CONTRACT.md) before interpreting invoice-line values. Missing IDs restrict customer inference; charge/adjustment codes and legitimate repeated lines complicate interpretation.

Source: Chen, D. (2012), **Online Retail II**, UCI, DOI [10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). [Official dataset](https://archive.ics.uci.edu/dataset/502/online+retail+ii). Evaluation description excerpts are attributed to this source. Raw workbooks/customer IDs and model weights are not redistributed in ordinary Git.

## Implemented safeguards and honest boundaries

Fixed read-only SQL, one-tool-call LangGraph, strict input/body limits, serial CPU inference, source/provenance display, no arbitrary URL fetching, no model-selected external actions and prompt-free in-memory metrics are implemented. Deterministic numbers cannot be rewritten by model prose. The local UI renders evidence as text; unsupported drafts are withheld.

The answer gate checks literal source spans/citation IDs, not semantic truth or sufficiency. Dense retrieval beats the more complex hybrid on this selected silver set, so complexity is not treated as proof of quality. Generation still fails the citation/extract contract. No default or model was retuned after viewing the frozen scores.

A transport-added EOF newline caused initial CI source hashes to differ. The first freeze/capture and failed CI are preserved. Corrected V2 bindings retain every task, reference and source text; canonical replay reproduces all routes, rankings, drafts and quality flags. The two captures are **one 64-case set**, not extra holdouts or projects.

**46 tests passed** locally and in corrected CI, with source/reference consistency and real HTTP smoke evidence. This is not production safety or a successful GenAI answer score. There is no training/fine-tuning, independent human review, n8n execution, graphical UI QA, Docker/Power BI execution, commercial impact or production usage claim. Current model inference is pretrained CPU generation.

Remaining: generator quality, independently reviewed semantic references, actual local n8n workflow, graphical review and final release/case-study demonstration. See [dated actual evidence](evidence/2026-11-03/), [quality report](QUALITY_EVALUATION.md), [original workflow results](AGENT_MILESTONE.md) and [initial model milestone](AI_MILESTONE.md).
