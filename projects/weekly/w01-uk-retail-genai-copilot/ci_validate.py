"""CI validation: real UCI source, explicit replay of prior LLM failures."""
import contextlib
from decimal import Decimal
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import resource
import subprocess
import sys
import time

def run():
    started=time.perf_counter()
    unit=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],capture_output=True,text=True)
    output=unit.stdout+unit.stderr
    match=re.search(r'Ran (\d+) tests?',output)
    report={'date':datetime.now(timezone.utc).date().isoformat(),'reported_at_utc':datetime.now(timezone.utc).isoformat(),'source_commit':os.environ.get('GITHUB_SHA'),'run_id':os.environ.get('GITHUB_RUN_ID'),
            'runner':'GitHub standard ubuntu-24.04; public repository','python':sys.version,'platform':platform.platform(),
            'unit_tests_passed':unit.returncode==0,'unit_test_count':int(match.group(1)) if match else None,
            'unit_test_output':output,'fresh_model_inference_run':False,'training_performed':False,'n8n_execution_run':False,
            'full_held_out_rag_quality_evaluation_run':False}
    if unit.returncode:
        report['passed']=False
        print('W01_EVIDENCE_JSON='+json.dumps(report,separators=(',',':')),flush=True)
        raise SystemExit(1)
    for command in ['fetch','build']:
        result=subprocess.run([sys.executable,'retail.py',command],capture_output=True,text=True)
        if result.returncode:
            report.update({'passed':False,'blocked_stage':command,'source_error':(result.stdout+result.stderr)[-6000:]})
            print('W01_EVIDENCE_JSON='+json.dumps(report,separators=(',',':')),flush=True);raise SystemExit(1)
    from catalogue import run as catalogue
    with contextlib.redirect_stdout(io.StringIO()):
        audit=catalogue(evidence='ci-evidence')
    from answer_gate import check_draft
    from bounded_agent import Warehouse,LexicalEvidence,make_agent
    import duckdb
    warehouse=Warehouse();agent=make_agent(warehouse.metric,warehouse.countries,LexicalEvidence())
    tasks_path=Path('evaluation/tasks.json');expected_hash=Path('evaluation/tasks.sha256').read_text().split()[0]
    tasks=json.loads(tasks_path.read_text())['tasks']
    profile=json.loads(Path('evidence/profile.json').read_text())
    new=json.loads(Path('evidence/profile.json').read_text())
    # Independent reference: profile from immutable published source commit.
    prior=json.loads(Path('evidence/2026-10-31/profile.json').read_text())
    checks={'source_rows':profile['raw_rows']==1067371,'deduplicated_rows':profile['deduplicated_rows']==1033036,
            'decimal_control':profile['independent_decimal_reconciliation_passed'],
            'prior_business_totals_unchanged':all(profile[k]==prior[k] for k in ['raw_rows','deduplicated_rows','deduplicated_signed_value','positive_non_cancel_line_value','missing_customer_rows']),
            'frozen_tasks_sha256':hashlib.sha256(tasks_path.read_bytes()).hexdigest()==expected_hash,
            'audit_reconciles':audit['total_rows_reconciled']}
    manifest=json.loads(Path('data/raw/source_manifest.json').read_text())
    checks['source_checksum_matches_previous_capture']=manifest['sha256']==json.loads(Path('evidence/2026-10-31/source_manifest.json').read_text())['sha256']
    replay=json.loads(Path('evidence/2026-10-31/ai-smoke.json').read_text())['samples']
    gates=[{'sample':i+1,**check_draft(x['draft'],x['evidence'])} for i,x in enumerate(replay)]
    checks['previous_bad_drafts_all_rejected']=len(gates)==3 and all(not x['accepted'] for x in gates)
    cases=[];times=[]
    expected_routes={'read_only_metric_query':'metric','retrieve_source_contract':'retrieve','decline_or_explain_limitation':'decline'}
    with duckdb.connect('data/retail.duckdb',read_only=True) as con:
        for task in tasks:
            begin=time.perf_counter()
            result=agent.invoke({'question':task['question']},config={'recursion_limit':8})
            times.append((time.perf_counter()-begin)*1000)
            row={'id':task['id'],'kind':task['kind'],'expected_route':expected_routes[task['expected_tool']],
                 'actual_route':result['plan']['route'],'status':result['answer']['status'],'tool_calls':result['calls'],
                 'route_correct':result['plan']['route']==expected_routes[task['expected_tool']],'trace':result['trace']}
            if task['kind']=='numerical':
                value=con.execute(task['oracle_sql'],task['parameters']).fetchone()[0]
                actual=result['answer'].get('fact',{}).get('value')
                row.update({'expected_value':str(value) if value is not None else None,'actual_value':actual,
                            'numeric_correct':actual is not None and value is not None and Decimal(actual)==Decimal(str(value))})
            cases.append(row)
    numeric=[x for x in cases if x['kind']=='numerical']
    report.update({'passed':all(checks.values()),'source_checks':checks,'source_manifest':manifest,
                   'raw_rows':profile['raw_rows'],'deduplicated_rows':profile['deduplicated_rows'],
                   'corpus_documents':audit['total_documents'],'task_contract_sha256':expected_hash,
                   'cases':cases,'route_correct':sum(x['route_correct'] for x in cases),'route_total':len(cases),
                   'numeric_correct':sum(x['numeric_correct'] for x in numeric),'numeric_total':len(numeric),
                   'evaluation_scope':'Frozen 40-case deterministic routing regression and 24-case SQL oracle comparison; first measured result preserved in 1 November evidence; not a full generated-answer/retrieval-grounding score. AI-authored synthetic questions, no independent human validation.',
                   'routing_policy':'Deterministic allowlist inside LangGraph, not LLM autonomous planning.',
                   'bad_llm_draft_replay':gates,'replay_capture_date':'2026-10-31','replay_note':'Actual previous local generations replayed; no fresh LLM weights loaded in this CI run.',
                   'latency_ms':{'samples':len(times),'p50':round(sorted(times)[len(times)//2],3),'p95':round(sorted(times)[int(len(times)*.95)-1],3),'all':[round(x,3) for x in times]},
                   'latency_note':'Mixed deterministic routes, SQL and BM25; no model load or generation. CI runner, not laptop end-to-end LLM latency.',
                   'total_seconds':round(time.perf_counter()-started,3),'process_peak_rss_mib':round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2)})
    import importlib.metadata
    report['versions']={x:importlib.metadata.version(x) for x in ['langgraph','duckdb','numpy','openpyxl']}
    print('W01_EVIDENCE_JSON='+json.dumps(report,separators=(',',':')),flush=True)
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':run()

