"""GB carbon BI star schema; actual estimates and regional forecasts stay separate."""
import argparse,csv,hashlib,html,json,math,sqlite3,urllib.request
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

LONDON=ZoneInfo('Europe/London')
BASE='https://api.carbonintensity.org.uk'
REGIONS={1:'North Scotland',7:'South Wales',13:'London'}
SCHEMA=Path(__file__).with_name('schema.sql')

def stamp(s):
    d=datetime.fromisoformat(s.replace('Z','+00:00'))
    if d.tzinfo is None:raise ValueError('Timezone required')
    return d.astimezone(timezone.utc)
def iso(d):return d.astimezone(timezone.utc).isoformat(timespec='minutes').replace('+00:00','Z')
def number(v):
    if v is None:return None
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:raise ValueError('Invalid intensity')
    return float(v)
def expected_slots(day):
    d=datetime.fromisoformat(day).replace(tzinfo=LONDON)
    return int(((d+timedelta(days=1)).astimezone(timezone.utc)-d.astimezone(timezone.utc)).total_seconds()/1800)
def time_row(start,end):
    a,b=stamp(start),stamp(end)
    if b-a!=timedelta(minutes=30) or a.second or a.minute not in (0,30):raise ValueError('Expected aligned 30-minute interval')
    local=a.astimezone(LONDON);mid=local.replace(hour=0,minute=0,second=0,microsecond=0)
    period=int((a-mid.astimezone(timezone.utc)).total_seconds()/1800)+1
    return (iso(a),iso(b),local.date().isoformat(),local.isoformat(),local.fold,period,30,expected_slots(local.date().isoformat()))
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AshJai23-carbon-BI/1.0','Accept':'application/json'}),timeout=30) as r:
        raw=r.read(5000001)
        if len(raw)>5000000:raise ValueError('Response too large')
        return json.loads(raw),{'url':url,'http_status':r.status,'sha256':hashlib.sha256(raw).hexdigest()}
def collect(end=None):
    end=end or datetime.now(timezone.utc).astimezone(LONDON).replace(hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc)
    local_end=end.astimezone(LONDON)
    if end>datetime.now(timezone.utc) or any((local_end.hour,local_end.minute,local_end.second,local_end.microsecond)):raise ValueError('End must be a past/current London midnight encoded with timezone')
    start=(end.astimezone(LONDON)-timedelta(days=3)).replace(hour=0,minute=0).astimezone(timezone.utc)
    national,np=fetch(f'{BASE}/intensity/{iso(start)}/{iso(end)}')
    regional_start=(end.astimezone(LONDON)-timedelta(days=1)).astimezone(timezone.utc)
    regional,rp=fetch(f'{BASE}/regional/intensity/{iso(regional_start)}/{iso(end)}')
    # Keep only selected DNO regions; countries and other regions are not additive.
    rows=[]
    for r in regional['data']:
        rows.append({'from':r['from'],'to':r['to'],'regions':[{'regionid':x['regionid'],'shortname':x['shortname'],'intensity':x['intensity']} for x in r['regions'] if x['regionid'] in REGIONS]})
    return {'captured_at_utc':datetime.now(timezone.utc).isoformat(),'window_start':iso(start),'window_end':iso(end),'regional_start':iso(regional_start),'national':national['data'],'regional':rows,'requests':[np,rp],'mode':'Live download of historical published estimates and provider forecasts; not a forecast-vintage archive','selection':'Three DNO regions only; no generation mix retained; raw-response hashes recorded'}
