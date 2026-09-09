// Run with node tests/ui-contract.cjs. Uses only Node built-ins.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('app/index.html','utf8');
const guide=fs.readFileSync('app/guide.html','utf8');
for(const m of html.replace(/<!--[\s\S]*?-->/g,'').matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g))new vm.Script(m[1]);
new vm.Script(fs.readFileSync('app/guide.js','utf8'));
const ids=new Set([...guide.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]));
for(const m of html.matchAll(/guide\.html#([a-z0-9-]+)["']/g))assert(ids.has(m[1]),'Missing guide anchor '+m[1]);
for(const id of ['lst','green','pop','pct65','ac','access','score','holc','planting','cost','weights'])assert(ids.has(id));
const data=JSON.parse(fs.readFileSync('data/bakersfield.geojson','utf8'));
const nodes=new Map();const node=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',value:25,disabled:false,setAttribute(){}});return nodes.get(id);};
const ctx={document:{getElementById:node},TREE_SPACING_M:10,TREE_M2:40,COST_TREE:500,areaOf:p=>p.area_m2,fInt:n=>Math.round(n).toLocaleString('en-US'),fTempD:v=>v.toFixed(2)+' C'};
vm.createContext(ctx);
const start=html.indexOf('const plantingShares=new Map();'),end=html.indexOf('function wireHover()',start);
vm.runInContext(html.slice(start,end),ctx);
let cases=0;
for(const f of data.features){const p=f.properties;let last=0;for(const share of [0,25,50,100]){node('roi-slider').value=share;node('roi-slider').disabled=!(p.street_m>0);ctx.p=p;vm.runInContext('updateROI(p)',ctx);if(!p.scenario_ok){assert.equal(node('roi-trees').textContent,'—');assert.equal(node('roi-cost').textContent,'—');assert.match(node('roi-note').textContent,/mapped street capacity/);cases++;continue;}const trees=Number(node('roi-trees').textContent.replaceAll(',',''));assert(trees>=last);assert(trees<=Math.floor((p.street_m||0)*2/10));const known=p.canopy_baseline_ok?Math.max(p.canopy_m2,p.green/100*p.area_m2):p.canopy_source==='usfs-2022'?p.canopy_m2:0;assert(trees*40<=Math.max(0,p.area_m2-known)+1);if(!p.canopy_baseline_ok&&trees>0)assert(!node('roi-note').textContent.includes('→'));assert(!/NaN|Infinity/.test([...nodes.values()].map(n=>n.textContent).join(' ')));if(share===0){assert.equal(trees,0);assert.equal(node('roi-cost').textContent,'$0');}last=trees;cases++;}}
assert.equal(data.features.filter(f=>f.properties.place==='res').length,3788);
assert.equal(data.features.filter(f=>f.properties.holc).length,0);
assert.equal(data.features.filter(f=>f.properties.place==='res'&&f.properties.green_src==='ndvi').length,0);
console.log(`PASS: syntax, guide anchors, residential count, HOLC availability, ${cases} scenario cases across ${data.features.length} cells.`);

// Rebuild invariants: stable geography/IDs, complete current schema, consecutive ranks.
const cp=require('node:child_process');
const original=JSON.parse(cp.execFileSync('git',['show','HEAD:data/bakersfield.geojson'],{maxBuffer:20*1024*1024,encoding:'utf8'}));
assert.deepEqual(data.features.map(f=>[f.properties.id,f.geometry]),original.features.map(f=>[f.properties.id,f.geometry]));
const ranked=data.features.filter(f=>f.properties.place==='res');
assert.deepEqual(ranked.map(f=>f.properties.rank).sort((a,b)=>a-b),Array.from({length:ranked.length},(_,i)=>i+1));
for(const f of data.features){assert(['canopy','ndvi'].includes(f.properties.green_src));assert.equal(typeof f.properties.scenario_ok,'boolean');}
console.log('PASS: stable geography, source/coverage metadata and consecutive rebuilt ranks.');
// Execute the actual browser scorer against the export, including its rounding and tie policy.
const live={score:new Map(),rank:new Map(),order:[]};
const scoring={HEX:data,svals:data.norm,LIVE:live,POPW:.45,normW:()=>({heat:.35,green:.25,ac:.25,age65:.15,access:0})};
scoring.svals.access_min=[0,Math.max(...data.features.map(f=>f.properties.access_min))];
vm.createContext(scoring);
vm.runInContext(html.slice(html.indexOf('function rescore(){'),html.indexOf('const sc=p=>')),scoring);
vm.runInContext('rescore()',scoring);
for(const f of ranked){const p=f.properties;assert.equal(live.rank.get(p.id),p.rank,'Browser/export rank mismatch '+p.id);assert(Math.abs(live.score.get(p.id)-p.score)<=.050001);}
console.log('PASS: browser/export scoring and rank parity for every residential cell.');

assert(!html.includes("+' pts'"));assert(html.includes('percentage-point canopy gain'));
const directory=fs.readFileSync('app/cooling.html','utf8');for(const m of directory.matchAll(/<script>([\s\S]*?)<\/script>/g))new vm.Script(m[1]);

// Export (CE-06): the builder runs against the export, the CSV is well-formed and
// carries the weights, and a reload of its own JSON is accepted while a foreign
// city or schema is refused.
{
  const ex={HEX:data,LIVE:{score:new Map(),rank:new Map(),order:[]},POPW:.45,W_INPUTS:[{k:'heat'},{k:'green'},{k:'ac'},{k:'age65'},{k:'access'}],
    CITY_NAV:[{slug:'x',name:'X'}],THIS_CITY:'x',CITY_SLUG:'x',DATA_URL:'../data/x.geojson?v=t',TREE_SPACING_M:10,TREE_M2:40,COST_TREE:500,
    nameOf:p=>p.name,areaOf:p=>p.area_m2,isDefaultW:()=>true,matchPreset:()=>({id:'default'}),selId:null,
    document:{getElementById:()=>null,createElement:()=>({click(){},remove(){},style:{}}),body:{appendChild(){}}},
    Blob:function(){},URL:{createObjectURL:()=>'blob:',revokeObjectURL(){}},crypto:{subtle:{digest:async()=>new ArrayBuffer(32)}},TextEncoder,
    applyWeights(){},selectHex(){},setTimeout};
  ex.normW=()=>({heat:.2,green:.5,ac:.2,age65:.1,access:0});
  ex.sc=p=>ex.LIVE.score.get(p.id);ex.rk=p=>ex.LIVE.rank.get(p.id);
  vm.createContext(ex);
  vm.runInContext(html.slice(html.indexOf('const plantingShares=new Map();'),html.indexOf('function updateROI(p){')),ex);
  vm.runInContext(html.slice(html.indexOf('const EXPORT_SCHEMA='),html.indexOf('async function boot(){')),ex);
  const res=data.features.filter(f=>f.properties.place==='res');
  res.forEach((f,i)=>{ex.LIVE.score.set(f.properties.id,100-i/res.length*100);ex.LIVE.rank.set(f.properties.id,i+1);});
  ex.LIVE.order=res;
  const cell=res.find(f=>f.properties.scenario_ok)||res[0];
  ex.cellId=cell.properties.id;vm.runInContext('plantingShares.set(cellId,50)',ex);
  const header=vm.runInContext('exportHeader()',ex);
  assert.equal(header.export_schema,1);assert.equal(header.dataset.cells,data.features.length);assert.equal(header.dataset.ranked_cells,res.length);
  assert.deepEqual(Object.keys(header.weights),['heat','green','ac','age65','access']);
  ex.cellP=cell.properties;const rec=vm.runInContext('cellRecord(cellP)',ex);
  for(const k of vm.runInContext('EXPORT_FIELDS',ex))assert(k in rec,'export field '+k);
  assert.equal(rec.rank,ex.LIVE.rank.get(cell.properties.id));
  if(cell.properties.scenario_ok){assert.equal(rec.planting_share,50);assert(rec.trees>=0);assert.equal(rec.cost_usd,rec.trees*500);}
  ex.recs=res.slice(0,5).map(f=>vm.runInContext('cellRecord',ex)(f.properties));ex.header=header;
  const csv=vm.runInContext('toCsv(recs,header)',ex).split('\r\n').filter(Boolean);
  assert.equal(csv.length,6);const cols=csv[0].split(',');assert(cols.includes('w_green')&&cols.includes('dataset_sha256'));
  for(const line of csv.slice(1))assert.equal(line.split(',').length,cols.length,'CSV column count');
  ex.doc={...header,kind:'ranked-list',cells:ex.recs};
  assert.equal(vm.runInContext('loadScenario(doc).ok',ex),true);
  ex.bad={...header,city_slug:'elsewhere'};assert.equal(vm.runInContext('loadScenario(bad).ok',ex),false);
  ex.old={...header,export_schema:0};assert.equal(vm.runInContext('loadScenario(old).ok',ex),false);
  assert.equal(vm.runInContext('plantingShares.get(cellP.id)',ex),50);
  console.log('PASS: scenario export builder, CSV shape, and reload acceptance/refusal.');
}
