"""Synthetic rule/security regressions; not a fraud-labelled ML benchmark."""
import json
import socket
import urllib.request

import pytest
from smartinvest.detection import scan_offer


def codes(text="", url=""):
    return {x.code for x in scan_offer(text, url).findings}


@pytest.mark.parametrize("text", [
    "Returns are not guaranteed. Values may fall.",
    "This is not a risk-free investment.",
    "We never promise guaranteed profits.",
    "There are no guaranteed returns.",
])
def test_explicit_negation_does_not_trigger_claim(text):
    assert not codes(text) & {"GUARANTEED_RETURNS", "NO_RISK_CLAIM"}


def test_later_affirmative_claim_still_matches():
    assert "GUARANTEED_RETURNS" in codes("Returns are not guaranteed. But we guarantee monthly profits.")


def test_not_only_is_not_a_denial():
    assert "GUARANTEED_RETURNS" in codes("Not only guaranteed profits, but risk-free gains too.")


def test_later_recurring_return_not_hidden_by_small_first_value():
    assert "HIGH_RECURRING_RETURN" in codes("Earn 0.2% daily or 50% monthly.")


@pytest.mark.parametrize("text,expected", [
    ("Earn 0,5% monthly", False), ("Earn 12,5% monthly", True),
    ("Earn 1000% monthly", True), ("We do not offer 20% monthly", False),
    ("Performance was 20% annually", False),
])
def test_percentage_formats_and_denial(text, expected):
    assert ("HIGH_RECURRING_RETURN" in codes(text)) is expected


@pytest.mark.parametrize("url", [
    "https://example.org:99999", "https://example.org:notaport",
    "https://example.org/path with spaces", "https://example.org\n/path",
    "https://example.org\\@other.example", "javascript:alert(1)",
    "https://bad..example", "https://example.org:bad",
])
def test_malformed_url_is_reported(url):
    assert "INVALID_URL" in codes(url=url)


def test_unicode_hostname_gets_internationalised_domain_indicator():
    assert "PUNYCODE_DOMAIN" in codes(url="https://examplе.org")  # Cyrillic e


def test_ipv6_and_host_without_scheme():
    assert "IP_ADDRESS_URL" in codes(url="https://[::1]/")
    assert not codes(url="example.org")


def test_credentials_not_returned_in_report():
    payload=scan_offer("Guaranteed returns at https://user:example-password@other.example", "http://user:example-password@other.example").as_dict()
    assert "example-password" not in json.dumps(payload)
    assert "URL_CREDENTIALS" in {x['code'] for x in payload['findings']}
    assert payload['verification_status']=='not_checked'


def test_no_dns_or_url_fetch(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Offline screening must not resolve or fetch URLs")
    monkeypatch.setattr(socket, 'getaddrinfo', fail)
    monkeypatch.setattr(urllib.request, 'urlopen', fail)
    assert scan_offer(website_url='http://127.0.0.1/private').verification_status=='not_checked'


@pytest.mark.parametrize("value", [None, 42, [], {}])
def test_core_rejects_non_string_inputs(value):
    with pytest.raises(TypeError):scan_offer(value)


def test_duplicate_urls_do_not_multiply_indicators():
    result=scan_offer('Visit https://bit.ly/demo or https://bit.ly/demo', 'https://bit.ly/demo')
    assert len(result.websites)==1
    assert len([x for x in result.findings if x.code=='SHORTENED_URL'])==1
