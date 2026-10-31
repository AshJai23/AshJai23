"""Download only pinned public model assets; no token or hosted inference."""
import argparse
import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SPECS = {
    'llm':('HuggingFaceTB/SmolLM2-135M-Instruct','12fd25f77366fa6b3b4b768ec3050bf629380bac'),
    'embedding':('sentence-transformers/all-MiniLM-L6-v2','1110a243fdf4706b3f48f1d95db1a4f5529b4d41'),
}
ALLOWED = {'config.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','generation_config.json','vocab.txt','model.safetensors','README.md'}

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def fetch(name, root='models'):
    model_id,rev=SPECS[name];dest=Path(root)/name;dest.mkdir(parents=True,exist_ok=True)
    url=f'https://huggingface.co/api/models/{model_id}/revision/{rev}'
    with urllib.request.urlopen(url,timeout=60) as r:meta=json.load(r)
    if meta.get('gated') or meta.get('cardData',{}).get('license')!='apache-2.0' or meta['sha']!=rev:
        raise ValueError('Model gate/licence/revision differs from verified contract')
    files=sorted(x['rfilename'] for x in meta['siblings'] if x['rfilename'] in ALLOWED)
    if not {'config.json','tokenizer.json','model.safetensors'}.issubset(files):raise ValueError('Required safetensors/tokenizer missing')
    records=[];start=time.perf_counter()
    old=json.loads((dest/'manifest.json').read_text()) if (dest/'manifest.json').exists() else None
    for name_ in files:
        target=dest/name_;source=f'https://huggingface.co/{model_id}/resolve/{rev}/{name_}'
        expected=next((x['sha256'] for x in (old or {}).get('files',[]) if x['name']==name_),None)
        if target.exists() and expected and digest(target)==expected:
            status='verified_cached'
        else:
            partial=target.with_suffix('.part')
            try:
                with urllib.request.urlopen(source,timeout=120) as r,partial.open('wb') as f:
                    if r.status!=200:raise ValueError(f'HTTP {r.status}')
                    count=0
                    while block:=r.read(1048576):
                        count+=len(block)
                        if count>400*1024*1024:raise ValueError('Asset exceeds local download bound')
                        f.write(block)
                partial.replace(target);status='downloaded'
            except Exception:
                partial.unlink(missing_ok=True);raise
        records.append({'name':name_,'bytes':target.stat().st_size,'sha256':digest(target),'url':source,'status':status})
        print(json.dumps({'model':model_id,'file':name_,'bytes':target.stat().st_size,'status':status}),flush=True)
    manifest={'model_id':model_id,'revision':rev,'licence':'apache-2.0','gated':False,'downloaded_at_utc':datetime.now(timezone.utc).isoformat(),'download_seconds':round(time.perf_counter()-start,3),'files':records,'total_bytes':sum(x['bytes'] for x in records),'training_performed':False,'trust_remote_code':False}
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',choices=list(SPECS));p.add_argument('--root',default='models');a=p.parse_args();print(json.dumps(fetch(a.model,a.root),indent=2))
