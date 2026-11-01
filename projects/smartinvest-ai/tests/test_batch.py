"""Synthetic batch fixtures; these are not investment-scam accuracy labels."""
import csv
import io
import json
import pytest
from smartinvest.batch import screen_csv, summary_csv, MAX_BYTES


def test_batch_mixed_rows_and_privacy():
    data=b'sample_id,offer_text,claimed_firm\n=HYPERLINK("bad"),Guaranteed profits,Private Example Firm\na,Returns are not guaranteed.,Another Name\nb,,\n'
    result=screen_csv(data)
    assert result['summary']=={'total_rows':3,'rows_with_indicators':1,'rows_without_configured_indicators':1,'input_error_rows':1}
    payload=json.dumps(result)
    for private in ['HYPERLINK','Guaranteed profits','Private Example Firm','Another Name']:
        assert private not in payload
        assert private.encode() not in summary_csv(result)
    assert all(x['verification_status']=='not_checked' for x in result['rows'])


def test_csv_quotes_multiline_and_bom():
    data='\ufeffoffer_text,website_url\n"Guaranteed returns,\nact now",https://example.org\n'.encode()
    assert screen_csv(data)['summary']['rows_with_indicators']==1


@pytest.mark.parametrize('data', [b'', b'firm\na\n', b'offer_text,offer_text\na,b\n', b'offer_text\n', b'offer_text\n"unclosed', b'offer_text\n\xff', b'offer_text\n\x00'])
def test_invalid_uploads_rejected(data):
    with pytest.raises(ValueError):screen_csv(data)


def test_limits_are_enforced_without_partial_result():
    with pytest.raises(ValueError):screen_csv(b'x'*(MAX_BYTES+1))
    with pytest.raises(ValueError,match='500-row'):screen_csv(b'offer_text\n'+b'Hello\n'*501)


def test_ragged_and_oversized_rows_remain_errors():
    result=screen_csv(('offer_text,website_url\nHello\nHello,,extra\n'+ 'x'*10001+',\n').encode())
    assert result['summary']['input_error_rows']==3


def test_export_schema_and_generated_rows_only():
    result=screen_csv(b'offer_text\nRead the prospectus\n')
    rows=list(csv.DictReader(io.StringIO(summary_csv(result).decode())))
    assert rows[0]['row_number']=='1'
    assert rows[0]['screening_status']=='no_configured_indicators_detected'
    assert 'offer_text' not in rows[0]
