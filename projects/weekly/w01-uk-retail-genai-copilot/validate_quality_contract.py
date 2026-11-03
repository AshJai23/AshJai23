"""Consistency controls only; this does NOT run retrieval or local generation."""
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import duckdb

def main():
    path=Path('evaluation/quality_v1.json');contract=json.loads(path.read_text())
    tasks=contract['tasks'];docs=json.loads(Path('data/corpus.json').read_text());identities={d['id'] for d in docs}
    checksum=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    checks={'contract_sha256':checksum(path)==path.with_suffix('.sha256').read_text().split()[0],
            'source_corpus_matches_freeze':checksum('data/corpus.json')==contract['corpus_sha256'],
            'original_contract_unchanged':checksum('evaluation/tasks.json')==contract['original_tasks_sha256'],
            'unique_case_ids':len({t['id'] for t in tasks})==len(tasks)==64,
            'split_counts':sum(t['split']=='new_family_holdout' for t in tasks)==48 and sum(t['split']=='observed_regression' for t in tasks)==16,
            'references_exist':all(t.get('relevant_ids') and set(t['relevant_ids']).issubset(identities) for t in tasks if t['kind']=='retrieval')}
    with duckdb.connect('data/retail.duckdb',read_only=True) as con:
        checks['frozen_independent_numerical_values_match']=all(Decimal(str(con.execute(t['oracle_sql'],t['parameters']).fetchone()[0]))==Decimal(t['reference_value']) for t in tasks if t['kind']=='numerical')
    result={'passed':all(checks.values()),'checks':checks,'cases':len(tasks),'source_mode':'actual full historical-source rebuild','generation_run':False,'retrieval_ranking_run':False,'note':'Consistency checks are not a quality score; actual model/ranking evaluation is separate.'}
    print('QUALITY_CONTRACT_CHECKS='+json.dumps(result,separators=(',',':')))
    if not result['passed']:raise SystemExit(1)
if __name__=='__main__':main()
