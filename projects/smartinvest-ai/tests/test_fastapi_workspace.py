"""Exercise the actual FastAPI routes and packaged web resources."""
from fastapi.testclient import TestClient
from importlib.resources import files
from smartinvest.api import app

client = TestClient(app)

def test_workspace_page_and_security_headers():
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "FASTAPI BACKEND" in response.text
    assert 'src="/assets/app.js"' in response.text
    assert response.headers["cache-control"] == "no-store"
    assert "connect-src 'self'" in response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]

def test_javascript_is_fixed_packaged_resource():
    response = client.get("/assets/app.js")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/javascript")
    assert response.text == files("smartinvest").joinpath("web/app.js").read_text(encoding="utf-8")
    assert 'post("/v1/market-research"' in response.text

def test_assets_do_not_expose_arbitrary_files():
    assert client.get("/assets/api.py").status_code == 404
    assert client.get("/assets/%2e%2e/api.py").status_code == 404

def test_openapi_preserves_json_routes_and_hides_assets():
    schema = client.get("/openapi.json").json()
    assert schema["info"]["version"] == "0.4.1"
    assert "/v1/market-research" in schema["paths"]
    assert "/v1/scans" in schema["paths"]
    assert "/v1/batch-scans" in schema["paths"]
    assert "/" not in schema["paths"]
    assert "/assets/app.js" not in schema["paths"]

def test_market_validation_does_not_echo_input():
    response = client.post("/v1/market-research",json={"csv_text":"PRIVATE-EXAMPLE", "horizon":4})
    assert response.status_code == 422
    assert "PRIVATE-EXAMPLE" not in response.text
    assert "horizon" in response.text
