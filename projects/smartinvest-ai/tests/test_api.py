from fastapi.testclient import TestClient
import pytest
from smartinvest.api import app

client = TestClient(app)


def test_health():
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_scan():
    response = client.post("/v1/scans", json={"offer_text": "Act now, guaranteed profits"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["verification_status"] == "not_checked"
    assert payload["screening_status"] == "warning_signals_detected"
    assert any(f["code"] == "GUARANTEED_RETURNS" for f in payload["findings"])


def test_empty_scan_rejected():
    response = client.post("/v1/scans", json={"offer_text": ""})
    assert response.status_code == 422


def test_extra_fields_rejected():
    response = client.post("/v1/scans", json={"offer_text": "Hi", "private_token": "secret"})
    assert response.status_code == 422


@pytest.mark.parametrize("body", [
    {"offer_text": None}, {"offer_text": ["guaranteed"]},
    {"offer_text": "x"*10001}, {"website_url": "x"*2049},
    {"claimed_firm": "x"*201}, {"offer_text": "   "},
])
def test_invalid_api_input_rejected(body):
    assert client.post('/v1/scans',json=body).status_code==422


def test_api_negation_version_and_no_fake_probability():
    body=client.post('/v1/scans',json={'offer_text':'Returns are not guaranteed.'}).json()
    assert not body['findings']
    assert body['engine_version']=='0.3.0'
    assert body['verification_status']=='not_checked'
    assert 'fraud_probability' not in body


def test_batch_endpoint():
    response=client.post('/v1/batch-scans',json={'csv_text':'offer_text\nGuaranteed returns\nRead the prospectus\n'})
    assert response.status_code==200
    body=response.json()
    assert body['summary']['rows_with_indicators']==1
    assert body['summary']['rows_without_configured_indicators']==1
    assert body['verification_status']=='not_checked'
    assert 'Guaranteed returns' not in response.text


def test_batch_bad_schema_rejected():
    assert client.post('/v1/batch-scans',json={'csv_text':'password\nsecret\n'}).status_code==422
    assert client.post('/v1/batch-scans',json={'csv_text':'offer_text\nHi\n','other':1}).status_code==422


def test_validation_errors_do_not_echo_submitted_values():
    value='PRIVATE-MESSAGE-'+'x'*10000
    response=client.post('/v1/scans',json={'offer_text':value,'private_token':'EXAMPLE-SECRET'})
    assert response.status_code==422
    assert 'PRIVATE-MESSAGE' not in response.text
    assert 'EXAMPLE-SECRET' not in response.text
    assert 'private_token' not in response.text
