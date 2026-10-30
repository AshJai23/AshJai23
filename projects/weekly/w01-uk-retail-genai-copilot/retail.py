"""Auditable historical retail ingestion. No LLM or live-sales claims."""
import argparse
import csv
import hashlib
import json
import os
import platform
import resource
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import duckdb
import openpyxl

URL = 'https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip'
SOURCE = 'https://archive.ics.uci.edu/dataset/502/online+retail+ii'
FIELDS = ['invoice','stock_code','description','quantity','invoice_date','unit_price','customer_id','country']
TYPES = {'invoice':'VARCHAR','stock_code':'VARCHAR','description':'VARCHAR','quantity':'BIGINT','invoice_date':'TIMESTAMP','unit_price':'DECIMAL(18,4)','customer_id':'VARCHAR','country':'VARCHAR'}

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def download(root):
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    target = root/'online_retail_ii.zip'
    if target.exists():
        raise FileExistsError('Download already exists; use existing file or remove explicitly to refresh')
    partial = target.with_suffix('.part'); started = time.perf_counter()
    try:
        with urllib.request.urlopen(urllib.request.Request(URL,headers={'User-Agent':'UKRetailPortfolio/0.1 public-research'}),timeout=120) as r, partial.open('wb') as out:
            status = r.status; headers = dict(r.headers)
            if status != 200: raise ValueError(f'HTTP {status}')
            total = 0
            while block := r.read(1024*1024):
                total += len(block)
                if total > 150*1024*1024: raise ValueError('Download exceeds 150 MiB bound')
                out.write(block)
        with zipfile.ZipFile(partial) as z:
            if z.testzip() is not None: raise ValueError('Corrupt archive')
        partial.rename(target)
    except Exception:
        partial.unlink(missing_ok=True); raise
    manifest = {'source':SOURCE,'download_url':URL,'mode':'historical actual transactions; not live','retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'http_status':status,'bytes':target.stat().st_size,'sha256':sha256(target),'download_seconds':round(time.perf_counter()-started,3),'last_modified':headers.get('Last-Modified'),'licence':'CC BY 4.0','attribution':'Chen, D. (2012). Online Retail II. UCI. https://doi.org/10.24432/C5CG6D'}
    (root/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

def normalise(row):
    if len(row) != 8: raise ValueError('Expected eight source fields')
    invoice,stock,desc,qty,date,price,customer,country = row
    if not isinstance(date,datetime): raise ValueError('Missing or invalid invoice datetime')
    q = Decimal(str(qty)); pr = Decimal(str(price))
    if not q.is_finite() or q != q.to_integral_value(): raise ValueError('Non-integral quantity')
    if not pr.is_finite() or pr != pr.quantize(Decimal('.0001')): raise ValueError('Invalid price precision')
    text = lambda x: '' if x is None else str(x).strip()
    cust = '' if customer is None else str(int(customer)) if isinstance(customer,(float,int)) else str(customer).strip()
    return [text(invoice),text(stock),text(desc),int(q),date.isoformat(sep=' '),str(pr),cust,text(country)]

def workbook_to_csv(archive, output):
    """Bounded-memory workbook stream; retain both sheets and audit their overlap."""
    output = Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        members = [n for n in z.namelist() if n.endswith('.xlsx')]
        if len(members) != 1: raise ValueError('Expected one workbook')
        # Extract fixed filename only, never archive-supplied paths.
        workbook = output.parent/'source.xlsx'
        with z.open(members[0]) as src, workbook.open('wb') as dst:
            while block := src.read(1024*1024): dst.write(block)
    wb = openpyxl.load_workbook(workbook,read_only=True,data_only=True)
    sheets = {}; control = Decimal(0); count = 0
    try:
        with output.open('w',newline='',encoding='utf-8') as f:
            writer = csv.writer(f); writer.writerow(FIELDS)
            for ws in wb.worksheets:
                rows = ws.iter_rows(values_only=True); header = next(rows)
                if tuple(header) != ('Invoice','StockCode','Description','Quantity','InvoiceDate','Price','Customer ID','Country'):
                    raise ValueError(f'Unexpected schema: {header}')
                n = 0
                for row in rows:
                    values = normalise(row); writer.writerow(values)
                    control += Decimal(values[3])*Decimal(values[5]); n += 1
                sheets[ws.title] = n; count += n
                print(json.dumps({'sheet':ws.title,'rows':n}),flush=True)
    finally:
        wb.close()
    return {'sheet_rows':sheets,'raw_rows':count,'python_decimal_raw_signed_value':str(control)}

def build(csv_path, db_path, parquet_path):
    db_path = Path(db_path); db_path.parent.mkdir(parents=True,exist_ok=True)
    con = duckdb.connect(str(db_path)); con.execute("SET threads=2"); con.execute("SET memory_limit='512MB'")
    try:
        con.register('incoming',con.read_csv(str(csv_path),header=True,columns=TYPES))
        con.execute('BEGIN')
        con.execute('CREATE OR REPLACE TABLE raw_transactions AS SELECT * FROM incoming')
        con.execute('CREATE OR REPLACE TABLE transactions AS SELECT DISTINCT * FROM raw_transactions')
        con.execute("CREATE OR REPLACE VIEW auditable_lines AS SELECT *, quantity*unit_price AS signed_value, starts_with(upper(invoice),'C') AS cancellation, quantity>0 AND unit_price>0 AND NOT starts_with(upper(invoice),'C') AND invoice IS NOT NULL AND stock_code IS NOT NULL AS sale_line FROM transactions")
        con.execute('COMMIT')
        con.execute('COPY transactions TO ? (FORMAT PARQUET, COMPRESSION ZSTD)',[str(parquet_path)])
        def scalar(sql): return con.execute(sql).fetchone()[0]
        report = {'raw_rows':scalar('SELECT count(*) FROM raw_transactions'),'deduplicated_rows':scalar('SELECT count(*) FROM transactions'),'raw_signed_value':str(scalar('SELECT sum(quantity*unit_price) FROM raw_transactions')),'date_min':str(scalar('SELECT min(invoice_date) FROM transactions')),'date_max':str(scalar('SELECT max(invoice_date) FROM transactions')),'missing_customer_rows':scalar('SELECT count(*) FROM transactions WHERE customer_id IS NULL'),'missing_description_rows':scalar('SELECT count(*) FROM transactions WHERE description IS NULL'),'negative_quantity_rows':scalar('SELECT count(*) FROM transactions WHERE quantity<0'),'zero_price_rows':scalar('SELECT count(*) FROM transactions WHERE unit_price=0'),'negative_price_rows':scalar('SELECT count(*) FROM transactions WHERE unit_price<0'),'cancellation_rows':scalar('SELECT count(*) FROM auditable_lines WHERE cancellation'),'sale_line_rows':scalar('SELECT count(*) FROM auditable_lines WHERE sale_line'),'countries':scalar('SELECT count(DISTINCT country) FROM transactions'),'distinct_stock_codes':scalar('SELECT count(DISTINCT stock_code) FROM transactions'),'distinct_nonempty_descriptions':scalar('SELECT count(DISTINCT description) FROM transactions'),'deduplicated_signed_value':str(scalar('SELECT sum(signed_value) FROM auditable_lines')),'positive_non_cancel_line_value':str(scalar('SELECT sum(signed_value) FROM auditable_lines WHERE sale_line')),'missing_customer_sale_value':str(scalar('SELECT sum(signed_value) FROM auditable_lines WHERE sale_line AND customer_id IS NULL'))}
        report['duplicate_rows_removed'] = report['raw_rows']-report['deduplicated_rows']
        report['country_signed_values'] = [{'country':r[0],'signed_value':str(r[1]),'rows':r[2]} for r in con.execute('SELECT country,sum(signed_value),count(*) FROM auditable_lines GROUP BY country ORDER BY country').fetchall()]
        return report
    finally: con.close()

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=['fetch','build']); parser.add_argument('--data-dir',default='data'); parser.add_argument('--evidence-dir',default='evidence'); args=parser.parse_args()
    root=Path(args.data_dir); ev=Path(args.evidence_dir); ev.mkdir(parents=True,exist_ok=True)
    if args.command=='fetch': print(json.dumps(download(root/'raw'),indent=2)); return
    started=time.perf_counter(); root.mkdir(parents=True,exist_ok=True)
    controls=workbook_to_csv(root/'raw/online_retail_ii.zip',root/'staging/transactions.csv')
    report=build(root/'staging/transactions.csv',root/'retail.duckdb',root/'transactions.parquet')
    report['independent_decimal_reconciliation_passed'] = Decimal(report['raw_signed_value'])==Decimal(controls['python_decimal_raw_signed_value'])
    if not report['independent_decimal_reconciliation_passed']: raise ValueError('Control total mismatch')
    report.update(controls); report.update({'generated_at_utc':datetime.now(timezone.utc).isoformat(),'ingest_and_profile_seconds':round(time.perf_counter()-started,3),'process_peak_rss_mib':round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2),'platform':platform.platform(),'python':platform.python_version(),'duckdb':duckdb.__version__,'openpyxl':openpyxl.__version__,'cpu_count_visible':os.cpu_count(),'duckdb_threads':2,'duckdb_memory_limit':'512MB','parquet_bytes':(root/'transactions.parquet').stat().st_size,'database_bytes':(root/'retail.duckdb').stat().st_size,'vector_index_built':False,'rag_documents_indexed':0,'llm_inference_run':False})
    (ev/'profile.json').write_text(json.dumps(report,indent=2)+'\n')
    (ev/'source_manifest.json').write_text((root/'raw/source_manifest.json').read_text())
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
