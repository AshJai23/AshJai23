"""Streamlit entry point: run with `streamlit run app.py`."""
import json
from pathlib import Path

import streamlit as st
from smartinvest.detection import ENGINE_VERSION, FCA_FIRM_CHECKER, FCA_WARNINGS, scan_offer
from smartinvest.batch import screen_csv, summary_csv

st.set_page_config(page_title="SmartInvest AI", page_icon="🛡️", layout="centered")
st.title("🛡️ SmartInvest AI")
st.caption("Educational investment offer screening — research project prototype")
st.info(
    "This tool highlights some warning signs; it cannot verify an investment or certify it as safe. "
    "Do not share passwords, account numbers, or other sensitive personal data."
)

def clear_report():
    for key in ("offer_input", "url_input", "firm_input"):
        st.session_state[key] = ""
    st.session_state.pop("screening_result", None)


with st.form("check_offer"):
    offer_text = st.text_area(
        "Paste an investment offer or message", height=160,
        placeholder="Example: Guaranteed 20% monthly profits. Act now...",
        max_chars=10000,
        key="offer_input",
    )
    url = st.text_input("Investment website URL (optional)", max_chars=2048, key="url_input")
    firm = st.text_input("Claimed firm name (optional)", max_chars=200, key="firm_input")
    submitted = st.form_submit_button("Check for warning signs", type="primary")

if submitted:
    st.session_state.pop("screening_result", None)
    try:
        result = scan_offer(offer_text, url, firm)
    except ValueError as exc:
        st.error(str(exc))
    else:
        st.session_state["screening_result"] = result

result = st.session_state.get("screening_result")
if result is not None:
        if result.findings:
            st.warning(f"{len(result.findings)} warning indicator(s) detected — review required")
        else:
            st.info("No configured warning patterns detected. This does NOT mean the offer is safe.")

        st.subheader("Detected indicators")
        if not result.findings:
            st.write("No text or URL indicators matched our limited rules.")
        for finding in result.findings:
            with st.expander(f"{finding.severity.upper()} · {finding.code}", expanded=True):
                st.write(finding.explanation)
                st.caption("Matched input (rendered as text)")
                st.code(finding.evidence, language=None)

        st.subheader("Firm verification")
        st.write("Verification status: **not checked**. A firm name alone does not establish FCA authorisation.")
        if result.claimed_firm:
            st.text("Claimed firm: " + result.claimed_firm)
        st.markdown(f"[FCA Firm Checker]({FCA_FIRM_CHECKER}) · [FCA Warning List]({FCA_WARNINGS})")

        st.subheader("Recommended next steps")
        for step in result.next_steps:
            st.write("• " + step)

        st.subheader("Limitations")
        for limitation in result.limitations:
            st.caption("• " + limitation)

        st.download_button(
            "Download screening report (JSON)",
            json.dumps(result.as_dict(), indent=2),
            file_name="smartinvest-screening.json",
            mime="application/json",
        )
        st.button("Clear report and inputs", on_click=clear_report)

st.divider()
st.subheader("Batch CSV review")
st.caption("Up to 500 rows / 2 MiB, UTF-8 CSV. Processing stays local. This is a review queue, not a labelled dataset or an accuracy result.")
st.download_button("Download synthetic CSV template", Path(__file__).with_name("examples").joinpath("synthetic-offers.csv").read_bytes(),
                   file_name="synthetic-offers.csv", mime="text/csv")


def clear_batch():
    st.session_state.pop("batch_report", None)
    st.session_state["batch_upload_generation"] = st.session_state.get("batch_upload_generation", 0) + 1


with st.form("batch_scan"):
    upload = st.file_uploader("Upload offers CSV", type=["csv"],
                              key=f"batch_csv_{st.session_state.get('batch_upload_generation', 0)}")
    batch_submitted = st.form_submit_button("Screen CSV")
if batch_submitted:
    st.session_state.pop("batch_report", None)
    try:
        if upload is None:
            raise ValueError("Choose a CSV file first")
        st.session_state["batch_report"] = screen_csv(upload.getvalue())
    except (ValueError, TypeError) as exc:
        st.error(str(exc))

