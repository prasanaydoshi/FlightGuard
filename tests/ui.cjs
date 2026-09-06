// DOM-level UI tests, NOT a rendered-browser or pixel-layout test.
const {JSDOM}=require('jsdom'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../web');
const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'https://flightguard.test/',runScripts:'outside-only'});
const w=dom.window,d=w.document;
w.fetch=async name=>({ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(root,name),'utf8'))});
w.eval(fs.readFileSync(path.join(root,'scoring.js'),'utf8'));
w.eval(fs.readFileSync(path.join(root,'app.js'),'utf8'));
const tick=()=>new Promise(resolve=>setTimeout(resolve,0));
async function test(){
 await tick();assert.match(d.getElementById('dataset-status').textContent,/6,601/);
 assert.ok(d.querySelectorAll('.card').length>0);assert.equal(d.querySelectorAll('.actual').length,0);
 d.getElementById('reveal').checked=true;d.getElementById('reveal').dispatchEvent(new w.Event('change'));assert.ok(d.querySelectorAll('.actual').length>0);
 d.getElementById('save').click();assert.equal(d.querySelectorAll('.saved-card').length,1);assert.equal(JSON.parse(w.localStorage.getItem('flightguard-shortlist-v1')).length,1);
 d.getElementById('buffer').value='45';d.getElementById('buffer').dispatchEvent(new w.Event('input'));assert.match(d.getElementById('buffer-label').textContent,/45 min/);assert.match(d.getElementById('buffer-score').textContent,/modeled failure/);
 d.getElementById('sort').value='duration';d.getElementById('filters').dispatchEvent(new w.Event('submit',{cancelable:true}));
 const cards=[...d.querySelectorAll('.card')];assert.ok(cards.length>1);cards[1].dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));assert.ok(cards[1].dataset.id===d.querySelector('.card.active').dataset.id);
 d.getElementById('dest').value='BOS';d.getElementById('filters').dispatchEvent(new w.Event('submit',{cancelable:true}));assert.equal(d.querySelectorAll('.card').length,0);assert.match(d.getElementById('results').textContent,/No eligible/);
 d.querySelector('[data-remove]').click();assert.equal(d.querySelectorAll('.saved-card').length,0);assert.ok(d.getElementById('export').disabled);
 assert.ok(d.querySelectorAll('#calibration circle').length>0);assert.equal(d.querySelectorAll('#policy tbody tr').length,3);
 console.log('DOM UI checks passed: initial render, hidden/revealed outcomes, shortlist persistence, buffer scenario, sorting, keyboard selection, empty state, removal, evidence panels.');
 dom.window.close();
}
test().catch(e=>{console.error(e);process.exitCode=1;dom.window.close();});
