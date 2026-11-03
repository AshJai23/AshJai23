"""Reproduce into ignored local output, preserving published historical evidence.

Preflight/resume checks never count as fresh inference. Use a new output directory
to perform a new full run; completed checkpoints cannot masquerade as a new run.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

def completed_count(directory):
    journal=Path(directory)/'quality-cases.jsonl'
    return sum(1 for line in journal.read_text().splitlines() if line.strip()) if journal.exists() else 0

def check_resume(directory, *, resume, expected_cases):
    count=completed_count(directory)
    if count and not resume:raise ValueError('Existing cases require --resume or a new --out directory')
    if resume and count>=expected_cases:raise ValueError('Run already complete. Review its evidence or choose a new --out; no new inference performed.')
    return count

def digest(path):
    checksum=hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda:source.read(1048576),b''):checksum.update(block)
    return checksum.hexdigest()

def verify_model_files(root):
    manifests={}
    for name in ('llm','embedding'):
        directory=Path(root)/name;manifest=json.loads((directory/'manifest.json').read_text())
        for item in manifest['files']:
            if Path(item['name']).name!=item['name']:raise ValueError('Invalid model manifest filename')
            if digest(directory/item['name'])!=item['sha256']:raise ValueError('Model file checksum mismatch')
        manifests[name]={'model_id':manifest['model_id'],'revision':manifest['revision'],'licence':manifest['licence'],
                         'files':{row['name']:row['sha256'] for row in manifest['files']}}
    return manifests

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',default='data/quality-evaluation');parser.add_argument('--resume',action='store_true');parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
    output=Path(args.out)
    # Never overwrite versioned evidence by accident. Check-only may inspect paths.
    if not args.check_only and 'evidence' in output.parts:
        raise ValueError('Choose an ignored local data/ output, not published evidence/')
    contract=json.loads(Path('evaluation/quality_v2.json').read_text())
    before=check_resume(output,resume=args.resume,expected_cases=len(contract['tasks']))
    config={'wrapper_sha256':digest(__file__),'models':verify_model_files('models'),
            'packages':{name:importlib.metadata.version(name) for name in ('torch','transformers','numpy','duckdb','langgraph')},
            'evaluation_sha256':digest('evaluation/quality_v2.json'),'corpus_sha256':digest('data/corpus.json'),
            'index_sha256':digest('data/retrieval/vectors.npy')}
    file=output/'resume-integrity.json'
    if file.exists() and json.loads(file.read_text())!=config:raise ValueError('Resume environment/model/index differs; choose a new --out')
    if args.resume and before and not file.exists():raise ValueError('No integrity lock for this checkpoint; use original evidence or a new run')
    if args.check_only:
        print(json.dumps({'preflight_passed':True,'model_files_verified':True,'existing_cases':before,'inference_performed':False}));return
    output.mkdir(parents=True,exist_ok=True);file.write_text(json.dumps(config,indent=2)+'\n')
    import evaluate_quality
    evaluate_quality.OUT=output
    sys.argv=[sys.argv[0],'--out',str(output)]+(['--resume'] if args.resume else [])
    evaluate_quality.main()
    path=output/'quality-summary.json';report=json.loads(path.read_text())
    report['checkpoint_execution']={'resumed':args.resume,'cases_before_execution':before,
        'new_cases_this_execution':report['completion']['recorded_cases']-before,
        'latency_rows_include_prior_checkpoint_cases':bool(before),
        'wall_time_note':'run_wall_seconds measures this process segment; per-case latencies may include prior verified checkpoints when resumed.'}
    path.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
