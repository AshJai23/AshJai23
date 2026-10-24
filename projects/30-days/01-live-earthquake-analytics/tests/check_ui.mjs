// Test-only DOM harness, using recorded real API responses. Not a runtime dependency.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const {parseHTML}=await import(process.env.LINKEDOM_TEST_MODULE || 'linkedom');

const html=fs.readFileSync('static/index.html','utf8');
const {document,window}=parseHTML(html);
// Linkedom omits native select-value assignment; provide browser-equivalent selection semantics.
const proto=window.HTMLSelectElement.prototype;
Object.defineProperty(proto,'value',{configurable:true,get(){return [...this.querySelectorAll('option')].find(o=>o.hasAttribute('selected'))?.getAttribute('value')??this.querySelector('option')?.getAttribute('value')??''},set(value){for(const option of this.querySelectorAll('option'))option.toggleAttribute('selected',option.getAttribute('value')===String(value))}});
const config={current_year:2026,minimum_year:2000,maximum_predict_year:2029,countries:[{code:'GBR',name:'United Kingdom',latitude:51.5074,longitude:-.1278,location:'London'},{code:'IND',name:'India',latitude:28.6139,longitude:77.2090,location:'New Delhi'}]};
let hold=false,release;
const mockedFetch=async url=>{
 const u=new URL(url,'http://localhost');let data;
 if(u.pathname==='/api/config')data=config;
 else if(u.pathname==='/api/map')data=JSON.parse(fs.readFileSync('data/countries.geojson','utf8'));
 else {const c=(u.searchParams.get('country')||'GBR').toLowerCase();const kind=u.pathname==='/api/earthquakes'?'earthquakes':u.pathname==='/api/predict'?'outlook-'+u.searchParams.get('year'):'forecast';data=JSON.parse(fs.readFileSync('examples/'+c+'-'+kind+'.json','utf8'));if(hold)await new Promise(resolve=>release=resolve)}
 return {ok:true,json:async()=>structuredClone(data)};
};
const context=vm.createContext({document,window,fetch:mockedFetch,URL,URLSearchParams,Blob,setTimeout,console});
vm.runInContext(html.split('<script>')[1].split('</script>')[0],context);
await new Promise(resolve=>setTimeout(resolve,30));
const $=id=>document.getElementById(id);
assert.equal($('country').value,'GBR');
assert.equal($('year').value,'2027');
await $('loadForecast').onclick();
assert.match($('weatherContent').textContent,/PROVIDER FORECAST/);
assert.equal($('weatherContent').querySelectorAll('tbody tr').length,7);
$('country').value='IND';$('country').dispatchEvent(new window.Event('change'));
assert.match($('weatherContent').textContent,/Selection changed/);
assert.equal(Number($('latitude').value),28.6139);
await $('predictYear').onclick();
assert.equal($('predictContent').querySelector('tbody').querySelectorAll('tr').length,12);
assert.match($('predictContent').textContent,/2024 & 2025/);
await $('loadQuakes').onclick();
assert.match($('quakeContent').textContent,/India/);
hold=true;const pending=$('loadForecast').onclick();
await new Promise(resolve=>setTimeout(resolve,0));
$('country').value='GBR';$('country').dispatchEvent(new window.Event('change'));release();await pending;
assert.match($('status').textContent,/Selection changed while loading/);
assert(!/PROVIDER FORECAST/.test($('weatherContent').textContent));
console.log('UI checks passed: defaults, country change, weather table, 12-month prediction, country events, and stale-response protection.');
