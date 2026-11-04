"""Frozen 64-case quality evaluation: untouched holdouts plus observed regressions.

Checkpoint files are actual source/model outputs, not synthetic data. No tuning is
performed by this script. Score definitions and reference limits are in the report.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
from platform_stats import peak_rss_mib
import statistics
import time
from service import build_runtime
from quality_metrics import retrieval_metrics,percentile_nearest_rank

OUT=Path('data/quality-evaluation')

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def latency(values):return {'samples':len(values),'p50_seconds':statistics.median(values) if values else None,'p95_seconds_nearest_rank':percentile_nearest_rank(values,.95)}

def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--resume',action='store_true');parser.add_argument('--contract',default='evaluation/quality_v2.json');parser.add_argument('--out',default='data/quality-evaluation');args=parser.parse_args()
    OUT=Path(args.out)
    contract_path=Path(args.contract);contract=json.loads(contract_path.read_text());contract_hash=digest(contract_path)
    assert contract_hash==contract_path.with_suffix('.sha256').read_text().split()[0]
    assert contract['corpus_sha256']==digest('data/corpus.json')
    assert contract['original_tasks_sha256']==digest('evaluation/tasks.json')
    OUT.mkdir(parents=True,exist_ok=True)
    fingerprint={p:digest(p) for p in ('bounded_agent.py','local_generate.py','retrieval.py','answer_gate.py','service.py','quality_metrics.py','evaluate_quality.py')}
    run_path=OUT/'quality-run-contract.json';journal=OUT/'quality-cases.jsonl'
    config={'evaluation_sha256':contract_hash,'code_sha256':fingerprint,'generator_max_new_tokens':80,'retrieval_modes':['bm25','dense','hybrid'],'top_k':3,'training_performed':False}
    if run_path.exists():
        if not args.resume:raise FileExistsError('Run exists; inspect evidence and use --resume without changing code/settings')
        previous=json.loads(run_path.read_text())
        assert all(previous[k]==v for k,v in config.items()),'Cannot resume with changed contract/code/settings'
    else:run_path.write_text(json.dumps({**config,'started_at_utc':datetime.now(timezone.utc).isoformat()},indent=2)+'\n')
    rows=[json.loads(line) for line in journal.read_text().splitlines()] if journal.exists() else []
    seen={row['id'] for row in rows}
    assert len(rows)==len(seen),'Duplicate checkpoint IDs'
    assert seen.issubset({task['id'] for task in contract['tasks']}),'Unknown checkpoint IDs'
    if len(rows)==len(contract['tasks']):
        print(json.dumps({'complete_checkpoint_replay':True,'new_inference_performed':False,'note':'Existing capture left unchanged; choose a new --out for fresh inference.'}))
        return
    started=time.perf_counter();runtime=build_runtime(mode='hybrid',with_generation=True)
    startup=time.perf_counter()-started
    # Use the exact Retriever owned by a separate read-only adapter for all ablations.
    # The workflow's hybrid adapter remains unchanged; no gold labels enter it.
    from retrieval import Retriever
    searcher=Retriever()
    for task in contract['tasks']:
        if task['id'] in seen:continue
        begin=time.perf_counter();rankings={}
        if task['kind']=='retrieval':
            for mode in ('bm25','dense','hybrid'):
                t=time.perf_counter();found=searcher.search(task['question'],mode=mode,kind=task['retrieval_kind'],k=3)
                rankings[mode]={'seconds':time.perf_counter()-t,'results':found,
                    'metrics':retrieval_metrics(task['relevant_ids'],[x['id'] for x in found])}
        t=time.perf_counter();response=runtime.ask(task['question'],audit=True);request_time=time.perf_counter()-t
        generation=response.pop('_development_generation',None)
        route_ok=response['plan']['route']==task['expected_route']
        if task['kind']=='retrieval':route_ok=route_ok and response['plan'].get('kind')==task['retrieval_kind']
        row={'id':task['id'],'split':task['split'],'family':task['family'],'kind':task['kind'],'question':task['question'],
             'route_correct':route_ok,'response':response,'generation':generation,'retrieval_ablation':rankings,'request_seconds':request_time,'case_seconds':time.perf_counter()-begin}
        if task['kind']=='numerical':
            value=response['answer'].get('answer')
            try:correct=value is not None and Decimal(value)==Decimal(task['reference_value'])
            except Exception:correct=False
            row['numerical_correct']=correct
        if task['kind']=='unsupported':row['abstention_correct']=response['answer']['status']=='abstained' and response['calls']==0
        if task['kind']=='retrieval':
            answer=response['answer'];gate=answer.get('draft_gate',{})
            cited=gate.get('extracts',[])
            row['extract_gate_accepted']=bool(gate.get('accepted'))
            row['silver_relevant_cited_extract']=bool(cited) and all(x['source_id'] in task['relevant_ids'] for x in cited)
            row['rubric_coverage_diagnostic']=all(term.casefold() in (answer.get('answer') or '').casefold() for term in task.get('rubric_terms',[])) if 'rubric_terms' in task else None
        with journal.open('a') as out:out.write(json.dumps(row,separators=(',',':'))+'\n');out.flush();os.fsync(out.fileno())
        rows.append(row);seen.add(task['id'])
        print(json.dumps({'case':task['id'],'completed':len(rows),'status':response['answer']['status'],'route_correct':route_ok,'generation_completed':generation is not None,'request_seconds':round(request_time,3)}),flush=True)
    retr=[r for r in rows if r['kind']=='retrieval'];numeric=[r for r in rows if r['kind']=='numerical'];unsupported=[r for r in rows if r['kind']=='unsupported']
    def route_summary(group):return {'cases':len(group),'correct':sum(r['route_correct'] for r in group),'accuracy':sum(r['route_correct'] for r in group)/len(group)}
    def retrieval_summary(group):
        result={}
        for mode in ('bm25','dense','hybrid'):
            metrics=[r['retrieval_ablation'][mode]['metrics'] for r in group]
            result[mode]={key:statistics.mean(float(m[key]) for m in metrics) for key in ('hit_at_3','recall_at_3','precision_at_3','mrr_at_3')}
            result[mode]['query_latency']=latency([r['retrieval_ablation'][mode]['seconds'] for r in group])
            result[mode]['cases']=len(group)
        return result
    index=json.loads(Path('data/retrieval/manifest.json').read_text());source=json.loads(Path('data/raw/source_manifest.json').read_text())
    generations=[r for r in rows if r['generation'] is not None]
    report={'captured_at_utc':datetime.now(timezone.utc).isoformat(),'contract':config,'authorship':contract['authorship'],'holdout_note':contract['holdout_note'],
        'completion':{'expected_cases':len(contract['tasks']),'recorded_cases':len(rows),'all_cases_recorded':len(rows)==len(contract['tasks'])},
        'routing':{split:route_summary([r for r in rows if r['split']==split]) for split in ('new_family_holdout','observed_regression')},
        'retrieval_all':retrieval_summary(retr),'retrieval_new_product_families':retrieval_summary([r for r in retr if r['split']=='new_family_holdout']),
        'retrieval_observed_contract_cases':retrieval_summary([r for r in retr if r['split']=='observed_regression']),
        'numerical':{'cases':len(numeric),'correct':sum(r['numerical_correct'] for r in numeric),'reference':'frozen independent direct SQL over deduplicated base table'},
        'unsupported':{'cases':len(unsupported),'correct_abstentions':sum(r['abstention_correct'] for r in unsupported)},
        'generation':{'samples':len(generations),'retrieval_cases':len(retr),'retrieval_extract_gate_accepted':sum(r['extract_gate_accepted'] for r in retr),
            'retrieval_silver_relevant_cited_extracts':sum(r['silver_relevant_cited_extract'] for r in retr),
            'citation_support_definition':'Verbatim extract in supplied evidence, checked by unchanged strict gate; silver relevance requires cited IDs in pre-frozen reference set. Not semantic sufficiency, independent factuality or source truth.',
            'raw_drafts_exposed_to_api':False,'pretrained_inference_not_training':True},
        'latency':{'workflow_all':latency([r['request_seconds'] for r in rows]),'workflow_with_generation':latency([r['request_seconds'] for r in generations]),'runtime_startup_seconds':startup,'note':'Sequential warm development-host calls with two CPU threads; retrieval ablations add work outside measured workflow requests. Extra Retriever is loaded for ablations, so peak memory exceeds serving-only baseline. No production SLA.'},
        'source':source,'raw_rows':runtime.source['raw_rows'],'deduplicated_rows':runtime.source['deduplicated_rows'],'index':index,
        'models':{name:json.loads((Path('models')/name/'manifest.json').read_text()) for name in ('llm','embedding')},
        'hardware':{'platform':platform.platform(),'python':platform.python_version(),'visible_cpu_count':os.cpu_count(),'cpu_model':'not exposed by workspace','torch_threads':2},
        'process_peak_rss_mib':peak_rss_mib(),
        'packages':{p:importlib.metadata.version(p) for p in ('torch','transformers','duckdb','langgraph','numpy')},
        'run_wall_seconds':time.perf_counter()-started,'original_first_route_score':'36/40 on 1 November; any repeats after fixes are regression, not unseen improvement',
        'independent_human_review':False,'n8n_execution_run':False,'weekly_release_complete':False,
        'limitations':[contract['reference_scope'],'Product query/reference terms were authored by the same AI; ranking results were not inspected before freeze and were not used for tuning.','Recall denominator includes every regex-matching description; low Recall@3 is expected for large silver sets, so Hit@3/MRR/Precision@3 also matter.','Dense/hybrid results are not assumed to beat BM25. No model weights fitted or fine-tuned.','Original observed source/safety cases are scored separately from new product/country groups.']}
    (OUT/'quality-summary.json').write_text(json.dumps(report,indent=2)+'\n')
    assert report['completion']['all_cases_recorded']
    print('QUALITY_SUMMARY='+json.dumps({k:report[k] for k in ('completion','routing','retrieval_new_product_families','numerical','unsupported','generation','latency')}),flush=True)
if __name__=='__main__':main()