batch = st.session_state.get("batch_report")
if batch is not None:
    summary = batch["summary"]
    cols = st.columns(3)
    cols[0].metric("Rows screened", summary["total_rows"] - summary["input_error_rows"])
    cols[1].metric("Rows with indicators", summary["rows_with_indicators"])
    cols[2].metric("Input errors", summary["input_error_rows"])
    st.info("No indicators does not mean safe. Firm verification: not checked for every row.")
    st.dataframe(batch["rows"], hide_index=True)
    if batch["indicator_row_counts"]:
        st.bar_chart({"Indicator": list(batch["indicator_row_counts"]),
                      "Rows": list(batch["indicator_row_counts"].values())}, x="Indicator", y="Rows")
    st.caption("Summary exports exclude raw messages, firm names, URLs and supplied sample IDs. Use generated row numbers to locate the original CSV records.")
    st.download_button("Download batch summary (CSV)", summary_csv(batch), file_name="smartinvest-batch-summary.csv", mime="text/csv")
    st.button("Clear batch report and upload", on_click=clear_batch)

st.divider()
st.caption(f"Research prototype v{ENGINE_VERSION} — offline rules, no website fetching or ML training. Inputs/results stay in this session's memory; no scan database or file logging.")

st.divider()
st.header('Investment research & experimental forecasts')
st.write('Compare historical price changes and risk. There is no universal best investment; the suitable choice depends on your goals, time horizon and ability to lose money.')
with st.expander('Where can I research investing?'):
    st.markdown('**Cash/deposits:** research access, interest and deposit protection. **Diversified funds/ETFs:** research holdings, fees and capital risk. **Bonds:** research credit, duration and interest-rate risk. **Individual shares:** research business and concentration risk. No specific product is recommended here.')
    st.markdown('[MoneyHelper: saving or investing](https://www.moneyhelper.org.uk/en/savings/how-to-save/should-i-save-or-invest) · [FCA Firm Checker](https://www.fca.org.uk/consumers/fca-firm-checker)')
st.caption('Upload price history you are permitted to use: date,symbol,price,currency. One quote currency; at least 240 shared daily observations; max 10 symbols / 2 MiB. Use adjusted prices if appropriate; dividends and costs are not handled here.')
market_upload = st.file_uploader('Upload price history CSV', type=['csv'], key='market_upload')
horizon = st.selectbox('Forecast horizon (subsequent observations)', [1,5,20], index=1)
use_example = st.button('Analyse ECB currency example')
use_upload = st.button('Analyse uploaded prices')
if use_example or use_upload:
    st.session_state.pop('market_result',None)
    try:
        from smartinvest.market import analyse_prices
        folder=Path(__file__).parent/'examples/market'
        if use_example:
            data=(folder/'ecb-fx-gbp.csv').read_bytes()
            source=json.loads((folder/'source-manifest.json').read_text())
            source_note='ECB historical daily FX reference snapshot. Latest '+source['latest_observation']+'; captured '+source['retrieved_at_utc']+'. Not stock/ETF prices or executable trading quotes. Derived GBP cross-rates.'
        else:
            if market_upload is None: raise ValueError('Choose a price CSV first')
            data=market_upload.getvalue(); source_note='User-uploaded history; provenance and price adjustments have not been independently verified.'
        st.session_state.market_result=(analyse_prices(data,horizon),source_note)
    except ValueError as exc: st.error(str(exc))
if 'market_result' in st.session_state:
    research,note=st.session_state.market_result
    st.info(note)
    st.caption('Source: European Central Bank; derived calculations by SmartInvest AI. '+research['latest_observation']+' latest observation. Snapshot, not live polling.')
    if research['stale_after_7_calendar_days']: st.warning('History is more than seven calendar days old; refresh or replace it before research.')
    st.dataframe([{'Symbol':a['symbol'],'Price':a['last_price'],'252-observation change %':a['trailing_252_observation_change_pct'],'Annualised volatility %':a['annualised_log_volatility_pct'],'Max drawdown %':a['max_drawdown_pct']} for a in research['assets']],hide_index=True)
    for a in research['assets']:
        f=a['forecast']
        with st.expander(a['symbol']+' · fitted Ridge forecast', expanded=True):
            st.write(f"Projection: {f['projection']:.6g} {research['quote_currency']} after {f['horizon_observations']} observations. Residual band: {f['calibration_band_low']:.6g}–{f['calibration_band_high']:.6g}.")
            st.write(f"Held-out mean absolute percentage error: model {f['ridge_mape_pct']:.3f}% vs unchanged-price baseline {f['persistence_mape_pct']:.3f}%. Test samples: {f['test_rows']}. Band coverage on test: {f['calibration_band_test_coverage']:.1%}.")
            if not f['model_beat_baseline']: st.warning('The model did not beat the unchanged-price baseline on held-out data.')
            st.caption(f['band_note']+' '+f['forecast_fit_note'])
    st.caption(' / '.join(research['limitations']))
    st.download_button('Download research and held-out results',json.dumps(research,indent=2),file_name='smartinvest-market-research.json')
