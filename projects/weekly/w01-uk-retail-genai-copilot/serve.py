"""Start the local web app from any terminal directory."""
import argparse
import os
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--baseline',action='store_true',help='Explicit BM25 mode with generation disabled; still requires real warehouse/corpus setup.')
    args=parser.parse_args()
    if not 1<=args.port<=65535:parser.error('Port must be between 1 and 65535')
    if args.baseline:
        os.environ['W01_RETRIEVAL']='bm25'
        os.environ['W01_GENERATION']='off'
    try:
        import uvicorn
        from api import app
    except ModuleNotFoundError as exc:
        raise SystemExit('A dependency is missing. Use the project virtual environment and install requirements-api.txt (plus requirements-ai.txt and CPU torch for generation).') from exc
    print('Open http://127.0.0.1:'+str(args.port)+'/ on this computer. Keep this terminal open; Ctrl+C stops the server.',flush=True)
    uvicorn.run(app,host='127.0.0.1',port=args.port,access_log=False)
if __name__=='__main__':main()
