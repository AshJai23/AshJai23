// DOM checks with mocked HTTP responses replayed from the real live smoke run.
// This is not a browser layout/accessibility audit.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const {parseHTML}=await import(process.env.LINKEDOM_MODULE || 'linkedom');
const {window}=parseHTML(fs.readFileSync('static/index.html','utf8'));
const sample=JSON.parse(fs.readFileSync('examples/trained-live-smoke.json','utf8')).responses[0];
const requests=[];
let fail=false;
const fetch=async(url,options={})=>{
  requests.push([url,options]);
  if(url==='/healthz')return {json:async()=>({data_mode:'live',llm_enabled:true})};
  if(url==='/api/feedback')return {ok:true,json:async()=>({saved:true})};
  if(fail)return {ok:false,status:429,json:async()=>({detail:'wait'})};
  return {ok:true,json:async()=>structuredClone(sample)};
};
vm.runInNewContext(fs.readFileSync('static/app.js','utf8'),{document:window.document,fetch,console,Error,Math});
const flush=()=>new Promise(resolve=>setImmediate(resolve));
await flush();
const doc=window.document;
assert.match(doc.querySelector('#service-status').textContent,/TRAINED QWEN ROUTER ENABLED/);
for(const button of doc.querySelectorAll('[data-question]')){
  button.dispatchEvent(new window.Event('click'));
  assert.equal(doc.querySelector('#question').value,button.dataset.question);
}
doc.querySelector('#ask-form').dispatchEvent(new window.Event('submit',{cancelable:true}));
assert.equal(doc.querySelector('#submit').disabled,true);
await flush();await flush();
assert.equal(doc.querySelectorAll('.guidance-card').length,1);
assert.match(doc.querySelector('#results').textContent,/18 months/);
assert.match(doc.querySelector('#results').textContent,/trained_qwen_head/);
assert.equal(doc.querySelector('.source a').getAttribute('href'),'https://www.gov.uk/graduate-visa');
assert.equal(doc.querySelector('#submit').disabled,false);
doc.querySelector('.feedback button').dispatchEvent(new window.Event('click'));
await flush();
assert.match(doc.querySelector('.feedback').textContent,/recorded/);
assert.ok(requests.some(r=>r[0]==='/api/feedback'));
fail=true;
doc.querySelector('#ask-form').dispatchEvent(new window.Event('submit',{cancelable:true}));
await flush();
assert.match(doc.querySelector('#loading').textContent,/wait a minute/);
assert.equal(doc.querySelector('#submit').disabled,false);
console.log('UI DOM checks passed: examples, submission, busy state, real-source card rendering, provenance link, feedback, rate-limit recovery. HTTP mocked; no browser rendering claimed.');
