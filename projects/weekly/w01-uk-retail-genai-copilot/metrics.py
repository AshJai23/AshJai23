"""Deterministic read-only baseline tool, not an AI agent or LLM."""
import argparse
import json
from pathlib import Path
import duckdb

METRICS = {'line_count':'count(*)','signed_value':'sum(signed_value)','positive_non_cancel_value':'sum(signed_value) FILTER (WHERE sale_line)','missing_customer_count':'count(*) FILTER (WHERE customer_id IS NULL)'}

def query(database, metric, country=None):
    if metric not in METRICS: raise ValueError('Unsupported metric')
    if country is not None and (not isinstance(country,str) or not 1<=len(country)<=80): raise ValueError('Invalid country')
    if not Path(database).is_file(): raise FileNotFoundError(database)
    con=duckdb.connect(str(database),read_only=True)
    try:
        con.execute("SET threads=2");con.execute("SET memory_limit='256MB'")
        where=' WHERE country = ?' if country is not None else ''
        result=con.execute(f'SELECT {METRICS[metric]} FROM auditable_lines{where}',[country] if country is not None else []).fetchone()[0]
        return {'metric':metric,'country':country,'value':str(result) if result is not None else None,'source':'UCI Online Retail II, 2009–2011 historical','population':'deduplicated normalised invoice lines','sql_template':f'SELECT {METRICS[metric]} FROM auditable_lines{where}','parameters':[country] if country is not None else [],'generated_by':'deterministic SQL baseline; no LLM'}
    finally:con.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--database',default='data/retail.duckdb');p.add_argument('--metric',choices=list(METRICS),required=True);p.add_argument('--country');a=p.parse_args()
    print(json.dumps(query(a.database,a.metric,a.country),indent=2))
