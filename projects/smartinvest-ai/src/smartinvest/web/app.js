"use strict";
const $=id=>document.getElementById(id);
const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);return n;};
let busy=false;
function status(text){$("status").textContent=text;}
function lock(value){busy=value;document.querySelectorAll("form button, form input, form select, form textarea").forEach(n=>n.disabled=value);}
async function post(path,payload){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),90000);
 try{const r=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload),signal:controller.signal,cache:"no-store"});
 const body=await r.json();
 if(!r.ok)throw new Error(typeof body.detail==="string"?body.detail:"Input rejected. Check the CSV format and field limits.");
 return body;}finally{clearTimeout(timer);}
}
async function csv(id){const f=$(id).files[0];if(!f)throw new Error("Choose a CSV file first.");if(f.size>2*1024*1024)throw new Error("CSV exceeds 2 MiB.");return new TextDecoder("utf-8",{fatal:true}).decode(await f.arrayBuffer());}
function download(report,name,container){
 const b=el("button","Download JSON");b.type="button";b.addEventListener("click",()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:"application/json"}));const a=el("a");a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);});container.append(b);
}
async function run(target,work){if(busy)return;$(target).replaceChildren();lock(true);status("Processing on the FastAPI server…");try{await work();status("Finished. Review the results and limitations.");}catch(e){status(e.name==="AbortError"?"Request timed out; the server may still finish processing.":e instanceof TypeError?"Request or UTF-8 decoding failed. Check the backend and file encoding.":e.message);}finally{lock(false);}}
$("scan-form").addEventListener("submit",e=>{e.preventDefault();run("scan-result",async()=>{const r=await post("/v1/scans",{offer_text:$("offer").value,website_url:$("website").value,claimed_firm:$("firm").value});const box=$("scan-result");box.append(el("h3",r.findings.length?r.findings.length+" warning indicator(s)":"No configured indicators matched — this does not mean safe."),el("p","Firm verification: "+r.verification_status));for(const f of r.findings)box.append(el("h4",f.code),el("p",f.explanation),el("pre",f.evidence));download(r,"smartinvest-screening.json",box);});});
$("batch-form").addEventListener("submit",e=>{e.preventDefault();run("batch-result",async()=>{const text=await csv("offers"),r=await post("/v1/batch-scans",{csv_text:text});$("batch-result").append(el("pre",JSON.stringify(r.summary,null,2)));download(r,"smartinvest-batch.json",$("batch-result"));});});
$("market-form").addEventListener("submit",e=>{e.preventDefault();run("market-result",async()=>{const text=await csv("prices"),r=await post("/v1/market-research",{csv_text:text,horizon:Number($("horizon").value)}),box=$("market-result");box.append(el("p","User-provided history; provenance not verified. Latest: "+r.latest_observation+"; age "+r.observation_age_calendar_days+" calendar days; quote currency "+r.quote_currency+"."));
 if(r.stale_after_7_calendar_days)box.append(el("strong","History is more than seven calendar days old. Refresh or replace it."));
 const table=el("table"),header=el("tr");for(const h of ["Symbol","252-observation change","Annual volatility","Max drawdown"])header.append(el("th",h));table.append(header);
 for(const a of r.assets){const row=el("tr");for(const v of [a.symbol,a.trailing_252_observation_change_pct,a.annualised_log_volatility_pct,a.max_drawdown_pct])row.append(el("td",typeof v==="number"?v.toFixed(2)+"%":v===null?"n/a":v));table.append(row);}box.append(table);
 for(const a of r.assets){const f=a.forecast;box.append(el("h3",a.symbol+" · experimental projection"),el("p","After "+f.horizon_observations+" observations: "+f.projection.toPrecision(6)+" "+r.quote_currency+"; residual band "+f.calibration_band_low.toPrecision(6)+"–"+f.calibration_band_high.toPrecision(6)+"."),el("p","Held-out MAPE: model "+f.ridge_mape_pct.toFixed(3)+"% versus unchanged-price baseline "+f.persistence_mape_pct.toFixed(3)+"% ("+f.test_rows+" samples)."),el("strong",f.model_beat_baseline?"Beat this baseline on this period only; future performance is unknown.":"Did NOT beat the unchanged-price baseline."),el("p","Held-out band coverage: "+(100*f.calibration_band_test_coverage).toFixed(1)+"%. "+f.band_note),el("small",f.forecast_fit_note));}
 for(const text of r.limitations)box.append(el("small",text));download(r,"smartinvest-market-research.json",box);});});
for(const mode of ["scan","market","batch"])$(mode+"-form").addEventListener("reset",()=>{$(mode+"-result").replaceChildren();status("Inputs and results cleared from the page.");});
fetch("/v1/health",{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error();return r.json();}).then(r=>status(r.status==="ok"?"FastAPI backend connected · local research prototype":"Backend health check failed.")).catch(()=>status("Backend unavailable. Start uvicorn and reload."));
