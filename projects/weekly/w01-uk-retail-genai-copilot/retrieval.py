"""Local BM25/dense/hybrid retrieval over real descriptions and project contract."""
import argparse
from collections import Counter
import hashlib
import json
import math
import re
from platform_stats import peak_rss_mib
import time
from pathlib import Path
import numpy as np

def tokens(text):return re.findall(r'[a-z0-9]+',text.lower())

class Lexical:
    def __init__(self, docs):
        self.counts=[Counter(tokens(x['text'])) for x in docs]
        self.lengths=[sum(c.values()) for c in self.counts];self.average=sum(self.lengths)/max(len(docs),1)
        self.df=Counter(t for c in self.counts for t in c);self.n=len(docs)
    def score(self, question):
        scores=[]
        for count,length in zip(self.counts,self.lengths):
            s=0.
            for term in set(tokens(question)):
                freq=count[term]
                if not freq:continue
                idf=math.log(1+(self.n-self.df[term]+.5)/(self.df[term]+.5))
                s+=idf*freq*2.5/(freq+1.5*(.25+.75*length/max(self.average,1)))
            scores.append(s)
        return np.array(scores)

class Embedder:
    def __init__(self, model='models/embedding'):
        import torch
        from transformers import AutoTokenizer,AutoModel
        torch.set_num_threads(2);self.torch=torch
        self.tokenizer=AutoTokenizer.from_pretrained(model,local_files_only=True,trust_remote_code=False)
        self.model=AutoModel.from_pretrained(model,local_files_only=True,trust_remote_code=False,attn_implementation='eager').eval()
    def encode(self,texts):
        vectors=[]
        for start in range(0,len(texts),64):
            batch=self.tokenizer(texts[start:start+64],padding=True,truncation=True,max_length=128,return_tensors='pt')
            with self.torch.inference_mode():
                hidden=self.model(**batch).last_hidden_state
                mask=batch['attention_mask'].unsqueeze(-1).float()
                pooled=(hidden*mask).sum(1)/mask.sum(1).clamp(min=1e-9)
                vectors.append(self.torch.nn.functional.normalize(pooled,p=2,dim=1).cpu().numpy())
        return np.concatenate(vectors).astype('float32')

def build(corpus='data/corpus.json',out='data/retrieval',model='models/embedding'):
    started=time.perf_counter();source=Path(corpus);docs=json.loads(source.read_text());target=Path(out);target.mkdir(parents=True,exist_ok=True)
    embedder=Embedder(model);vectors=embedder.encode([x['text'] for x in docs]);np.save(target/'vectors.npy',vectors)
    manifest=json.loads((Path(model)/'manifest.json').read_text())
    meta={'corpus_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'documents':len(docs),'description_documents':sum(x['kind']=='source_description' for x in docs),'contract_documents':sum(x['kind']=='project_contract' for x in docs),'vector_shape':list(vectors.shape),'vector_bytes':(target/'vectors.npy').stat().st_size,'index_type':'exact cosine over normalised float32 vectors, plus in-memory BM25; no ANN service','model_id':manifest['model_id'],'revision':manifest['revision'],'max_tokens_per_document':128,'batch_size':64,'threads':2,'index_build_seconds':round(time.perf_counter()-started,3),'process_peak_rss_mib':peak_rss_mib(),'training_performed':False}
    (target/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n');return meta

class Retriever:
    def __init__(self,corpus='data/corpus.json',index='data/retrieval',model='models/embedding'):
        source=Path(corpus);self.docs=json.loads(source.read_text());meta=json.loads((Path(index)/'manifest.json').read_text())
        if hashlib.sha256(source.read_bytes()).hexdigest()!=meta['corpus_sha256']:raise ValueError('Corpus/index mismatch; rebuild')
        self.vectors=np.load(Path(index)/'vectors.npy',allow_pickle=False)
        if self.vectors.shape!=(len(self.docs),384):raise ValueError('Index shape mismatch')
        self.lexical=Lexical(self.docs);self.embedder=Embedder(model)
    def search(self,question,mode='hybrid',kind=None,k=3):
        if not isinstance(question,str) or not 1<=len(question)<=500:raise ValueError('Question must have 1–500 characters')
        if mode not in ['bm25','dense','hybrid']:raise ValueError('Unknown retrieval mode')
        if kind not in [None,'source_description','project_contract'] or not 1<=k<=5:raise ValueError('Invalid filter/top-k')
        ids=[i for i,d in enumerate(self.docs) if kind is None or d['kind']==kind]
        lexical=self.lexical.score(question)
        dense=self.vectors@self.embedder.encode([question])[0] if mode!='bm25' else np.zeros(len(self.docs))
        lex_rank=sorted((i for i in ids if lexical[i]>0),key=lambda i:(-lexical[i],self.docs[i]['id']))
        dense_rank=sorted(ids,key=lambda i:(-dense[i],self.docs[i]['id']))
        if mode=='bm25':rank=lex_rank;score={i:float(lexical[i]) for i in rank}
        elif mode=='dense':rank=dense_rank;score={i:float(dense[i]) for i in rank}
        else:
            score={}
            for ranking in [lex_rank[:50],dense_rank[:50]]:
                for pos,i in enumerate(ranking,1):score[i]=score.get(i,0)+1/(60+pos)
            rank=sorted(score,key=lambda i:(-score[i],self.docs[i]['id']))
        return [{**self.docs[i],'score':score[i],'retrieval_mode':mode} for i in rank[:k]]

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['build','query']);p.add_argument('--question');p.add_argument('--mode',default='hybrid',choices=['bm25','dense','hybrid']);p.add_argument('--kind',choices=['project_contract','source_description']);a=p.parse_args()
    result=build() if a.command=='build' else Retriever().search(a.question,a.mode,a.kind)
    print(json.dumps(result,indent=2))
