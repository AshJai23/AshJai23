"""Audit a canonical replay without editing either actual capture."""
import json
from pathlib import Path

ROOT=Path('evidence/2026-11-03')
def load_rows(path):return {row['id']:row for row in (json.loads(line) for line in Path(path).read_text().splitlines())}
def main():
    first=load_rows(ROOT/'quality-cases.jsonl');canonical=load_rows(ROOT/'canonical-replay/quality-cases.jsonl')
    if set(first)!=set(canonical) or len(first)!=64:raise ValueError('Both complete captures must contain the same 64 IDs')
    changed_routes=[];changed_rankings=[];changed_drafts=[];changed_scores=[]
    for identity,a in first.items():
        b=canonical[identity]
        if a['response']['plan']!=b['response']['plan']:changed_routes.append(identity)
        if (a.get('generation') or {}).get('draft')!=(b.get('generation') or {}).get('draft'):changed_drafts.append(identity)
        if any(a.get(key)!=b.get(key) for key in ('route_correct','numerical_correct','abstention_correct','extract_gate_accepted','silver_relevant_cited_extract')):changed_scores.append(identity)
        for mode,ranking in a['retrieval_ablation'].items():
            if [row['id'] for row in ranking['results']]!=[row['id'] for row in b['retrieval_ablation'][mode]['results']]:changed_rankings.append(identity+':'+mode)
    contract1=json.loads(Path('evaluation/quality_v1.json').read_text());contract2=json.loads(Path('evaluation/quality_v2.json').read_text())
    result={'unique_cases':64,'extra_independent_holdouts_from_replay':0,'task_objects_identical':contract1['tasks']==contract2['tasks'],
        'changed_routes':changed_routes,'changed_ranked_id_lists':changed_rankings,'changed_raw_model_drafts':changed_drafts,'changed_case_quality_flags':changed_scores,
        'note':'Actual scores/drafts are retained in both captures. Timing/memory/load timestamps may differ. Replay is not extra unique data or an independent evaluation.'}
    (ROOT/'capture-comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
