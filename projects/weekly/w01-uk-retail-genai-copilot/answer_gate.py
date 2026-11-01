"""Strict extract-only gate. Passing is not general semantic factuality."""
import re

def check_draft(draft, evidence):
    if not isinstance(draft,str) or not draft.strip():
        return {'accepted':False,'reason':'empty_draft','answer':None}
    if len(draft)>4000:
        return {'accepted':False,'reason':'draft_budget','answer':None}
    if not isinstance(evidence,list) or not 1<=len(evidence)<=3:
        return {'accepted':False,'reason':'invalid_evidence','answer':None}
    sources={}
    for row in evidence:
        if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not isinstance(row.get('text'),str):
            return {'accepted':False,'reason':'invalid_evidence','answer':None}
        if row['id'] in sources:
            return {'accepted':False,'reason':'duplicate_evidence_id','answer':None}
        sources[row['id']]=row['text']
    extracts=[]
    for line in draft.strip().splitlines():
        if not line.strip():continue
        match=re.fullmatch(r'\[([A-Za-z0-9:_-]+)\] (.{12,700})',line.strip())
        if not match:
            return {'accepted':False,'reason':'citation_or_extract_format','answer':None}
        identity,quote=match.groups()
        if identity not in sources:
            return {'accepted':False,'reason':'unknown_citation','answer':None}
        if quote not in sources[identity]:
            return {'accepted':False,'reason':'unsupported_span','answer':None}
        extracts.append({'source_id':identity,'quote':quote})
    if not extracts:
        return {'accepted':False,'reason':'no_extracts','answer':None}
    return {'accepted':True,'reason':'verbatim_cited_extracts_only','answer':draft.strip(),
            'extracts':extracts,'limitation':'Literal source support only; sources may be stale or wrong. No free-form semantic factuality claim.'}
