const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..'),scoring=require('../web/scoring.js');
const model=JSON.parse(fs.readFileSync(path.join(root,'web/model.json'))),rows=JSON.parse(fs.readFileSync(path.join(root,'web/replay.json')));
let max=0;
for(const r of rows)for(const [target,key] of [['failure','risk'],['disruption','disruption_risk']]){
  const error=Math.abs(scoring.predict(r,model.models[target])-r[key]);max=Math.max(max,error);assert.ok(error<1e-12);
}
for(const update of [{layover:NaN},{hour:24},{weekday:7},{origin:'XYZ'}])assert.throws(()=>scoring.predict({...rows[0],...update},model.models.failure));
console.log(JSON.stringify({itineraries:rows.length,predictions_checked:rows.length*2,max_absolute_error:max}));
