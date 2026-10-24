'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element {
  constructor(){this.children=[];this.attributes={};this.style={};this.value='';this.listeners={};}
  append(...values){this.children.push(...values);}
  replaceChildren(...values){this.children=values;}
  setAttribute(k,v){this.attributes[k]=String(v);}
  addEventListener(k,v){this.listeners[k]=v;}
}
const elements={};
const document={getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element(),createElementNS:()=>new Element()};
const requests=[];
const context=vm.createContext({document,performance:{now:()=>0},setInterval:()=>1,clearInterval:()=>{},fetch:url=>new Promise(resolve=>requests.push({url,resolve}))});
vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),context);
const flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  if(process.argv[3]==='phase'){
    vm.runInContext("frames=[{capture_time_ns:0,decision_time_ns:1,completion_time_ns:10000000},{capture_time_ns:10000000,decision_time_ns:10000001,completion_time_ns:20000000}];current=0;lineChart('curvature',[{name:'PRE',phase:'CAPTURE',values:[0,1]},{name:'POST',phase:'COMPLETION',values:[0,1]}]);",context);
    const paths=elements.curvature.children.filter(n=>n.attributes.d);
    assert.equal(Number(paths[0].attributes.d.match(/^M([^,]+)/)[1]),42);
    assert.equal(Number(paths[1].attributes.d.match(/^M([^,]+)/)[1]),450);
    assert.ok(paths[1].attributes.d.includes('L858,'));
  }else if(process.argv[3]==='switch'){
    vm.runInContext("catalog={campaigns:[{campaign_id:'A'},{campaign_id:'B'}]};frames=[{frame_index:1}];run={old:true};",context);
    elements.campaign.value='A';const a=vm.runInContext('selectCampaign()',context);
    assert.equal(vm.runInContext('frames.length',context),0);
    assert.equal(elements.play.disabled,true);
    elements.campaign.value='B';const b=vm.runInContext('selectCampaign()',context);
    vm.runInContext("loadScenario=async()=>{};",context);
    requests.find(x=>x.url==='/api/campaigns/B/scenarios').resolve({ok:true,json:async()=>({scenarios:[{scenario:'B-only'}]})});
    await flush();
    requests.find(x=>x.url==='/api/campaigns/A/scenarios').resolve({ok:true,json:async()=>({scenarios:[{scenario:'A-stale'}]})});
    await Promise.all([a,b]);
    assert.equal(elements.scenario.children[0].value,'B-only');
  }else if(process.argv[3]==='emptyplay'){
    vm.runInContext('frames=[];play();',context);
    assert.equal(vm.runInContext('timer',context),null);
  }
  process.stdout.write('PASS '+process.argv[3]+'\n');
})().catch(e=>{process.stderr.write(String(e.stack));process.exitCode=1;});
