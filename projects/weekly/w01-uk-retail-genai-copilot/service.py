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
                    'p50_seconds':times[(len(times)-1)//2] if times else None,
                    'p95_seconds':times[min(len(times)-1,int(.95*len(times)))] if times else None,
                    'scope':'in-memory completed requests, last 100 latencies; no prompts or model drafts stored'}

def build_runtime(mode='hybrid', with_generation=True):
    if mode not in ('bm25','hybrid'):raise ValueError('Choose bm25 or hybrid')
    warehouse=Warehouse()
    capture=json.loads(Path('data/raw/source_manifest.json').read_text())
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
        retriever=Retriever()
        retrieval=lambda question,kind:retriever.search(question,mode='hybrid',kind=kind,k=3)
    else:
        retrieval=LexicalEvidence()
    generator=None
    if with_generation:
        from local_generate import Generator
        generator=Generator()
    return Runtime(warehouse,retrieval,generator,source,mode)
