# SmartInvest browser research demo

Private demo: https://smartinvest-ai-lab-ashjai23.denickesolomon2462.chatgpt.site

The static assets mirror the deployed Site source commit
`e3fd83d7038dac26f2824e4e0d4b7d6625d3a796`.
The `.openai/hosting.json` retains the exact Site identity for future Sites
updates. Do not create a duplicate Site or change its audience just to test it.

This is a browser interface over the actual Python engine, not a hosted
Streamlit server or a JavaScript approximation. Pyodide 0.29.0 runs the exact
detection.py and batch.py files copied into dist/py/smartinvest/. Checksums
are verified before loading. Internet is needed to download the runtime from
the official Pyodide jsDelivr distribution; user message/CSV content is not
sent there. No localStorage, scan database, message logging or URL fetching.

Full Streamlit application: ../app.py. Run it using the parent README.
This Site is a research demo; outputs are warning indicators only, not fraud
verdicts, probabilities or a statement that an offer is safe. Firm verification
remains not_checked.

Validation: Node JavaScript syntax check; same-version Pyodide WebAssembly
engine parity on six synthetic cases and the three-row synthetic batch.
This is distinct from authenticated browser UI QA, which was blocked by sign-in.
The parent Python app has 78 passing tests including actual Streamlit file upload.

For basic code/asset verification from the parent project:
`python browser-demo/verify_source.py`.
For a local static demo, serve dist/ from a normal localhost HTTP development
server and use an internet-connected modern browser. Do not open index.html
as a file:// URL: fetch/WebAssembly loading requires an HTTP origin.

## Market research extension (0.4.0)

Third tab runs `smartinvest.market` in the same Pyodide runtime. Four Python assets are checksum-verified and identical to the main project. An attributed ECB daily FX reference snapshot is bundled for historical replay; latest observation 30 October 2026. User-permitted price CSV upload supports shares/ETFs. The browser fits Ridge and shows purged held-out metrics, unchanged-price baseline, residual bands and staleness. No personal best investment, live stock quote or buy/sell instruction. See ../MARKET_RESEARCH.md and ../validation/v0.4.0/. Python/WASM parity passed; full authenticated browser UI QA remains unavailable.
