"""Real-source replay/reload smoke; synthetic fixtures live only in unit tests."""
import json
import statistics
import time
from decimal import Decimal
from pathlib import Path
import duckdb
from retail import build, sha256
from metrics import query

def main():
    root=Path('data'); ev=Path('evidence')
    previous=json.loads((ev/'profile.json').read_text())
    started=time.perf_counter()
    replay=build(root/'staging/transactions.csv',root/'retail.duckdb',root/'transactions.parquet')
    compare_keys=[k for k in replay]
    checks={'raw_rows_match_official_catalogue':previous['raw_rows']==1067371,
            'reload_same_metrics':all(previous[k]==replay[k] for k in compare_keys),
            'country_subtotals_reconcile':sum(Decimal(x['signed_value']) for x in replay['country_signed_values'])==Decimal(replay['deduplicated_signed_value']),
            'python_vs_sql_raw_control':previous['independent_decimal_reconciliation_passed']}
    manifest=json.loads((ev/'source_manifest.json').read_text())
    checks['source_archive_checksum_matches']=sha256(root/'raw/online_retail_ii.zip')==manifest['sha256']
    con=duckdb.connect(); checks['parquet_row_count_matches']=con.execute('SELECT count(*) FROM read_parquet(?)',[str(root/'transactions.parquet')]).fetchone()[0]==replay['deduplicated_rows'];con.close()
    timings=[]
    for _ in range(30):
        t=time.perf_counter();query(root/'retail.duckdb','signed_value','United Kingdom');timings.append((time.perf_counter()-t)*1000)
    tasks=json.loads(Path('evaluation/tasks.json').read_text())['tasks']; oracle=[]
    with duckdb.connect(str(root/'retail.duckdb'),read_only=True) as c:
        for task in tasks:
            if task['kind']=='numerical':
                value=c.execute(task['oracle_sql'],task['parameters']).fetchone()[0]
                oracle.append({'id':task['id'],'value':str(value) if value is not None else None})
    result={'checks':checks,'passed':all(checks.values()),'source_mode':'real full-source historical replay','reload_seconds':round(time.perf_counter()-started,3),'query_timing_note':'30 local deterministic UK signed-value queries, each opens/closes read-only database; not LLM/agent latency','query_samples':30,'query_latency_ms_p50':round(statistics.median(timings),3),'query_latency_ms_p95':round(sorted(timings)[28],3),'query_latency_ms_all':[round(t,3) for t in timings],'tasks_sha256':sha256('evaluation/tasks.json'),'numerical_oracle_results':oracle,'agent_evaluation_run':False,'llm_inference_run':False,'n8n_execution_run':False}
    (ev/'real-source-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    (ev/'sample-query.json').write_text(json.dumps(query(root/'retail.duckdb','signed_value','United Kingdom'),indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':main()
