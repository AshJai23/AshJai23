"""Verify deployed Python assets match the main project, without processing messages."""
import hashlib
import json
from pathlib import Path
base=Path(__file__).resolve().parent
project=base.parent
manifest=json.loads((base/'dist/engine-manifest.json').read_text())
assert {x['name'] for x in manifest['files']}=={'__init__.py','detection.py','batch.py','market.py'}
for item in manifest['files']:
    served=(base/'dist'/item['path']).read_bytes()
    source=(project/'src/smartinvest'/item['name']).read_bytes()
    assert served==source, item['name']
    assert hashlib.sha256(served).hexdigest()==item['sha256'],item['name']
print(json.dumps({'source_assets_match':True,'engine_version':manifest['engine_version'],'files':len(manifest['files'])}))
