'use strict';
const $=id=>document.getElementById(id),pct=x=>(100*x).toFixed(1)+'%',esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const zones={BOS:'America/New_York',ATL:'America/New_York',ORD:'America/Chicago',DEN:'America/Denver',LAX:'America/Los_Angeles',SEA:'America/Los_Angeles'};
let replay=[],model,evaluation,selected=null,filtered=[],saved=[];
function time(iso,airport,full=false){return new Intl.DateTimeFormat('en-US',{timeZone:zones[airport],hour:'2-digit',minute:'2-digit',hour12:false,...(full?{month:'short',day:'numeric',timeZoneName:'short'}:{})}).format(new Date(iso));}
function duration(v){return Math.floor(v/60)+'h '+Math.round(v%60)+'m';}
function persist(){try{localStorage.setItem('flightguard-shortlist-v1',JSON.stringify(saved));$('storage-status').textContent='';}catch(e){$('storage-status').textContent='Browser storage is unavailable. Your shortlist will last only for this session.';}}
function card(r){return `<article class="card ${selected?.id===r.id?'active':''}" tabindex="0" role="button" aria-label="Inspect ${esc(r.inbound)} to ${esc(r.outbound)}, ${pct(r.risk)} modeled failure risk" data-id="${esc(r.id)}"><div class="card-top"><small>${esc(r.inbound)} → ${esc(r.outbound)} · VIA ATL</small><div class="risk">${pct(r.risk)}<small>MODELED FAILURE RISK</small></div></div><div class="schedule"><span>${time(r.departure_utc,r.origin)}</span><span>→</span><span>${time(r.arrival_utc,r.dest)}</span></div><div class="card-bottom"><span>${duration(r.duration)} total · ${r.layover}m layover</span><span class="badge">${pct(r.disruption_risk)} disruption</span></div><small style="color:var(--muted);font-size:10px">${time(r.arrival_utc,r.dest,true)} arrival · local airport times</small>${$('reveal').checked?`<div class="actual">Recorded synthetic outcome: ${esc(r.reason)}</div>`:''}</article>`;}
function renderResults(){
  $('result-count').textContent=filtered.length+' historical options · DL-operated flights';
  $('results').innerHTML=filtered.length?filtered.map(card).join(''):'<p class="empty">No eligible connections for these filters. Choose different airports or a date from March 3–31, 2025.</p>';
  for(const el of $('results').querySelectorAll('[data-id]')){
    const select=()=>{selected=replay.find(r=>r.id===el.dataset.id);renderResults();renderDetail();};
    el.addEventListener('click',select);el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select();}});
  }
}
function filter(){
  if(!model)return;
  filtered=replay.filter(r=>r.origin===$('origin').value&&r.dest===$('dest').value&&r.date===$('date').value).sort((a,b)=>a[$('sort').value]-b[$('sort').value]||a.duration-b.duration||a.id.localeCompare(b.id));
  selected=filtered.find(r=>r.id===selected?.id)||filtered[0]||null;renderResults();renderDetail();
}
function renderDetail(){
  if(!selected){$('detail').innerHTML='<h3>No itinerary selected</h3><p>Adjust the route and departure date to explore this historical sample.</p>';return;}
  const r=selected,m=model.models.failure,x=FlightGuard.features(r);
  const factors=m.features.map((name,i)=>({name,value:x[i]*m.coef[i]*m.cal_coef})).filter(f=>f.value!==0).sort((a,b)=>Math.abs(b.value)-Math.abs(a.value)).slice(0,4);
  const alt=replay.filter(a=>a.group===r.group&&a.id!==r.id);
  $('detail').innerHTML=`<div class="eyebrow">ITINERARY INSPECTION</div><div class="detail-title"><h3>${esc(r.origin)} → ATL → ${esc(r.dest)}</h3><button id="save" class="secondary">${saved.includes(r.id)?'Remove saved':'Save route +'}</button></div><p>${esc(r.date)} · ${esc(r.inbound)} / ${esc(r.outbound)}</p><div class="timeline"><div>${time(r.departure_utc,r.origin,true)}<small>Depart ${esc(r.origin)}</small></div><div>${time(r.hub_arrival_utc,'ATL',true)}<small>Arrive ATL · ${r.layover} minute scheduled layover</small></div><div>${time(r.hub_departure_utc,'ATL',true)}<small>Depart ATL</small></div><div>${time(r.arrival_utc,r.dest,true)}<small>Arrive ${esc(r.dest)}</small></div></div><h4>What contributes to this score?</h4><div class="factors">${factors.map(f=>`<div class="factor"><span>${esc(f.name)}</span><b class="${f.value<0?'negative':''}">${f.value>0?'+':''}${f.value.toFixed(2)} log-odds</b></div>`).join('')}</div><p>Signed terms in the calibrated model, relative to its intercept. These are associations, not causal explanations or percentage-point changes.</p><h4>Buffer sensitivity</h4><div class="whatif"><label>Hypothetical layover: <output id="buffer-label">${r.layover} min</output><input id="buffer" type="range" min="45" max="240" step="1" value="${r.layover}"></label><p id="buffer-score"></p><small>Changes only layover while holding other model inputs fixed. Not an available flight or a calibrated causal intervention.</small></div><h4>Same-inbound alternatives</h4>${alt.length?alt.map(a=>`<p>${esc(a.outbound)} · ${a.layover}m layover · ${pct(a.risk)} modeled failure risk · ${duration(a.duration)} total</p>`).join(''):'<p>No second sampled onward option.</p>'}${$('reveal').checked?`<div class="actual"><strong>${esc(r.reason)}</strong><p>Inbound arrival delay: ${r.inbound_arr_delay??'not reported'}m<br>Outbound departure delay: ${r.outbound_dep_delay??'not reported'}m<br>Outbound arrival delay: ${r.outbound_arr_delay??'not reported'}m</p></div>`:''}`;
  $('save').onclick=()=>{if(saved.includes(r.id))saved=saved.filter(id=>id!==r.id);else if(saved.length<3)saved.push(r.id);else{$('storage-status').textContent='Shortlist is full. Remove a saved route before adding another.';return;}persist();renderSaved();renderDetail();};
  const update=()=>{const lay=Number($('buffer').value);$('buffer-label').textContent=lay+' min';$('buffer-score').textContent=pct(FlightGuard.predict({...r,layover:lay},m))+' modeled failure risk';};$('buffer').oninput=update;update();
}
function renderSaved(){
  $('saved').innerHTML=saved.length?saved.map(id=>{const r=replay.find(a=>a.id===id);return `<div class="saved-card"><button class="secondary" aria-label="Remove saved ${esc(r.inbound)}" data-remove="${esc(id)}">×</button><strong>${esc(r.origin)} → ${esc(r.dest)}</strong><br>${esc(r.date)} · ${esc(r.inbound)} / ${esc(r.outbound)}<br>${pct(r.risk)} modeled failure · ${r.layover}m buffer</div>`;}).join(''):'<p class="empty">Save an itinerary to keep it here.</p>';
  $('export').disabled=!saved.length;
  for(const b of $('saved').querySelectorAll('[data-remove]'))b.onclick=()=>{saved=saved.filter(id=>id!==b.dataset.remove);persist();renderSaved();renderDetail();};
}
function evidence(){
  const e=evaluation;
  $('metrics').innerHTML=[['Real source flights',e.source_flights.toLocaleString(),'Selected from official BTS archives'],['Held-out connections',e.failure.n.toLocaleString(),'Synthetic itineraries · March 2025'],['Failure ROC AUC',e.failure.roc_auc.toFixed(3),'Layover baseline: '+e.layover_baseline.roc_auc.toFixed(3)],['Failure Brier score',e.failure.brier.toFixed(4),'Lower is better · baseline '+e.layover_baseline.brier.toFixed(4)]].map(([label,v,note])=>`<div class="metric"><span>${label}</span><strong>${v}</strong><small>${note}</small></div>`).join('');
  const x=v=>45+v*470,y=v=>210-v*190;
  $('calibration').innerHTML=`<svg viewBox="0 0 550 255" role="img" aria-label="Calibration plot comparing predicted and observed failure risk"><path d="M45 20V210H515" fill="none" stroke="#536777"/><path d="M45 210L515 20" stroke="#536777" stroke-dasharray="4 4"/>${[0,.25,.5,.75,1].map(v=>`<text x="${x(v)}" y="229" text-anchor="middle" fill="#a4b4c4" font-size="10">${Math.round(v*100)}%</text><text x="35" y="${y(v)+3}" text-anchor="end" fill="#a4b4c4" font-size="10">${Math.round(v*100)}%</text>`).join('')}${e.failure.calibration_bins.map(b=>`<circle cx="${x(b.predicted)}" cy="${y(b.observed)}" r="${Math.max(3,Math.min(11,Math.sqrt(b.n)/6))}" fill="#a9efdf"><title>Predicted ${pct(b.predicted)}, observed ${pct(b.observed)}, n=${b.n}</title></circle>`).join('')}<text x="280" y="249" fill="#a4b4c4" font-size="10" text-anchor="middle">Predicted risk → (vertical axis: observed rate)</text></svg><p>ECE (10 equal-width bins): ${pct(e.failure.ece_10)}. Small high-risk bins carry more uncertainty; inspect their counts before drawing conclusions.</p>`;
  const policy=e.policy_comparison;
  $('policy').innerHTML=`<table><thead><tr><th>Selection rule</th><th>Failure</th><th>Disruption</th><th>Mean trip</th></tr></thead><tbody>${[['shortest','Shortest'],['lowest_failure_risk','Lower failure risk'],['lowest_disruption_risk','Lower disruption risk']].map(([k,label])=>`<tr><td>${label}</td><td>${pct(policy[k].failure_rate)}</td><td>${pct(policy[k].disruption_rate)}</td><td>${Math.round(policy[k].mean_scheduled_minutes)}m</td></tr>`).join('')}</tbody></table><p>${policy.shortest.groups.toLocaleString()} matched alternative sets. Both risk rules chose the same options in this test. The fuller model does not beat the simpler layover-only baseline on Brier score or AUC; do not interpret complexity as improvement.</p>`;
}
$('filters').onsubmit=e=>{e.preventDefault();filter();};$('reveal').onchange=()=>{renderResults();renderDetail();};
$('export').onclick=()=>{
  const fields=['date','origin','dest','inbound','outbound','layover','duration','risk','disruption_risk',...($('reveal').checked?['failure','disruption','reason']:[])];
  const quote=v=>'"'+String(v??'').replaceAll('"','""')+'"';
  const text=[fields.join(','),...saved.map(id=>{const r=replay.find(a=>a.id===id);return fields.map(f=>quote(r[f])).join(',');})].join('\n');
  const url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='flightguard-historical-shortlist.csv';a.click();URL.revokeObjectURL(url);
};
async function start(){
  try{
    [replay,model,evaluation]=await Promise.all(['replay.json','model.json','evaluation.json'].map(async f=>{const r=await fetch(f);if(!r.ok)throw Error(f+' unavailable');return r.json();}));
    try{const s=JSON.parse(localStorage.getItem('flightguard-shortlist-v1')||'[]');saved=Array.isArray(s)?[...new Set(s.filter(id=>replay.some(r=>r.id===id)))].slice(0,3):[];}catch(e){saved=[];$('storage-status').textContent='Could not restore local shortlist.';}
    $('dataset-status').textContent=evaluation.source_flights.toLocaleString()+' VERIFIED FLIGHTS · MAR 2025 REPLAY';filter();renderSaved();evidence();
  }catch(e){$('dataset-status').textContent='Data could not load. Serve the web folder over HTTP and reload.';$('results').innerHTML='<p class="empty">The app needs its bundled JSON files. Run python -m http.server 8000 --directory web from the repository root.</p>';}
}
start();
