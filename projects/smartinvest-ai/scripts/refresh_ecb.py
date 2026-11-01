"""Download the fixed public ECB source and derive attributed GBP FX prices."""
import csv, hashlib, io, json, zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
URL = 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip'
DEST = Path(__file__).resolve().parents[1] / 'examples/market'
def convert(raw, manifest):
    output = io.StringIO(newline=''); writer = csv.writer(output)
    writer.writerow(['date','symbol','price','currency'])
    count = 0
    rows = sorted(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))), key=lambda r:r['Date'])
    for row in rows:
        if row['Date'] < '2020-01-01': continue
        try: gbp, usd, jpy = (float(row[k]) for k in ('GBP','USD','JPY'))
        except ValueError: continue
        if min(gbp,usd,jpy) <= 0: continue
        for symbol, price in [('EURGBP',gbp),('USDGBP',gbp/usd),('JPYGBP',gbp/jpy)]:
            writer.writerow([row['Date'],symbol,format(price,'.12g'),'GBP']); count += 1
    data = output.getvalue().encode()
    manifest.update(processed_rows=count, symbols=['EURGBP','USDGBP','JPYGBP'],
                    latest_observation=rows[-1]['Date'], processed_sha256=hashlib.sha256(data).hexdigest(),
                    processed_bytes=len(data), start_date='2020-01-01',
                    attribution='Source: European Central Bank. Derived GBP-per-unit cross-rates and date filtering by SmartInvest AI; not ECB investment advice.')
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/'ecb-fx-gbp.csv').write_bytes(data)
    (DEST/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__ == '__main__':
    with urlopen(URL,timeout=30) as response:
        if response.geturl() != URL: raise ValueError('Unexpected redirect; review source')
        archive = response.read(5*1024*1024+1)
    if len(archive)>5*1024*1024: raise ValueError('ECB download too large')
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        info=z.getinfo('eurofxref-hist.csv')
        if info.file_size>20*1024*1024: raise ValueError('Uncompressed source too large')
        raw=z.read(info)
    convert(raw,dict(publisher='European Central Bank',url=URL,
        copyright_terms='https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html',
        retrieved_at_utc=datetime.now(timezone.utc).isoformat(),http_status=200,
        zip_sha256=hashlib.sha256(archive).hexdigest(),zip_bytes=len(archive),csv_sha256=hashlib.sha256(raw).hexdigest(),
        mode='Historical daily reference snapshot, not live polling or executable trading quotes',
        modification='GBP per EUR directly; GBP per USD/JPY = GBP per EUR divided by USD/JPY per EUR.'))
