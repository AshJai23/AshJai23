# Local retrieval and generation milestone — 31 October 2026

**In progress, not a launched copilot.** This increment adds an auditable item-code
review, actual public-model downloads, a real description index, three retrieval
modes and actual CPU generation. A tool-selecting LangGraph agent, answer-quality
gate, full held-out evaluation, interface/API and n8n execution remain unfinished.

## Reproduce

From this directory in a clean Python 3.12 virtual environment:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-ai.txt
python -m unittest discover -s tests -v
python retail.py fetch
python retail.py build
python catalogue.py
python model_store.py embedding
python model_store.py llm
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python retrieval.py build
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python smoke_ai.py
python retrieval.py query --question 'Find ceramic storage items with a strawberry design.' --kind source_description --mode hybrid
python local_generate.py --question 'Describe how the data fields support an audit trail.'
python validate_increment.py
```

If the source capture already exists, omit `fetch`; it intentionally refuses
silent overwrites. Rebuilding the database does not append duplicate rows.
`catalogue.py` expects execution from this directory so it can read the versioned
DATA_CONTRACT.md. Do not edit that contract without rebuilding the corpus/index.
Index hashes detect accidental corpus changes. Model directories and vectors are
local ignored outputs; do not push weights or the full corpus into ordinary Git.
Budget at least 2 GB free disk/RAM for models/dependencies/runtime in addition to
data. This is a laptop prototype, not a large-model training job or hosted service.

No Hugging Face login/token, hosted inference bill or credentials are required.
Downloads use immutable revisions and write file sizes/SHA-256 into manifests.
Inference uses local files only, safetensors and `trust_remote_code=False`.
The model cards/licences were checked on 31 October, not assumed from a model name.

## Models and scale

| Component | Model / pinned revision | Role |
|---|---|---|
| Local generation | [HuggingFaceTB/SmolLM2-135M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct), `12fd25f77366fa6b3b4b768ec3050bf629380bac` | Small CPU text-generation smoke; Apache 2.0 |
| Embeddings | [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | 384-dimensional text vectors; Apache 2.0 |

Embedding inference uses Hugging Face Transformers with attention-mask mean
pooling and L2 normalisation, following the model card; the Sentence Transformers
Python package itself is not required or claimed as executed. Generation uses
float32, greedy decoding, two CPU threads, no quantisation and at most 120 new
tokens. These pretrained weights were **not trained or fine-tuned by this project**.

The index contains 5,665 distinct document IDs: 5,655 observed descriptions and
10 project-contract paragraphs. Its float32 matrix is 5,665 × 384 (8,701,568 bytes
on disk including the NumPy header). Corpus text/metadata is 2,213,419 bytes.
Batch size 64, maximum 128 tokens per document; longer passages are truncated.
That can omit relevant details and must be included in later retrieval evaluation.
Build took 17.945 s with peak process RSS 718.09 MiB in the recorded environment.

BM25 uses in-memory term frequencies; dense retrieval uses exact cosine search,
and hybrid retrieval uses reciprocal-rank fusion (k=60) over the top 50 of each.
This small corpus does not require an ANN/vector server. SQL invoice rows remain
in the warehouse and are not presented as millions of retrieval documents.

## Product/charge review

`catalogue.py` applies a transparent heuristic, not a verified merchandise master.
It classifies 1,027,056 rows as product-code candidates, 5,818 as charge/adjustment
review and 162 as ambiguous-code review. Some unknown-shaped codes are genuine
goods. There is no new merchandise-only revenue KPI and no source row is dropped.
All three groups reconcile to the deduplicated invoice population and signed
value. The original signed-value/positive-non-cancel metrics are unchanged.
See [audit evidence](evidence/2026-10-31/catalogue-audit.json) for every review code.

## Evidence and limits

The eight previous ingestion tests plus six new retrieval/policy tests ran.
Real-source checks and model outputs are in [dated evidence](evidence/2026-10-31/).
The new source download is byte-identical to the 30 October archive, while the
underlying transaction dates remain **2009–2011**, not current UK shop activity.

The generation smoke uses three development examples and saves full prompts'
evidence, drafts, token counts, settings, runtime and citation presence. It does
not run or tune against the frozen 40 held-out tasks. Literal citation/number
presence is a diagnostic, **not** proof an answer is factual or supported.
Generated drafts are explicitly unverified and must not become customer-facing
answers. Retrieved descriptions are untrusted text, not executable instructions.
This prototype cannot execute an LLM-generated action: generation has no tools.

A small model may omit citations, invent details or mishandle a decimal total.
Those failures belong in the saved evidence; no prompt changes should be made
to hide them. Next implement bounded routing, deterministic fact presentation
and an answer-quality/abstention gate, then run group-separated evaluation and
measure genuine end-to-end latency. No production users, deployment, Docker,
n8n execution, model training or independent human evaluation is claimed here.

### Observed negative generation result

All three actual drafts omitted the supplied evidence citation IDs. The numeric
draft preserved the exact SQL total but added an unsupported population of 10,000.
The code-shape explanation echoed the prompt, changed an evidence ID and was
truncated at the token budget. The product description draft also hit the budget.
These are saved as failures, not silently corrected examples. Literal citation
presence was 0/3; this small diagnostic is not a statistical grounding benchmark.
Generation times were 5.358, 4.803 and 5.398 seconds for 80, 69 and 80 tokens.
The model has 134,515,008 parameters. Peak combined process RSS with both models
loaded was 1,261.2 MiB. These timings do not include initial model loading.

There is no automatic supported-answer endpoint in this increment. Even a future
literal citation check alone cannot prevent invented non-numeric claims. Use the
deterministic SQL result separately while developing and testing stricter gates.

The dated warehouse profile and catalogue audit were captured before the model/index
stage. Their zero-index/no-inference fields describe those individual stages;
index-manifest.json, ai-smoke.json and increment-validation.json record the later
actual model work. Source observations remain historical at every stage.
