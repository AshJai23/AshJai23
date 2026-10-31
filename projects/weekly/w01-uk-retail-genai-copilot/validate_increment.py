"""Actual-source and model/index replay checks; no held-out agent score."""
import hashlib
import json
import statistics
import time
from decimal import Decimal
from pathlib import Path
import numpy as np
from metrics import query
from model_store import digest
from retrieval import Retriever

def main():
    ev=Path('evidence/2026-10-31');old=json.loads(Path('evidence/profile.json').read_text());new=json.loads((ev/'profile.json').read_text())
    audit=json.loads((ev/'catalogue-audit.json').read_text());index=json.loads((ev/'index-manifest.json').read_text())
    immutable=['raw_rows','deduplicated_rows','raw_signed_value','deduplicated_signed_value','positive_non_cancel_line_value','duplicate_rows_removed','missing_customer_rows','missing_description_rows','negative_quantity_rows','zero_price_rows','negative_price_rows','cancellation_rows','sale_line_rows','countries','distinct_stock_codes','distinct_nonempty_descriptions','date_min','date_max']
    checks={'full_source_rebuild_same_business_values':all(old[k]==new[k] for k in immutable),'new_rebuild_decimal_control':new['independent_decimal_reconciliation_passed'],'source_checksum_matches_oct30':digest('data/raw/online_retail_ii.zip')==json.loads(Path('evidence/source_manifest.json').read_text())['sha256'],'audit_rows_reconcile':sum(x['rows'] for x in audit['classes'].values())==new['deduplicated_rows'],'audit_signed_values_reconcile':sum(Decimal(x['signed_value']) for x in audit['classes'].values())==Decimal(new['deduplicated_signed_value']),'uk_signed_value_unchanged':query('data/retail.duckdb','signed_value','United Kingdom')['value']=='15986060.3370'}
    expected=Path('evaluation/tasks.sha256').read_text().split()[0];checks['frozen_40_task_contract_unchanged']=digest('evaluation/tasks.json')==expected
    models={}
    for name in ['llm','embedding']:
        m=json.loads((Path('models')/name/'manifest.json').read_text());ok=all(digest(Path('models')/name/x['name'])==x['sha256'] for x in m['files']);checks[f'{name}_asset_checksums_match']=ok;models[name]={'model_id':m['model_id'],'revision':m['revision'],'bytes':m['total_bytes']}
    retriever=Retriever();norms=np.linalg.norm(retriever.vectors,axis=1)
    checks['all_5665_vectors_finite_and_unit_normalised']=len(norms)==5665 and bool(np.isfinite(retriever.vectors).all()) and bool(np.allclose(norms,1,atol=1e-5))
    checks['distinct_corpus_ids']=len(set(x['id'] for x in retriever.docs))==len(retriever.docs)
    samples=[0,100,500,1000,2000,3000,4000,5000,5655,5664]
    replay=retriever.embedder.encode([retriever.docs[i]['text'] for i in samples]);error=float(np.max(np.abs(replay-retriever.vectors[samples])))
    checks['ten_source_embeddings_replay_within_1e_5']=error<1e-5
    timings={}
    for mode in ['bm25','dense','hybrid']:
        values=[]
        for _ in range(30):
            t=time.perf_counter();retriever.search('ceramic strawberry design storage',mode=mode,kind='source_description');values.append((time.perf_counter()-t)*1000)
        timings[mode]={'samples':30,'p50_ms':round(statistics.median(values),3),'p95_ms':round(sorted(values)[28],3),'min_ms':round(min(values),3),'max_ms':round(max(values),3)}
    smoke=json.loads((ev/'ai-smoke.json').read_text());checks['three_actual_local_generations_saved']=smoke['llm_generations']==3 and all(x['generated_tokens']>0 for x in smoke['samples'])
    result={'checks':checks,'passed':all(checks.values()),'check_count':len(checks),'real_data_mode':'same public historical archive, freshly downloaded and rebuilt 31 October; observations 2009–2011','models':models,'embedding_replay_max_abs_error':error,'latency':timings,'latency_note':'Repeated warm queries, 30 per mode, includes embedding forward pass for dense/hybrid; excludes model/index loading and LLM generation. Not independent query diversity or production concurrency.','model_quality_not_passed':'0/3 generations contained literal supplied evidence citations; numeric example added unsupported population 10,000. Full grounding evaluation has not run.','held_out_40_task_agent_evaluation_run':False,'training_performed':False,'n8n_execution_run':False}
    (ev/'increment-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':main()
