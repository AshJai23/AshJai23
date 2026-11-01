"""Finite LangGraph workflow with deterministic routing and allowlisted tools.

Not an autonomous LLM planner. The LLM may draft text, but cannot select arbitrary
tools, write SQL, mutate data, send messages or expand the graph.
"""
import argparse
import hashlib
import json
import re
from typing import TypedDict
from langgraph.graph import StateGraph,START,END
from answer_gate import check_draft

METRICS={'line_count','signed_value','positive_non_cancel_value','missing_customer_count'}
PERIOD='2009-12-01 through 2011-12-09; historical, not current sales'

class State(TypedDict,total=False):
    question:str
    plan:dict
    evidence:list
    fact:dict
    draft:str
    answer:dict
    trace:list
    calls:int

def plan_question(question,countries):
    if not isinstance(question,str) or not question.strip() or len(question)>500:
        return {'route':'decline','reason':'Question must contain 1–500 characters.'}
    q=question.casefold()
    if re.search(r'\b(drop|delete|insert|update|execute|password|secret|email|send|ignore)\b',q):
        return {'route':'decline','reason':'Only bounded read-only analysis is supported; no external actions or instruction overrides.'}
    if re.search(r'\b(today|now|current|live|tomorrow|predict|forecast|profit|costs|inventory|address|real name)\b',q):
        return {'route':'decline','reason':'Historical invoice data cannot establish current trading, future outcomes, private identity, costs or profit.'}
    patterns=[
        ('missing_customer_count',r'missing_customer_count|(?:missing|unknown|null|without).{0,35}(?:customer|ids?)'),
        ('positive_non_cancel_value',r'positive_non_cancel_value|positive[ _-]non[ _-]cancel'),
        ('signed_value',r'signed_value|signed[ _-](?:invoice[ _-])?value|net[ _-]invoice'),
        ('line_count',r'line_count|line[ _-]count|how many (?:invoice )?lines|number of (?:invoice )?lines'),
    ]
    found=[metric for metric,pattern in patterns if re.search(pattern,q)]
    if len(found)>1:
        return {'route':'decline','reason':'Choose one metric per request.'}
    if found:
        if re.search(r'\b(?:2009|2010|2011|january|february|march|april|may|june|july|august|september|october|november|december)\b',q) and not re.search(r'all historical|all dates|full period',q):
            return {'route':'decline','reason':'This first tool supports the full historical period only; date-filtered metrics are not implemented.'}
        names={x.casefold():x for x in countries}
        if 'united kingdom' in names:names.update({'uk':names['united kingdom'],'britain':names['united kingdom']})
        matches={canonical for term,canonical in names.items() if re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',q)}
        if len(matches)>1:
            return {'route':'decline','reason':'Choose one country per request.'}
        if not matches and not re.search(r'all countries|overall|global|entire|whole dataset|dataset total',q):
            return {'route':'decline','reason':'Specify a known customer country or explicitly request overall totals.'}
        return {'route':'metric','metric':found[0],'country':next(iter(matches)) if matches else None}
    if re.search(r'\b(find|search|look for|show)\b',q) and re.search(r'\b(item|items|product|products|design|mug|jar|ceramic|bag)\b',q):
        return {'route':'retrieve','kind':'source_description'}
    if re.search(r'\b(source|dataset|country|invoice|customer|duplicate|timezone|timestamp|fields|quantity|price|cancellation|signed)\b',q):
        return {'route':'retrieve','kind':'project_contract'}
    return {'route':'decline','reason':'Unsupported or ambiguous question. Choose a supported metric or source/product lookup.'}

def make_agent(metric_tool,countries,retrieval_tool=None,generator=None):
    def route(state):
        return {'plan':plan_question(state['question'],countries),'trace':['route'],'calls':0,'evidence':[]}
    def tool(state):
        plan=state['plan']
        if state.get('calls',0)>=1:raise ValueError('Tool-call budget exceeded')
        try:
            if plan['route']=='metric':
                if plan['metric'] not in METRICS:raise ValueError('Metric not allowed')
                fact=metric_tool(plan['metric'],plan['country'])
                identity='sql:'+hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()[:16]
                evidence=[{'id':identity,'text':json.dumps(fact,sort_keys=True),'source':'metrics.py read-only aggregate','period':PERIOD}]
                return {'fact':fact,'evidence':evidence,'calls':1,'trace':state['trace']+['read_only_metric']}
            if retrieval_tool is None:raise RuntimeError('Retrieval unavailable')
            evidence=retrieval_tool(state['question'],plan['kind'])
            if not isinstance(evidence,list) or not 1<=len(evidence)<=3:raise ValueError('Evidence budget/shape')
            if any(not isinstance(x,dict) or not isinstance(x.get('id'),str) or not isinstance(x.get('text'),str) for x in evidence):raise ValueError('Malformed evidence')
            return {'evidence':evidence,'calls':1,'trace':state['trace']+['retrieve']}
        except Exception as exc:
            return {'plan':{'route':'decline','reason':'Source/tool unavailable; no fabricated fallback.'},'evidence':[],'calls':1,'trace':state['trace']+['tool_error:'+type(exc).__name__]}
    def compose(state):
        if state['plan']['route']=='decline':
            return {'answer':{'status':'abstained','answer':None,'reason':state['plan']['reason'],'period':PERIOD},'trace':state['trace']+['abstain']}
        draft=''
        if generator is not None:
            try:
                result=generator.generate(state['question'],state['evidence'])
                draft=result['draft']
            except Exception:
                draft=''
        gate=check_draft(draft,state['evidence'])
        if state['plan']['route']=='metric':
            fact=state['fact']
            if fact.get('value') is None:
                answer={'status':'no_matching_value','answer':None,'fact':fact,'period':PERIOD}
            else:
                answer={'status':'deterministic_calculation','answer':str(fact['value']),'fact':fact,
                        'citations':[x['id'] for x in state['evidence']],'period':PERIOD,
                        'generated_by':'fixed SQL, not LLM','limitation':'Invoice-line value is not profit; customer-country filter, exact-deduplication policy.'}
        elif gate['accepted']:
            answer={'status':'supported_extract','answer':gate['answer'],'extracts':gate['extracts'],'period':PERIOD,'limitation':gate['limitation']}
        else:
            answer={'status':'evidence_only','answer':None,'evidence':state['evidence'],'period':PERIOD,
                    'reason':'No validated generated answer. Review source evidence directly.',
                    'generated_by':'retrieval results, not generated prose'}
        answer['draft_gate']=gate
        return {'answer':answer,'trace':state['trace']+['compose_and_gate']}
    graph=StateGraph(State);graph.add_node('route',route);graph.add_node('tool',tool);graph.add_node('compose',compose)
    graph.add_edge(START,'route')
    graph.add_conditional_edges('route',lambda s:'compose' if s['plan']['route']=='decline' else 'tool',{'compose':'compose','tool':'tool'})
    graph.add_edge('tool','compose');graph.add_edge('compose',END)
    return graph.compile()

class Warehouse:
    def __init__(self,database='data/retail.duckdb'):
        import duckdb
        from metrics import query
        self.database=database;self.query=query
        with duckdb.connect(database,read_only=True) as con:
            self.countries=[x[0] for x in con.execute('SELECT DISTINCT country FROM transactions WHERE country IS NOT NULL').fetchall()]
    def metric(self,metric,country):return self.query(self.database,metric,country)

class LexicalEvidence:
    """Explicit BM25-only adapter; dense/hybrid adapter remains available separately."""
    def __init__(self,corpus='data/corpus.json'):
        from retrieval import Lexical
        with open(corpus) as f:self.docs=json.load(f)
        self.index=Lexical(self.docs)
    def __call__(self,question,kind):
        scores=self.index.score(question)
        ids=[i for i,x in enumerate(self.docs) if x['kind']==kind and scores[i]>0]
        ids.sort(key=lambda i:(-scores[i],self.docs[i]['id']))
        return [{**self.docs[i],'retrieval_mode':'bm25','score':float(scores[i])} for i in ids[:3]]

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--question',required=True);p.add_argument('--with-local-model',action='store_true');a=p.parse_args()
    warehouse=Warehouse();generator=None
    if a.with_local_model:
        from local_generate import Generator
        generator=Generator()
    agent=make_agent(warehouse.metric,warehouse.countries,LexicalEvidence(),generator)
    print(json.dumps(agent.invoke({'question':a.question},config={'recursion_limit':8}),indent=2))
