"""Real HTTP smoke against local Uvicorn; no permanent host provisioned."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request,urlopen

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("--baseline",action="store_true");parser.add_argument("--evidence-dir",default="data/http-smoke");args=parser.parse_args()
    mode="bm25" if args.baseline else "hybrid"
    generation="off" if args.baseline else "on"
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    started=time.perf_counter()
    server=subprocess.Popen([sys.executable,'-m','uvicorn','api:app','--host','127.0.0.1','--port',str(port),'--no-access-log','--log-level','warning'],env={**os.environ,'W01_RETRIEVAL':mode,'W01_GENERATION':generation,'OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2'})
    base=f'http://127.0.0.1:{port}'
    def get(path):
        with urlopen(base+path,timeout=60) as response:
            assert response.status==200
            return response.read()
    try:
        deadline=time.monotonic()+90
        while True:
            if server.poll() is not None:raise RuntimeError('Uvicorn exited')
            try:
                health=json.loads(get('/v1/health'));break
            except (URLError,OSError):
                if time.monotonic()>deadline:raise
                time.sleep(.2)
        assert health['status']=='ready' and health['local_generation_enabled']==(not args.baseline) and health['retrieval']==mode
        assert b'Retail Evidence' in get('/')
        assert b'/v1/ask' in get('/assets/app.js')
        request=Request(base+'/v1/ask',data=json.dumps({'question':'Explain invoice fields'}).encode(),headers={'Content-Type':'application/json'},method='POST')
        with urlopen(request,timeout=60) as response:answer=json.load(response)
        assert answer['generation']['attempted']==(not args.baseline)
        if not args.baseline:assert answer['generation']['completed']
        assert answer['calls']==1
        report={'passed':True,'mode':'actual ephemeral Uvicorn HTTP; full historical replay; '+('explicit BM25/no-generation baseline' if args.baseline else 'hybrid retrieval and fresh CPU generation'),
                'source':health['source'],'response':answer,'wall_seconds':time.perf_counter()-started,
                'public_deployment':False,'server_stopped_after_smoke':True}
        Path(args.evidence_dir).mkdir(parents=True,exist_ok=True)
        Path(args.evidence_dir).joinpath('http-smoke-baseline.json' if args.baseline else 'http-smoke.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'passed':True,'fresh_generation':not args.baseline,'status':answer['answer']['status'],'request_seconds':answer['request_seconds']}))
    finally:
        server.terminate()
        try:server.wait(timeout=10)
        except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
if __name__=='__main__':main()

