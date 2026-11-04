"""Single-process, bounded local workflow service; no external model calls."""
from collections import Counter, deque
from datetime import datetime, timezone
import json
import os
# Local-only operation even if the parent shell has tracing enabled.
os.environ["LANGSMITH_TRACING"]="false"
os.environ["LANGCHAIN_TRACING_V2"]="false"
import threading
import time
import statistics
from quality_metrics import percentile_nearest_rank
from pathlib import Path
from bounded_agent import Warehouse, LexicalEvidence, make_agent, PERIOD

class BusyError(Exception):
    pass

class RecordingGenerator:
    def __init__(self, generator):
        self.generator=generator
        self.last=None
        self.attempted=False
        self.error=None
    def generate(self, question, evidence):
        self.attempted=True
        try:
            self.last=self.generator.generate(question,evidence)
            return self.last
        except Exception as exc:
            self.error=type(exc).__name__
            raise

class Runtime:
    def __init__(self, warehouse, retrieval, generator=None, source=None, retrieval_mode='bm25'):
        self.warehouse=warehouse
        self.generator=RecordingGenerator(generator) if generator is not None else None
        self.graph=make_agent(warehouse.metric, warehouse.countries, retrieval, self.generator)
        self.source=source or {'mode':'unverified local source; inspect provenance','period':PERIOD}
        self.retrieval_mode=retrieval_mode
        self.lock=threading.Lock()
        self.stats_lock=threading.Lock()
        self.counts=Counter()
        self.latencies=deque(maxlen=100)
    def ask(self, question, *, audit=False):
        # The API validates before reaching here; direct callers have the same bounds.
        if not isinstance(question,str) or not question.strip() or len(question)>500:
            raise ValueError('Question must contain 1–500 characters')
        if not self.lock.acquire(blocking=False):
            raise BusyError('Local inference is busy; retry after the current request')
        start=time.perf_counter()
        try:
            if self.generator is not None:
                self.generator.last=None
                self.generator.attempted=False
                self.generator.error=None
            state=self.graph.invoke({'question':question},config={'recursion_limit':8})
            result={key:state[key] for key in ('plan','answer','trace','calls','evidence') if key in state}
            generated=self.generator.last if self.generator is not None else None
            result['generation']={'enabled':self.generator is not None,'attempted':self.generator.attempted if self.generator else False,'completed':generated is not None,'error':self.generator.error if self.generator else None,'training_performed':False}
            if generated is not None:
                keys=('model_id','revision','licence','input_tokens','generated_tokens','generation_seconds','settings','dtype','device','threads','training_performed')
                result['generation'].update({k:generated[k] for k in keys if k in generated})
                result['generation']['attempted']=True
            result['source']=self.source
            result['retrieval_mode']=self.retrieval_mode
            result['request_seconds']=round(time.perf_counter()-start,6)
            result['evaluation_limit']='Routing is heuristic; original first score was 36/40 and later fixes are regression-tested. Exact cited extraction is not semantic factuality or relevance validation.'
            if audit and generated is not None:
                # Deliberate development CLI evidence only, never enabled by API input.
                result['_development_generation']=generated
            with self.stats_lock:
                self.counts[state['answer']['status']]+=1
                self.latencies.append(result['request_seconds'])
            return result
        finally:
            if self.generator is not None:self.generator.last=None
            self.lock.release()
    def metrics(self):
        with self.stats_lock:
            times=sorted(self.latencies)
            return {'completed_requests':sum(self.counts.values()),'status_counts':dict(self.counts),
                    'latency_window_samples':len(times),
                    'p50_seconds':statistics.median(times) if times else None,
                    'p95_seconds':percentile_nearest_rank(times,.95),
                    'scope':'in-memory completed requests, last 100 latencies; no prompts or model drafts stored'}

ROOT=Path(__file__).resolve().parent

class RuntimeSetupError(Exception):
    def __init__(self, code, action):
        super().__init__(code)
        self.code=code
        self.action=action

def check_runtime_files(root, mode, with_generation):
    required=[('data/retail.duckdb','warehouse_missing','Run python retail.py fetch, then python retail.py build from the project folder.'),
              ('data/raw/source_manifest.json','source_manifest_missing','Fetch and build the real source; see README.md.'),
              ('data/corpus.json','corpus_missing',"Run python -c \"import catalogue; catalogue.run(evidence='data/local-evidence')\" from the project folder.")]
    if mode=='hybrid':
        required.extend([('data/retrieval/manifest.json','index_missing','Run python model_store.py embedding, then python retrieval.py build.'),
                         ('data/retrieval/vectors.npy','index_missing','Run python retrieval.py build.'),
                         ('models/embedding/manifest.json','embedding_missing','Run python model_store.py embedding.')])
    if with_generation:required.append(('models/llm/manifest.json','model_missing','Run python model_store.py llm; or explicitly start serve.py --baseline for BM25 without generation.'))
    for name,code,action in required:
        if not (Path(root)/name).is_file():raise RuntimeSetupError(code,action)

def build_runtime(mode='hybrid', with_generation=True):
    if mode not in ('bm25','hybrid'):raise ValueError('Choose bm25 or hybrid')
    check_runtime_files(ROOT,mode,with_generation)
    warehouse=Warehouse(str(ROOT/'data/retail.duckdb'))
    capture=json.loads((ROOT/'data/raw/source_manifest.json').read_text())
    import duckdb
    with duckdb.connect(warehouse.database,read_only=True) as con:
        raw=con.execute('SELECT count(*) FROM raw_transactions').fetchone()[0]
        clean,first,last=con.execute('SELECT count(*),min(invoice_date),max(invoice_date) FROM transactions').fetchone()
    source={'publisher':'UCI / Chen, D. (2012), Online Retail II, DOI 10.24432/C5CG6D',
            'licence':'CC BY 4.0','mode':'historical replay, NOT live retail polling',
            'observation_first':str(first),'observation_last':str(last),
            'raw_rows':raw,'deduplicated_rows':clean,'retrieved_at_utc':capture['retrieved_at_utc'],
            'source_sha256':capture['sha256'],'source_url':capture['source'],
            'loaded_at_utc':datetime.now(timezone.utc).isoformat()}
    if mode=='hybrid':
        from retrieval import Retriever
        retriever=Retriever(corpus=str(ROOT/'data/corpus.json'),index=str(ROOT/'data/retrieval'),model=str(ROOT/'models/embedding'))
        retrieval=lambda question,kind:retriever.search(question,mode='hybrid',kind=kind,k=3)
    else:
        retrieval=LexicalEvidence(corpus=str(ROOT/'data/corpus.json'))
    generator=None
    if with_generation:
        from local_generate import Generator
        generator=Generator(model=str(ROOT/'models/llm'))
    return Runtime(warehouse,retrieval,generator,source,mode)