def build(snapshot,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(':memory:');db.executescript(SCHEMA.read_text())
    for key,name in REGIONS.items():db.execute('INSERT INTO dim_region VALUES (?,?)',(key,name))
    start,end=stamp(snapshot['window_start']),stamp(snapshot['window_end']);rstart=stamp(snapshot['regional_start'])
    if not start<=rstart<end<=stamp(snapshot['captured_at_utc']) or end-start>timedelta(days=8):raise ValueError('Invalid or future snapshot window')
    quality={'outside_window_rows':0,'exact_duplicates':0,'missing_actual':0,'missing_national_forecast':0,'missing_regional_forecast':0}
    times={};nation={};regions={}
    def register(a,b):
        row=time_row(a,b)
        if row[0] in times and times[row[0]]!=row:raise ValueError('Conflicting interval')
        times[row[0]]=row
        return row[0]
    def put(mapping,key,value):
        if key in mapping:
            if mapping[key]!=value:raise ValueError('Conflicting duplicate')
            quality['exact_duplicates']+=1
        mapping[key]=value
    for r in snapshot['national']:
        a=stamp(r['from'])
        if not start<=a<end:quality['outside_window_rows']+=1;continue
        key=register(r['from'],r['to']);v=r['intensity']
        put(nation,key,(number(v.get('actual')),number(v.get('forecast'))))
    for r in snapshot['regional']:
        a=stamp(r['from'])
        if not rstart<=a<end:quality['outside_window_rows']+=1;continue
        key=register(r['from'],r['to'])
        for reg in r['regions']:
            rid=reg['regionid']
            if rid not in REGIONS:raise ValueError('Unexpected region in retained snapshot')
            put(regions,(key,rid),number(reg['intensity'].get('forecast')))
    if not nation or not regions:raise ValueError('Empty fact table')
    # Scaffold every requested UTC half-hour, even when both sources omit it.
    point=start
    while point<end:
        register(iso(point),iso(point+timedelta(minutes=30)));point+=timedelta(minutes=30)
    for row in times.values():db.execute('INSERT INTO dim_time VALUES (?,?,?,?,?,?,?,?)',row)
    for key,(a,f) in nation.items():
        quality['missing_actual']+=a is None;quality['missing_national_forecast']+=f is None
        db.execute('INSERT INTO fact_national VALUES (?,?,?)',(key,a,f))
    for (key,rid),f in regions.items():
        quality['missing_regional_forecast']+=f is None
        db.execute('INSERT INTO fact_regional_forecast VALUES (?,?,?)',(key,rid,f))
    db.commit()
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    daily=[]
    for row in db.execute('SELECT * FROM v_national_daily ORDER BY local_date'):
        d=dict(zip(['local_date','rows','actual_count','mean_actual_g','mean_forecast_g','paired_mae_g'],row));d['expected_local_slots']=expected_slots(d['local_date']);d['actual_coverage']=d['actual_count']/d['expected_local_slots'];d['complete_intervals']=d['rows']==d['expected_local_slots'];daily.append(d)
    regional=[dict(zip(['region_id','region_name','observations','mean_provider_forecast_g'],r)) for r in db.execute('SELECT r.region_id,r.region_name,COUNT(f.forecast_g),AVG(f.forecast_g) FROM dim_region r LEFT JOIN fact_regional_forecast f USING(region_id) GROUP BY r.region_id ORDER BY r.region_id')]
    expected=int((end-start).total_seconds()/1800);rexp=int((end-rstart).total_seconds()/1800)*len(REGIONS)
    summary={'data_mode':snapshot['mode'],'captured_at_utc':snapshot['captured_at_utc'],'window_start':iso(start),'window_end':iso(end),'national_fact_rows':len(nation),'regional_fact_rows':len(regions),'expected_national_rows':expected,'expected_regional_rows':rexp,'missing_national_intervals':expected-len(nation),'missing_regional_intervals':rexp-len(regions),'quality':quality,'national_daily':daily,'regional_forecasts':regional,'training':'None: this is SQL data modelling and BI, not a new ML forecast.','units':'gCO2/kWh; means time-weight equal 30-minute intervals, not demand-weighted emissions','geography':'GB national, three DNO regions; not council boundaries or Northern Ireland','freshness_hours_at_capture':(stamp(snapshot['captured_at_utc'])-max(stamp(k)+timedelta(minutes=30) for k in nation)).total_seconds()/3600}
    with sqlite3.connect(out/'carbon.sqlite') as target:db.backup(target)
    dump='PRAGMA foreign_keys=ON;\n'+'\n'.join(db.iterdump())+'\n';(out/'warehouse.sql').write_text(dump)
    for table in ['dim_time','dim_region','fact_national','fact_regional_forecast','v_national_daily']:
        cur=db.execute(f'SELECT * FROM {table} ORDER BY 1,2');rows=cur.fetchall()
        with (out/(table+'.csv')).open('w',newline='') as f:w=csv.writer(f);w.writerow(x[0] for x in cur.description);w.writerows(rows)
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    (out/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>GB carbon BI audit</title><style>body{font:16px system-ui;max-width:1000px;margin:30px auto;background:#112535;color:#ecf3f9}pre{white-space:pre-wrap}</style><h1>GB carbon BI audit</h1><p>Saved report, not a live website. Provider forecasts are separate from national actual estimates. No emissions totals without consumption.</p><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre></html>')
    db.close();return summary

def main():
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--input',default='examples/source_snapshot.json');p.add_argument('--output',default='outputs');p.add_argument('--end',help='London midnight encoded in UTC, e.g. 2026-10-28T00:00Z');a=p.parse_args()
    s=collect(stamp(a.end) if a.end else None) if a.live else json.loads(Path(a.input).read_text())
    summary=build(s,a.output)
    if a.live:(Path(a.output)/'source_snapshot.json').write_text(json.dumps(s,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
