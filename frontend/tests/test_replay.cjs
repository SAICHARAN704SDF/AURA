// Exercise the replay handler with a DOM stub: no browser or network is launched.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('frontend/app.js','utf8');
const code=source.slice(source.indexOf("$('replay').addEventListener"),source.indexOf("$('direction').addEventListener"));
const calls=[],elements={},state={events:[],replaying:false};let handler,shown;
const $=id=>elements[id]??=( {value:'test',addEventListener:(name,fn)=>handler=fn} );
const workflow={id:'w',plan:{tasks:[]},state:'COMPLETED',tokens:42};
const context={$,state,encodeURIComponent,setTimeout:fn=>fn(),async api(path,options){assert.equal(options,undefined);calls.push(path);if(path.startsWith('/monitor/'))return [workflow];if(path.includes('/events'))return {events:[{type:'planning'},{type:'verification',outcome:'PASS'}]};return workflow;},reset(){state.events=[];},busy(){},notice(){},addEvents(rows){state.events.push(...rows)},output(value){shown=value},formatWorkflow:()=>'',renderFlow(){}};
vm.createContext(context);vm.runInContext(code,context);
(async()=>{await handler();assert.equal(calls.length,3);assert.ok(calls.every(p=>!p.includes('/execute')));assert.equal(shown,workflow);assert.equal(elements.runState.textContent,'REPLAY FINISHED');assert.equal(state.replaying,false);console.log('Replay reads stored state only; no generation or execution requests.');})().catch(e=>{console.error(e);process.exitCode=1});
