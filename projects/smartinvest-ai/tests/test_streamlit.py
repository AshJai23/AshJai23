"""Real Streamlit AppTest runs; no browser or financial data needed."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1]/'app.py')


def test_app_load_and_blank_validation():
    at=AppTest.from_file(APP).run()
    assert not at.exception
    at.button[0].click().run()
    assert not at.exception
    assert any('Provide an offer' in x.value for x in at.error)


def test_warning_report_survives_rerun_and_can_be_cleared():
    at=AppTest.from_file(APP).run()
    at.text_area[0].set_value('Guaranteed 20% monthly profits. Act now!')
    at.text_input[1].set_value('[Not a link](https://example.org)')
    at.button[0].click().run()
    assert not at.exception
    assert at.warning
    assert any(x.label=='Download screening report (JSON)' for x in at.get('download_button'))
    assert any('not checked' in x.value for x in at.markdown)
    assert any('[Not a link]' in x.value for x in at.text)
    at.run()
    assert any(x.label=='Download screening report (JSON)' for x in at.get('download_button'))
    at.button[1].click().run()
    assert not at.exception
    assert not at.warning
    assert at.text_area[0].value==''
    assert not any(x.label=='Download screening report (JSON)' for x in at.get('download_button'))


def test_negated_claim_ui_does_not_imply_safe():
    at=AppTest.from_file(APP).run()
    at.text_area[0].set_value('Returns are not guaranteed. Investment values can fall.')
    at.button[0].click().run()
    assert not at.exception
    assert not at.warning
    assert any('does NOT mean' in x.value for x in at.info)


def test_batch_dashboard_and_clear():
    at=AppTest.from_file(APP).run()
    at.file_uploader[0].set_value(('offers.csv',b'offer_text\nGuaranteed returns\nRead the prospectus\n','text/csv'))
    next(x for x in at.button if x.label=='Screen CSV').click().run()
    assert not at.exception
    assert [x.value for x in at.metric]==['2','1','0']
    assert any(x.label=='Download batch summary (CSV)' for x in at.get('download_button'))
    assert 'offer_text' not in at.dataframe[0].value.columns
    next(x for x in at.button if x.label=='Clear batch report and upload').click().run()
    assert not at.exception
    assert not at.metric
    assert at.file_uploader[0].value is None


def test_batch_submit_without_file():
    at=AppTest.from_file(APP).run()
    next(x for x in at.button if x.label=='Screen CSV').click().run()
    assert not at.exception
    assert any('Choose a CSV' in x.value for x in at.error)


def test_invalid_csv_upload_shows_validation_error():
    at=AppTest.from_file(APP).run()
    at.file_uploader[0].set_value(('bad.csv',b'private_column\nPRIVATE-EXAMPLE\n','text/csv'))
    next(x for x in at.button if x.label=='Screen CSV').click().run()
    assert not at.exception
    assert at.error
    assert not at.metric
    assert 'PRIVATE-EXAMPLE' not in at.error[0].value
