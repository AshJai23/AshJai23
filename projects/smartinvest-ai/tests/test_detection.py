import pytest
from smartinvest.detection import scan_offer


def codes(report):
    return {item.code for item in report.findings}


def test_guaranteed_return_and_urgency():
    result = scan_offer("Guaranteed 20% monthly profits. Act now! Contact us on WhatsApp")
    assert result.screening_status == "warning_signals_detected"
    assert {"GUARANTEED_RETURNS", "HIGH_RECURRING_RETURN", "URGENCY", "PRIVATE_MESSAGING"} <= codes(result)
    assert result.verification_status == "not_checked"


def test_neutral_text_does_not_imply_safe():
    result = scan_offer("Read the investment prospectus before deciding.")
    assert result.screening_status == "no_configured_indicators_detected"
    assert any("does not mean" in x for x in result.limitations)


def test_url_creds_are_flagged():
    result = scan_offer(website_url="https://trusted-bank.example@unknown.example/offer")
    assert "URL_CREDENTIALS" in codes(result)


def test_shortener_is_flagged_not_confirmed_scam():
    result = scan_offer(website_url="https://bit.ly/abc")
    assert "SHORTENED_URL" in codes(result)
    assert result.verification_status == "not_checked"


def test_https_is_not_a_safety_stamp():
    result = scan_offer(website_url="https://example.org")
    assert not result.findings
    assert result.verification_status == "not_checked"


def test_no_text_or_url_rejected():
    with pytest.raises(ValueError):
        scan_offer(claimed_firm="Example Ltd")


def test_long_text_rejected():
    with pytest.raises(ValueError):
        scan_offer("a" * 10001)


def test_annual_return_not_confused_with_monthly():
    result = scan_offer("Our annual performance in 2023 was 15%.")
    assert "HIGH_RECURRING_RETURN" not in codes(result)


def test_punycode_domain_flagged():
    result = scan_offer(website_url="https://xn--sample-abc.example")
    assert "PUNYCODE_DOMAIN" in codes(result)


def test_result_serializable():
    import json
    result = scan_offer("Guaranteed returns")
    json.dumps(result.as_dict())
