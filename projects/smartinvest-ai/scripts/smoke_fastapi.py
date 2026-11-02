"""Bounded real HTTP smoke; real ECB replay, no public host or permanent service."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

root = Path(__file__).resolve().parents[1]
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
server = subprocess.Popen([sys.executable, "-m", "uvicorn", "smartinvest.api:app",
    "--host", "127.0.0.1", "--port", str(port), "--no-access-log", "--log-level", "warning"], cwd=root)
base = f"http://127.0.0.1:{port}"
def get(path):
    with urlopen(base+path, timeout=30) as response:
        assert response.status == 200
        return response.read()
def post(path, payload):
    request = Request(base+path, data=json.dumps(payload).encode(),
                      headers={"Content-Type":"application/json"}, method="POST")
    with urlopen(request, timeout=30) as response:
        assert response.status == 200
        return json.load(response)
try:
    deadline = time.monotonic()+20
    while True:
        if server.poll() is not None:
            raise RuntimeError("Uvicorn exited before becoming healthy")
        try:
            assert json.loads(get("/v1/health"))["status"] == "ok"
            break
        except (URLError, OSError):
            if time.monotonic() >= deadline: raise
            time.sleep(.1)
    assert b"SmartInvest AI" in get("/")
    assert b"market-research" in get("/assets/app.js")
    assert "/v1/scans" in json.loads(get("/openapi.json"))["paths"]
    scan = post("/v1/scans", {"offer_text":"Guaranteed 20% monthly profits. Act now!"})
    assert scan["verification_status"] == "not_checked" and scan["findings"]
    batch = post("/v1/batch-scans", {"csv_text":"offer_text\nGuaranteed returns\nRead the prospectus\n"})
    assert batch["summary"]["total_rows"] == 2
    csv = (root/"examples/market/ecb-fx-gbp.csv").read_text()
    result = post("/v1/market-research", {"csv_text":csv,"horizon":5})
    assert len(result["assets"]) == 3
    assert all(a["observations"] == 1751 for a in result["assets"])
    assert all(a["forecast"]["test_rows"] == 346 for a in result["assets"])
    print(json.dumps({"real_http_smoke":"passed", "server":"uvicorn on ephemeral loopback port",
        "health":True,"html":True,"javascript":True,"openapi":True,
        "scam_input":"labelled synthetic fixture", "batch_input":"labelled synthetic fixture",
        "market_input":"attributed ECB historical replay", "latest_observation":result["latest_observation"],
        "market_assets":3,"market_observations_per_asset":1751,
        "public_deployment":False}))
finally:
    server.terminate()
    try: server.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait(timeout=5)
