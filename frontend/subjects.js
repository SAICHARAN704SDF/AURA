// PRESENTATION SECTION: SUBJECT WORKFLOWS
// Subject diagrams: explain actual subsystem operations and derive statuses only from selected-operation telemetry.
/* Read-only diagrams driven by real telemetry; opening a diagram makes no requests. */
const SubjectWorkflows = (() => {
 const node=(stage,title,description,annotation)=>({stage,title,description,annotation});
 const sections=[
  {id:'documents',title:'Read and store a paper',when:'Runs when you upload a new document. An already indexed file may skip later steps.',nodes:[
   node('parsing','Read pages and text','The document loader extracts text and page references. Scanned image pages use bounded local English OCR when language data is installed.'),
   node('ocr','Read scanned pages','Local English OCR reads image-only pages, with a 20-page limit and a per-page timeout. It consumes no LLM tokens. Always review recognized text.'),
   node('chunking','Divide the text','The chunker creates overlapping pieces while keeping document and page references.'),
   node('embeddings','Represent their meaning','The embedding service turns chunks into numeric vectors, reusing cached vectors where possible.'),
   node('vector_storage','Save searchable pieces','Qdrant stores vectors and chunk references for later search.') ]},
  {id:'chunking',title:'Chunking · make manageable pieces',when:'Recursive chunking is the default. Semantic merging is optional, available through the upload API.',nodes:[
   node('chunking','Create overlapping chunks','Default chunks contain up to 1,200 characters with 150 characters of overlap. This is text processing, not an LLM call.'),
   node('chunk_inventory','Count pieces and pages','The inventory records chunk count, page count and requested strategy.'),
   node('semantic_chunking','Optional: merge similar neighbours','Only the semantic strategy embeds smaller blocks and merges adjacent blocks on the same page when similarity exceeds 0.8 and the combined size is within 1,800 characters. This step is skipped for recursive chunking.') ]},
  {id:'embeddings',title:'Embeddings · turn meaning into numbers',when:'Used for uploaded chunks, search questions and sentence comparison. A cache hit can skip the cloud request.',nodes:[
   node('embedding_cache','Look in the cache','SQLite checks whether these texts already have embeddings. Inspect hit and miss counts here.'),
   node('embedding_request','Encode missing texts','Only cache misses go to Cloudflare bge-m3, in batches of up to 16 texts. Each vector has 1,024 dimensions.'),
   node('embedding_validation','Check the vectors','AURA checks dimensions and rejects non-finite values before returning vectors to the caller.') ]},
  {id:'retrieval',title:'RAG retrieval · find the evidence',when:'Runs when a question or research tool searches selected documents. Reranking can fall back to the fused search order.',nodes:[
   node('embeddings','Encode the question','Convert the question into a vector, using the same model as the stored chunks.'),
   node('dense_search','Search by meaning','Qdrant finds vectors close to the question, filtered to the chosen document.'),
   node('lexical_search','Search by words','BM25 finds chunks that contain useful matching terms.'),
   node('bm25_fusion','Combine the rankings','Reciprocal-rank fusion combines meaning and word matches; duplicate content is removed.'),
   node('reranking','Reorder the best matches','Cloudflare reranks up to ten candidates. A failed reranker does not necessarily fail the entire search.') ]},
  {id:'nlp',title:'NLP · understand words and grammar',when:'Runs in Explore words or when an agent calls nlp_analyze. It does not automatically run for every report. Annotation cards are outputs of one spaCy pass, not separately timed stages.',nodes:[
   node('spacy_pipeline','Process the text with spaCy','A local English pipeline processes text. With no trained model, only tokenization and sentence splitting are available.'),
   node('text_preprocessing','Prepare a search vocabulary','Keep alphabetic content words, remove English stop words, normalize Unicode and case, and use lemmas when available. Original text offsets are preserved.'),
   node('vocabulary_summary','Count content words','Count retained terms and distinct terms. The analysis result includes the twenty most frequent.'),
   node('nlp_annotations','Words and sentences','Break text into tokens and sentence boundaries.','tokens'),
   node('nlp_annotations','Grammar and base words','Read part-of-speech tags, lemmas and dependency relationships from the trained pipeline.','dependencies'),
   node('nlp_annotations','Names and places','Read named entities such as people, organizations and locations. No detected entities can be a valid result.','entities') ]},
  {id:'similarity',title:'Semantic similarity · compare two texts',when:'Runs in Compare two sentences. A similarity score is not proof that two statements mean exactly the same thing.',nodes:[
   node('embeddings','Encode both texts','Generate or reuse two vectors from the embedding service.'),
   node('cosine_similarity','Compare the vectors','Cosine similarity measures the angle between the two vectors; no text-generation model is needed.') ]},
  {id:'generation',title:'LLM · create and check an answer',when:'Quick answers assemble retrieved context; report agents use their own bounded evidence context. Requests may repeat for planning and synthesis.',nodes:[
   node('context_assembly','Prepare answer context','LangChain-core Document objects carry the retrieved text and metadata for quick-answer generation. This stage is not used by the separate report-context builder.'),
   node('model_selected','Select the configured model','Inspect the actual provider, model and output-token limit. The app does not automatically switch to a larger model.'),
   node('llm','Generate structured text','The gateway calls the model and validates the returned data format.'),
   node('token_usage','Record model usage','Provider-reported token usage is recorded. This is not a credit balance or a price estimate.'),
   node('claim_review','Review each claim','A separate small-model call checks each sentence against the evidence. Missing or unsupported judgments block a fully verified answer; this review is fallible.'),
   node('citation_validation','Check quick-answer quotes','Quick-answer quotations must appear exactly in the referenced chunks. Agent reports instead run the verification step in the main graph.') ]},
  {id:'orchestration',title:'LangGraph · coordinate the agents',when:'Used for Detailed report. The main diagram above shows the actual task dependencies; this diagram shows the scheduler lifecycle. Task waves repeat until dependencies are complete.',nodes:[
   node('planning','Validate the task plan','Create or load the plan, then check permitted tools, dependency IDs and cycles.'),
   node('plan_template_selected','Choose a planning template','The scheduler can select a bounded report plan for a small model.'),
   node('task_wave','Run ready tasks ↺','Run tasks whose dependencies are complete, within call, tool, time and concurrency budgets. Each task has a limited retry policy.'),
   node('verification','Check the report evidence','Check source identity and literal quotes, plus explicitly calculated numeric relations. These checks do not establish every claim’s semantic correctness.') ]},
  {id:'memory',title:'Memory · save workflow progress',when:'SQLite persists application-level workflow state and events. This is not a native LangGraph checkpointer, and does not imply that AURA remembers every conversation.',nodes:[node('workflow_checkpoint','Save a workflow checkpoint','Persist task states, usage counters and workflow events in SQLite transactions. Completed tasks can be recovered from this stored state.')]},
  {id:'requests',title:'Server and cloud requests',when:'Request activity can repeat throughout a run. Retry waiting is optional. Cloudflare AI requests are distinct from Cloudflare Tunnel; AURA does not currently manage or verify a tunnel.',nodes:[
   node('server_request','Receive an API request','The FastAPI server handles an upload, question or workflow request. Workflow execution continues in a background task.'),
   node('provider_request','Contact a cloud provider','Inspect the actual host, HTTP status and attempt number. A failed attempt may be followed by a successful retry.'),
   node('provider_retry_wait','Optional: wait before retrying','Respect a bounded provider wait, for example after HTTP 429. No new model call occurs while waiting.') ]}
 ];
 function matching(n,events){
  const bySpan=new Map();
  for(const event of events)if(event.span_id&&(!bySpan.has(event.span_id)||event.parent_id))bySpan.set(event.span_id,event);
  return events.filter(e=>{
   if(e.stage!==n.stage)return false;
   if(!n.ingestionOnly)return true;
   let parent=e.parent_id||bySpan.get(e.span_id)?.parent_id;
   const visited=new Set();
   while(parent&&!visited.has(parent)){
    visited.add(parent);
    const ancestor=bySpan.get(parent);
    if(!ancestor)break;
    if(ancestor.stage==='ingestion')return true;
    parent=ancestor.parent_id;
   }
   return false;
  });
 }
 for(const section of sections)for(const step of section.nodes){
  step.section=section.id;
  if(section.id==='documents'&&step.stage==='embeddings')step.ingestionOnly=true;
 }
 function absent(n,events){
  const saved=events.find(e=>e.stage==='document_preparation');
  const upload=events.some(e=>e.stage==='ingestion');
  if(['documents','chunking'].includes(n.section)&&saved&&!upload){
   if(n.stage==='ocr')return {label:saved.ocr_pages?'OCR text reused':'No scanned pages processed',reason:saved.ocr_pages?`${saved.ocr_pages} previously OCR-processed pages are in the saved index.`:'This report reused indexed text. OCR is only needed for image-only pages. Earlier extraction details may be absent for older uploads.'};
   return {label:'Saved index reused',reason:`Search used ${saved.chunks} saved chunks from ${saved.documents} documents. Parsing, chunking and storage run during upload.`};
  }
  if(n.stage==='ocr'&&events.some(e=>e.stage==='ocr_decision'&&e.applied_pages===0))return {label:'Skipped · text already readable',reason:'The loader extracted selectable text. No scanned-page OCR was required.'};
  if(n.stage==='embedding_request'&&events.some(e=>e.stage==='embedding_cache'&&e.misses===0))return {label:'Skipped · cache hit',reason:'The saved embeddings were reused.'};
  const operation=events.some(e=>['retrieval','planning','semantic_similarity','nlp_linguistics'].includes(e.stage));
  if(n.section==='nlp'&&operation&&!events.some(e=>e.stage==='nlp_linguistics'))return {label:'Use Explore words',reason:'Choose Explore words and submit text to run tokenization, grammar and entity extraction.'};
  if(n.section==='similarity'&&operation&&!events.some(e=>e.stage==='semantic_similarity'))return {label:'Use Compare two sentences',reason:'Choose Compare two sentences and submit both texts to run this function.'};
  if(n.stage==='semantic_chunking'&&events.some(e=>e.stage==='chunk_inventory'&&e.strategy==='recursive'))return {label:'Skipped · recursive selected',reason:'Select semantic chunking through the upload API before uploading a new document to run semantic merging.'};
  return {label:'Not observed',reason:'No recorded event for this step in this operation. It may be waiting, unused, or absent from an older trace.'};
 }
 function status(n,events){
  const rows=matching(n,events),last=rows.at(-1);if(!last)return {kind:'idle',...absent(n,events),rows};
  if(n.annotation&&!(last.annotations||[]).includes(n.annotation))return {kind:'idle',label:'Unavailable',rows};
  const spans=new Map();for(const e of rows)if(e.span_id)spans.set(e.span_id,e.status);
  if([...spans.values()].includes('started'))return {kind:'active',label:'Running',rows};
  const kind=['failed','cancelled'].includes(last.status)?'failed':last.status==='started'?'active':'done';
  return {kind,label:{failed:'Needs attention',active:'Running',done:last.status==='info'?'Observed':'Completed'}[kind],rows};
 }
 let views=[];
 function mount(root){
  if(!root)return;
  const map=document.getElementById('stationMap');
  const names={documents:'Document intake',chunking:'Chunking',embeddings:'Embeddings',retrieval:'Evidence search',nlp:'Language lab',similarity:'Similarity',generation:'Writing & review',orchestration:'Agent control',memory:'Memory',requests:'Connections'};
  for(const section of sections){
   const details=document.createElement('details');details.className='subject-section';
   const summary=document.createElement('summary');summary.textContent=section.title;details.append(summary);
   const note=document.createElement('p');note.className='muted';note.textContent=section.when;details.append(note);
   const layout=document.createElement('div');layout.className='subject-layout';
   const flow=document.createElement('div');flow.className='subject-flow';flow.setAttribute('aria-label',section.title+' workflow');
   const info=document.createElement('section');info.className='subject-info';info.textContent='Select a step to see its explanation and recorded activity.';
   const view={section,details,info,cards:[],selected:null,events:[]};
   if(map){
    const station=document.createElement('button');
    const name=document.createElement('strong');
    const count=document.createElement('small');
    station.type='button';
    station.className='studio-station';
    name.textContent=names[section.id];
    const island=document.createElement('span');
    island.className='desk-island';
    island.setAttribute('aria-hidden','true');
    for(const part of ['platform','table','screen','chair','plant']){
     const piece=document.createElement('i');
     piece.className='office-'+part;
     island.append(piece);
    }
    station.append(island,name,count);
    view.station=station;
    view.count=count;
    const select=()=>{
     for(const other of views){
      const chosen=other===view;
      other.details.hidden=!chosen;
      other.details.open=chosen;
      other.station.setAttribute('aria-pressed',String(chosen));
     }
     view.selected ||= section.nodes[0];
     refresh(view);
    };
    station.addEventListener('click',select);
    map.append(station);
    details.hidden=true;
    summary.hidden=true;
   }
   for(const n of section.nodes){
    const button=document.createElement('button');button.type='button';button.className='subject-card';button.setAttribute('aria-pressed','false');
    const title=document.createElement('strong');title.textContent=n.title;const badge=document.createElement('small');badge.textContent='Not observed';button.append(title,badge);
    button.addEventListener('click',()=>{view.selected=n;refresh(view);});flow.append(button);view.cards.push({n,button,badge});
   }
   layout.append(flow,info);details.append(layout);root.append(details);views.push(view);
   if(view.station){refresh(view);if(section.id==="orchestration")view.station.click();else view.station.setAttribute("aria-pressed","false");}
  }
 }
 function refresh(view){
  if(view.count){
   const states=view.section.nodes.map(n=>status(n,view.events).kind);
   const label=states.includes('active')?'Running':states.includes('failed')?'Needs attention':states.includes('done')?'Observed':'Idle';
   view.count.textContent=label+' · '+states.filter(s=>s==='done').length+'/'+states.length+' steps';
   view.station.dataset.state=label;
  }
  for(const {n,button,badge} of view.cards){const current=status(n,view.events);button.className='subject-card '+current.kind;badge.textContent=current.label;button.setAttribute('aria-pressed',String(view.selected===n));}
  if(!view.selected)return;
  const n=view.selected,current=status(n,view.events);view.info.replaceChildren();
  const h=document.createElement('h3');h.textContent=n.title;const p=document.createElement('p');p.textContent=n.description;const state=document.createElement('p');state.textContent=current.rows.length?`${current.label} · ${current.rows.length} recorded events. Repeated calls are shown in the timeline.`:current.reason||'No recorded event for this step.';view.info.append(h,p,state);
  const last=current.rows.at(-1);if(last){const pre=document.createElement('pre');pre.textContent=JSON.stringify(last,null,2);view.info.append(pre);}
 }
 function update(events,replaying=false){for(const view of views){view.events=events;refresh(view);}const scope=document.getElementById('subjectScope');if(scope)scope.textContent=replaying?'Recorded replay · older saved runs may not contain detailed substeps.':'Selected operation only · diagrams explain the implementation; status comes only from recorded events. New operations clear previous activity.';}
 return {mount,update,sections,status};
})();
