"""Development smoke only, never the frozen held-out agent evaluation."""
import json
import resource
import time
from pathlib import Path
from decimal import Decimal
from catalogue import run as audit
from local_generate import Generator
from metrics import query
from retrieval import Retriever

def main():
    ev=Path('evidence/2026-10-31');ev.mkdir(parents=True,exist_ok=True)
    retrieval=Retriever();generator=Generator();reports=[];retrieval_reports=[]
    # Development example outside the frozen contract-question families.
    question='Find ceramic storage items with a strawberry design.'
    for mode in ['bm25','dense','hybrid']:
        start=time.perf_counter();hits=retrieval.search(question,mode=mode,kind='source_description')
        retrieval_reports.append({'question':question,'mode':mode,'seconds':round(time.perf_counter()-start,3),'hits':hits,'quality_score':None,'note':'Illustrative real-source retrieval, no independently labelled relevance score.'})
    reports.append(generator.generate('Describe the retrieved item descriptions without adding features or availability claims.',retrieval_reports[-1]['hits']))
    computed=query('data/retail.duckdb','signed_value','United Kingdom')
    proof={'id':'sql:uk-signed-value','text':json.dumps(computed),'source':'read-only metrics.py over full-source warehouse','untrusted':True}
    result=generator.generate('Write a short note describing this computed aggregate, preserving its exact value and source period.',[proof])
    result['automatic_checks']={'exact_value_in_draft':computed['value'] in result['draft'],'source_citation_present':'sql:uk-signed-value' in result['citation_ids_found']}
    result['automatic_check_limits']='Literal checks only; not full factuality or independent human evaluation.'
    reports.append(result)
    audit_report=json.loads((ev/'catalogue-audit.json').read_text())
    evidence={'id':'audit:code-shape','text':'This is a heuristic audit only. Product-shaped codes are candidates, not a verified merchandise master. Charge/adjustment and ambiguous codes require review. No source rows are removed and original metric definitions are unchanged.','source':'catalogue.py audit policy v1','untrusted':True}
    reports.append(generator.generate('Explain what an analyst must check before treating item-code shape as a verified merchandise catalogue.',[evidence]))
    result={'mode':'development smoke on actual downloaded models and real-source warehouse/corpus','model_training_performed':False,'agent_implemented':False,'held_out_40_task_evaluation_run':False,'samples':reports,'retrieval_examples':retrieval_reports,'llm_generations':len(reports),'generations_with_literal_evidence_citation':sum(bool(r['citation_ids_found']) for r in reports),'citation_check_is_not_grounding_score':True,'peak_combined_process_rss_mib':round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2),'status':'unverified draft outputs, not final supported answers or launch readiness'}
    (ev/'ai-smoke.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
