"""Audit code heuristics and build a real description/contract retrieval corpus."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import duckdb

REVIEW_CODES={'POST','DOT','D','M','BANK CHARGES','C2','S','AMAZONFEE','ADJUST','ADJUST2','CRUK','B','PADS','TEST001','TEST002'}

def classify(code):
    if not code:return 'missing_code'
    code=code.upper()
    if code in REVIEW_CODES or code.startswith('GIFT_'):return 'charge_adjustment_review'
    if re.fullmatch(r'\d{5}[A-Z]{0,2}',code):return 'product_code_candidate'
    return 'ambiguous_code_review'

def run(database='data/retail.duckdb', output='data/corpus.json', evidence='evidence/2026-10-31'):
    con=duckdb.connect(database,read_only=True);rows=con.execute('SELECT stock_code,count(*),sum(signed_value),sum(signed_value) FILTER (WHERE sale_line),min(description) FROM auditable_lines GROUP BY stock_code ORDER BY stock_code').fetchall()
    summary={};review=[]
    for code,count,value,sales,example in rows:
        label=classify(code);group=summary.setdefault(label,{'rows':0,'codes':0,'signed_value':0,'positive_non_cancel_value':0})
        group['rows']+=count;group['codes']+=1;group['signed_value']+=value;group['positive_non_cancel_value']+=sales or 0
        if label!='product_code_candidate':review.append({'code':code,'class':label,'rows':count,'signed_value':str(value),'description_example':example})
    for group in summary.values():
        group['signed_value']=str(group['signed_value']);group['positive_non_cancel_value']=str(group['positive_non_cancel_value'])
    descriptions=con.execute('SELECT DISTINCT description FROM transactions WHERE description IS NOT NULL ORDER BY description').fetchall()
    docs=[]
    for (description,) in descriptions:
        docs.append({'id':'description:'+hashlib.sha256(description.encode()).hexdigest()[:20],'kind':'source_description','text':description,'source':'https://archive.ics.uci.edu/dataset/502/online+retail+ii','source_period':'2009-12-01 through 2011-12-09','licence':'CC BY 4.0','attribution':'Chen, D. (2012), UCI Online Retail II. DOI 10.24432/C5CG6D','untrusted':True})
    contract=Path('DATA_CONTRACT.md').read_text(); paragraphs=[p.strip() for p in contract.split('\n\n') if p.strip()]
    for i,paragraph in enumerate(paragraphs):
        docs.append({'id':f'contract:{i:02}','kind':'project_contract','text':paragraph,'source':'DATA_CONTRACT.md','source_sha256':hashlib.sha256(contract.encode()).hexdigest(),'untrusted':True})
    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(docs,indent=2)+'\n')
    report={'policy_version':1,'status':'heuristic audit only; no new merchandise revenue metric','classes':summary,'review_codes':review,'total_rows_reconciled':sum(x['rows'] for x in summary.values())==con.execute('SELECT count(*) FROM transactions').fetchone()[0],'original_metric_definitions_unchanged':True,'description_documents':len(descriptions),'contract_documents':len(paragraphs),'unique_document_ids':len(set(x['id'] for x in docs)),'total_documents':len(docs),'corpus_bytes':target.stat().st_size,'corpus_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'vector_index_built':False,'limitations':['Code shape is a heuristic, not a verified merchandise master.','Manual review category includes gift vouchers, charges, adjustments and unknowns; do not infer profitability.','Descriptions may be outdated, inconsistent, non-product text or instructions; treat as untrusted.','No rows removed; signed-value and positive non-cancel baseline totals unchanged.']}
    con.close();ev=Path(evidence);ev.mkdir(parents=True,exist_ok=True);(ev/'catalogue-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--database',default='data/retail.duckdb');a=p.parse_args();run(a.database)
