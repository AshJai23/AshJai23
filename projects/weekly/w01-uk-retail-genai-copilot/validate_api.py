"""Actual local API + hybrid retrieval + generation, using development probes.

The audit sink records actual model outputs for these public research questions;
it does not edit prompts, answers, routing, weights or the answer gate.
"""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
from platform_stats import peak_rss_mib
import statistics
import time
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from api import create_app
from service import build_runtime
from metrics import query

EV=Path('evidence/2026-11-02')

def cpu_model():
    try:
        text=Path('/proc/cpuinfo').read_text()
    except OSError:
        return 'not exposed by this environment'
    return next((line.split(':',1)[1].strip() for line in text.splitlines() if line.startswith('model name')), 'unknown')

def main():
    started=time.perf_counter()
    runtime=build_runtime(mode='hybrid',with_generation=True)
    startup_seconds=time.perf_counter()-started
    real_generator=runtime.generator.generator
    samples=[]
    class AuditSink:
        def generate(self,q,e):
            record=real_generator.generate(q,e)
            samples.append(record)
            return record
    runtime.generator.generator=AuditSink()
    probes_path=Path('evaluation/integration_probes_2026-11-02.json')
    frozen=json.loads(probes_path.read_text());responses=[]
    with TestClient(create_app(runtime)) as client:
        health=client.get('/v1/health')
        assert health.status_code==200
        assert client.get('/').status_code==200
        assert client.get('/assets/app.js').status_code==200
        for probe in frozen['probes']:
            start=time.perf_counter()
            response=client.post('/v1/ask',json={'question':probe['question']})
            body=response.json()
            observed={key:body['plan'].get(key) for key in ('route','kind','metric','country') if key in probe}
            expected={key:probe[key] for key in observed}
            controls={'http_200':response.status_code==200,'expected_development_scope':observed==expected,
                      'tool_budget':body['calls']<=1,'raw_draft_withheld':'_development_generation' not in body and 'draft' not in body.get('generation',{})}
            if probe['route']=='metric':
                oracle=query('data/retail.duckdb',probe['metric'],probe['country'])
                controls['sql_control_matches']=body['answer']['answer']==oracle['value']
            if probe['route']=='decline':
                controls['abstained_without_tool']=body['answer']['status']=='abstained' and body['calls']==0
            responses.append({'id':probe['id'],'question':probe['question'],'checks':controls,'http_roundtrip_seconds':time.perf_counter()-start,'response':body})
        metrics=client.get('/v1/metrics').json()
    profile=json.loads((EV/'profile.json').read_text())
    capture=json.loads(Path('data/raw/source_manifest.json').read_text())
    previous=json.loads(Path('evidence/source_manifest.json').read_text())
    index=json.loads(Path('data/retrieval/manifest.json').read_text())
    source_checks={'raw_rows':profile['raw_rows']==1067371,'deduplicated_rows':profile['deduplicated_rows']==1033036,
        'decimal_reconciliation':profile['independent_decimal_reconciliation_passed'],
        'source_checksum_matches_previous':capture['sha256']==previous['sha256'],
        'all_probe_checks':all(all(row['checks'].values()) for row in responses),
        'fresh_generation_samples':len(samples)==3,
        'actual_hybrid_results':all(x['retrieval_mode']=='hybrid' for row in responses if row['response']['plan']['route']=='retrieve' for x in row['response']['evidence'])}
    times=[row['http_roundtrip_seconds'] for row in responses]
    with_generation=[row['http_roundtrip_seconds'] for row in responses if row['response']['generation']['attempted']]
    def stats(values):return {'samples':len(values),'p50_seconds':statistics.median(values),'p95_seconds_nearest_rank':sorted(values)[min(len(values)-1,__import__('math').ceil(.95*len(values))-1)]}
    report={'captured_at_utc':datetime.now(timezone.utc).isoformat(),'mode':'real full-source historical replay; fresh CPU pretrained inference, no training',
        'evaluation_provenance':frozen['provenance'],'probe_sha256':hashlib.sha256(probes_path.read_bytes()).hexdigest(),
        'checks':source_checks,'passed':all(source_checks.values()),'source':capture,'index':index,
        'raw_rows':profile['raw_rows'],'deduplicated_rows':profile['deduplicated_rows'],
        'model_manifests':{name:json.loads((Path('models')/name/'manifest.json').read_text()) for name in ('llm','embedding')},
        'startup_seconds':startup_seconds,'http_roundtrip_all_probes':stats(times),
        'http_roundtrip_generation_probes':stats(with_generation),
        'latency_note':'Tiny development smoke, not a representative p95 service benchmark. Includes ASGI request, workflow, retrieval/SQL and warm generation; startup shown separately.',
        'generation_samples':samples,'responses':responses,'in_memory_metrics':metrics,
        'hardware':{'platform':platform.platform(),'python':platform.python_version(),'cpu_count_visible':os.cpu_count(),'processor':platform.processor(),'cpu_model':cpu_model(),'torch_threads':2},
        'process_peak_rss_mib':peak_rss_mib(),
        'validation_seconds':time.perf_counter()-started,
        'packages':{name:importlib.metadata.version(name) for name in ('torch','transformers','duckdb','langgraph','fastapi','starlette','numpy')},
        'weekly_release_complete':False,'n8n_execution_run':False,'independent_human_review':False,
        'limitations':['Prior frozen routing result remains 36/40; no routing rule changes or unseen improvement claim.','Full held-out relevance/grounding evaluation is still unfinished.','Three development generations do not establish broad quality.','No LLM training/fine-tuning, current sales, public hosting or production use.']}
    (EV/'integrated-api-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'checks':source_checks,'generations':len(samples),'accepted_drafts':sum(row['response']['answer'].get('draft_gate',{}).get('accepted',False) for row in responses),'latency':report['http_roundtrip_generation_probes'],'peak_rss_mib':report['process_peak_rss_mib']}))
    if not report['passed']:raise SystemExit(1)
if __name__=='__main__':main()
