(function(root){
  'use strict';
  const airports=['BOS','DEN','LAX','ORD','SEA'];
  function features(r){
    if(!Number.isFinite(r.layover)||r.layover<45||r.layover>240||!Number.isFinite(r.hour)||r.hour<0||r.hour>=24||!Number.isInteger(r.weekday)||r.weekday<0||r.weekday>6||!airports.includes(r.origin)||!airports.includes(r.dest)||r.origin===r.dest)throw Error('Outside model scope');
    return [r.layover/60,60/r.layover,Math.sin(2*Math.PI*r.hour/24),Math.cos(2*Math.PI*r.hour/24),Number(r.weekday>=5),...airports.map(a=>Number(a===r.origin)),...airports.map(a=>Number(a===r.dest))];
  }
  function predict(r,m){const x=features(r);const z=m.intercept+x.reduce((s,v,i)=>s+v*m.coef[i],0);return 1/(1+Math.exp(-Math.max(-700,Math.min(700,m.cal_intercept+m.cal_coef*z))));}
  const api={features,predict};if(typeof module!=='undefined')module.exports=api;else root.FlightGuard=api;
})(typeof globalThis!=='undefined'?globalThis:this);
