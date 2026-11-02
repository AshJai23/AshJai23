"""Independent direct-SQL reconciliation of the saved API development probe.

This is run after validate_api.py. It does not call the service's metric helper or
view and does not alter model outputs or inference timings.
"""
from decimal import Decimal
import json
from pathlib import Path
import duckdb

def main():
    ev=Path('evidence/2026-11-02')
    report=json.loads((ev/'integrated-api-validation.json').read_text())
    response=next(row['response'] for row in report['responses'] if row['id']=='P01')
    # Fixed independent expression over the deduplicated base table, not the view.
    sql='SELECT sum(quantity * unit_price), count(*) FROM transactions WHERE country = ?'
    with duckdb.connect('data/retail.duckdb',read_only=True) as con:
        expected,rows=con.execute(sql,['United Kingdom']).fetchone()
        all_countries=con.execute('SELECT country,sum(quantity * unit_price) FROM transactions GROUP BY country').fetchall()
        overall=con.execute('SELECT sum(quantity * unit_price) FROM transactions').fetchone()[0]
    result={'scope':'independent direct SQL over actual historical base table; no service metric helper',
        'sql':sql,'parameters':['United Kingdom'],'population_rows':rows,
        'api_value':response['answer']['answer'],'independent_value':str(expected),
        'api_matches_independent_value':Decimal(response['answer']['answer'])==expected,
        'country_subtotals_match':sum(value for _,value in all_countries)==overall,
        'inference_report_unchanged':True}
    result['passed']=result['api_matches_independent_value'] and result['country_subtotals_match']
    (ev/'independent-sql-controls.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    if not result['passed']:raise SystemExit(1)
if __name__=='__main__':main()
