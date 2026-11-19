const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const context={};vm.createContext(context);
vm.runInContext(fs.readFileSync('frontend/subjects.js','utf8')+'\nthis.subjects=SubjectWorkflows;',context);
const {sections,status}=context.subjects;
assert.equal(sections.length,10);
assert.equal(new Set(sections.map(s=>s.id)).size,10);
const grammar=sections.find(s=>s.id==='nlp').nodes.find(n=>n.annotation==='dependencies');
assert.equal(status(grammar,[]).label,'Not observed');
assert.equal(status(grammar,[{stage:'nlp_annotations',status:'completed',annotations:['tokens','sentences']}]).label,'Unavailable');
assert.equal(status(grammar,[{stage:'nlp_annotations',status:'completed',annotations:['dependencies']}]).label,'Completed');
const request={stage:'embedding_request'};
assert.equal(status(request,[{stage:'embedding_cache',status:'info',hits:3,misses:0}]).label,'Skipped · cache hit');
assert.equal(status(request,[{stage:'embedding_request',span_id:'a',status:'started'}]).label,'Running');
assert.equal(status(request,[{stage:'embedding_request',span_id:'a',status:'started'},{stage:'embedding_request',span_id:'a',status:'failed'}]).label,'Needs attention');
assert.equal(status(request,[{stage:'embedding_request',span_id:'a',status:'failed'},{stage:'embedding_request',span_id:'b',status:'completed'}]).label,'Completed');
console.log('Subject diagrams: optional steps, cache hits, NLP fallback and observed states passed.');

const saved=[{stage:'document_preparation',source:'saved_index',documents:1,pages:8,chunks:12,ocr_pages:0}];
const documents=sections.find(s=>s.id==='documents');
assert.equal(status(documents.nodes[0],saved).label,'Saved index reused');
assert.equal(status(documents.nodes[1],saved).label,'No scanned pages processed');
const queryEmbedding={stage:'embeddings',status:'completed',span_id:'embed',parent_id:'search'};
assert.equal(status(documents.nodes[3],[...saved,{stage:'retrieval',span_id:'search',status:'started'},queryEmbedding]).label,'Saved index reused');
assert.equal(status(documents.nodes[3],[{stage:'ingestion',span_id:'upload',status:'started'},{...queryEmbedding,parent_id:'upload'}]).label,'Completed');

assert.equal(status(documents.nodes[3],[{stage:'ingestion',span_id:'upload',status:'started'},{stage:'embeddings',span_id:'e',parent_id:'upload',status:'started'},{stage:'embeddings',span_id:'e',status:'completed'}]).label,'Completed');
