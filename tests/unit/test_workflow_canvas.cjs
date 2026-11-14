// Pure DOM-stub test of dependency layout; does not launch or automate a browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('frontend/app.js', 'utf8');
const code = source.slice(source.indexOf('function renderFlow(){'), source.indexOf("$('mode').addEventListener('change',renderFlow)"));
function element(){return {children:[],style:{},attrs:{},append(...items){this.children.push(...items)},replaceChildren(...items){this.children=items},setAttribute(k,v){this.attrs[k]=v},addEventListener(){}};}
const elements={flow:element(),stages:element(),mode:{value:'report'}};
const state={events:[],stageStates:new Map(),plan:{tasks:[
 {id:'C',agent:'analysis',description:'Combine evidence',dependencies:['A','B']},
 {id:'A',agent:'research',description:'Find A',dependencies:[]},
 {id:'B',agent:'research',description:'Find B',dependencies:[]},
]}};
const context={state,$:id=>elements[id],document:{createElement:element,createElementNS:element},explanations:{},nodeStatus:()=>'',showStep(){}};
vm.createContext(context);vm.runInContext(code,context);context.renderFlow();
let scene=elements.flow.children[0],cards=scene.children.slice(1);
assert.equal(scene.children[0].children.length,7,'Every actual dependency has an edge');
// Order is start, planning, C, A, B, verification, output; layout is topological.
assert.equal(cards[3].style.top,cards[4].style.top);
assert.notEqual(cards[3].style.left,cards[4].style.left);
assert.ok(parseFloat(cards[2].style.top)>parseFloat(cards[3].style.top));
state.horizontal=true;context.renderFlow();cards=elements.flow.children[0].children.slice(1);
assert.equal(cards[3].style.left,cards[4].style.left);
assert.notEqual(cards[3].style.top,cards[4].style.top);
assert.ok(parseFloat(cards[2].style.left)>parseFloat(cards[3].style.left));
state.plan=null;elements.mode.value='answer';state.events=[{stage:'retrieval',status:'started'}];context.renderFlow();
assert.equal(elements.flow.children[0].children[0].children.length,4);
console.log('Workflow canvas: branch, join, ordering, orientation and answer path passed.');
