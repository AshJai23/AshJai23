"use strict";
const $ = id => document.getElementById(id);
let py = null, lastReport = null, reportMode = null, busy = false;
const runtime = $("runtime");
function node(tag, text, cls) { const e=document.createElement(tag); if(text!==undefined)e.textContent=text; if(cls)e.className=cls; return e; }
function error(message) { $("error").textContent=message; $("error").hidden=!message; }
function setBusy(value) { busy=value; $("scan-button").disabled=value||!py; $("batch-button").disabled=value||!py; }
function clearResult() { lastReport=null;reportMode=null;$("report").replaceChildren();$("report").hidden=true;$("downloads").hidden=true;$("empty-report").hidden=false;$("report-type").textContent="READY TO EXPLORE";error(""); }
function updateCount() { $("char-count").textContent=`${$("offer").value.length.toLocaleString()} / 10,000`; }
$("offer").addEventListener("input",updateCount);
for (const [tab,pane,otherTab,otherPane] of [["single-tab","single-pane","batch-tab","batch-pane"],["batch-tab","batch-pane","single-tab","single-pane"]]) {
  $(tab).addEventListener("click",()=>{$(pane).hidden=false;$(otherPane).hidden=true;$(tab).classList.add("selected");$(otherTab).classList.remove("selected");$(tab).setAttribute("aria-selected","true");$(otherTab).setAttribute("aria-selected","false");clearResult();});
}
$("example-warning").addEventListener("click",()=>{$("offer").value="Guaranteed 20% monthly profits. Act now! Contact us on WhatsApp.";$("website").value="";$("firm").value="Synthetic example — not a real firm";updateCount();clearResult();});
$("example-neutral").addEventListener("click",()=>{$("offer").value="Returns are not guaranteed. Investment values can fall. Read the prospectus before deciding.";$("website").value="";$("firm").value="";updateCount();clearResult();});
$("clear").addEventListener("click",()=>{$("offer-form").reset();updateCount();clearResult();});
$("clear-batch").addEventListener("click",()=>{$("csv-file").value="";clearResult();});
function showReport(report, mode) {
  lastReport=report;reportMode=mode;$("empty-report").hidden=true;$("report").hidden=false;$("report").replaceChildren();$("downloads").hidden=false;$("download-csv").hidden=mode!=="batch";
  $("report-type").textContent="VERIFICATION: NOT CHECKED";
  const box=$("report");
  if(mode==="single") {
    const count=report.findings.length;
    box.append(node("div",count?`${count} warning indicator${count===1?"":"s"} detected`:"No configured indicators matched",`result-heading ${count?"warn":""}`));
    box.append(node("p",count?"Review the matched evidence below. These signals do not prove fraud.":"This does not mean the offer is safe or legitimate. The rules cover only a limited set of patterns.","result-note"));
    for(const finding of report.findings){const card=node("div",undefined,"finding");const top=node("div",undefined,"finding-top");top.append(node("span",finding.severity.toUpperCase(),`badge ${finding.severity}`),node("span",finding.code.replaceAll("_"," ")));card.append(top,node("p",finding.explanation),node("pre",finding.evidence));box.append(card);}
    if(report.claimed_firm)box.append(node("p",`Claimed firm: ${report.claimed_firm}. Identity and permissions not checked.`,"result-note"));
    if(report.websites.length)box.append(node("p",`URL text only — not visited: ${report.websites.join(" · ")}`,"result-note"));
  } else {
    const s=report.summary;
    box.append(node("div","Batch review summary","result-heading"));const stats=node("div",undefined,"summary-stats");
    for(const [label,value] of [["Rows",s.total_rows],["With indicators",s.rows_with_indicators],["Input errors",s.input_error_rows]]){const stat=node("div",undefined,"stat");stat.append(node("b",String(value)),node("span",label));stats.append(stat);}box.append(stats,node("p","Counts are review outcomes, not fraud labels or accuracy. Summary excludes messages, firms, URLs and supplied IDs.","result-note"));
    const wrap=node("div",undefined,"table-wrap"),table=node("table"),thead=node("thead"),head=node("tr");for(const t of ["Row","Outcome","Indicators"]){head.append(node("th",t));}thead.append(head);table.append(thead);const tbody=node("tbody");
    for(const row of report.rows){const tr=node("tr");tr.append(node("td",String(row.row_number)),node("td",row.error||row.screening_status.replaceAll("_"," ")),node("td",row.finding_codes||"—"));tbody.append(tr);}table.append(tbody);wrap.append(table);box.append(wrap);
  }
}
async function callPython(mode,payload){
  py.globals.set("_smart_payload",JSON.stringify(payload));
  try {return JSON.parse(await py.runPythonAsync(mode==="single"?"json.dumps(scan_offer(**json.loads(_smart_payload)).as_dict())":"json.dumps(screen_csv(json.loads(_smart_payload)['csv_text'].encode('utf-8')))"));}
  finally {py.runPython("del _smart_payload");}
}
function explainError(e) {const text=String(e.message||e);return text.match(/(?:ValueError|TypeError): ([^\n]+)/)?.[1]||"The operation could not finish. Check the input or reload if the Python runtime failed.";}
$("offer-form").addEventListener("submit",async e=>{e.preventDefault();if(!py||busy)return;clearResult();setBusy(true);try{showReport(await callPython("single",{offer_text:$("offer").value,website_url:$("website").value,claimed_firm:$("firm").value}),"single");}catch(err){error(explainError(err));}finally{setBusy(false);}});
$("batch-button").addEventListener("click",async()=>{if(!py||busy)return;clearResult();const file=$("csv-file").files[0];if(!file){error("Choose a CSV file first.");return;}if(file.size>2*1024*1024){error("CSV exceeds the 2 MiB limit.");return;}setBusy(true);try{const csv=new TextDecoder("utf-8",{fatal:true}).decode(await file.arrayBuffer());showReport(await callPython("batch",{csv_text:csv}),"batch");}catch(err){error(err instanceof TypeError?"CSV must use UTF-8 encoding.":explainError(err));}finally{setBusy(false);}});
function download(name,data,type){const url=URL.createObjectURL(new Blob([data],{type}));const a=node("a");a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$("download-json").addEventListener("click",()=>{if(lastReport)download("smartinvest-screening.json",JSON.stringify(lastReport,null,2),"application/json");});
$("download-csv").addEventListener("click",async()=>{if(!lastReport||reportMode!=="batch"||busy)return;setBusy(true);py.globals.set("_smart_payload",JSON.stringify(lastReport));try{const csv=await py.runPythonAsync("summary_csv(json.loads(_smart_payload)).decode('utf-8')");download("smartinvest-batch-summary.csv",csv,"text/csv");}catch(e){error(explainError(e));}finally{py.runPython("del _smart_payload");setBusy(false);}});
async function initialise(){
  try{
    if(typeof loadPyodide!=="function")throw new Error("Runtime download unavailable");
    py=await loadPyodide({indexURL:"https://cdn.jsdelivr.net/pyodide/v0.29.0/full/"});
    const manifest=await fetch("engine-manifest.json").then(r=>{if(!r.ok)throw new Error("Missing engine manifest");return r.json();});
    py.FS.mkdirTree("/app/smartinvest");
    for(const file of manifest.files){const response=await fetch(file.path);if(!response.ok)throw new Error("Missing Python engine asset");const bytes=new Uint8Array(await response.arrayBuffer());const digest=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes))).map(x=>x.toString(16).padStart(2,"0")).join("");if(digest!==file.sha256)throw new Error("Engine asset checksum mismatch");py.FS.writeFile("/app/smartinvest/"+file.name,bytes);}
    py.runPython("import sys, json\nsys.path.insert(0, '/app')\nfrom smartinvest.detection import scan_offer, ENGINE_VERSION\nfrom smartinvest.batch import screen_csv, summary_csv");
    runtime.textContent="Python ready · engine "+py.runPython("ENGINE_VERSION");runtime.className="runtime ready";setBusy(false);
    window.smartInvestDemo={engineVersion:py.runPython("ENGINE_VERSION"),runtimeVersion:py.version};
  }catch(e){py=null;runtime.textContent="Python could not load";runtime.className="runtime failed";error("The Python runtime could not load. Check your connection and reload. No scan was performed.");}
}
initialise();
