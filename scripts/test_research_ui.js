/* DOM fixtures only: no browser installation, account login or live requests. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require(path.resolve(process.argv[2]||'.test-data/dom-tests/node_modules/jsdom'));
const html=fs.readFileSync('ui/index.html','utf8'),dom=new JSDOM(html,{url:'http://127.0.0.1:12345/',runScripts:'outside-only'}),w=dom.window,context=dom.getInternalVMContext(),calls=[];
w.HTMLDialogElement.prototype.showModal=function(){this.open=true};w.HTMLDialogElement.prototype.close=function(){this.open=false};w.setTimeout=()=>0;w.clearTimeout=()=>{};
let authPhase='idle';const cid='a'.repeat(24),rid='b'.repeat(24),newRid='c'.repeat(24);
const auth=()=>({phase:authPhase,busy:authPhase==='two-factor-required',connected:authPhase==='connected',saved:authPhase==='connected',message:'Synthetic operator status',login_id:'fixture',username:'operatorfixture'});
w.fetch=async(url,options={})=>{
  const p=options.body?JSON.parse(options.body):undefined;calls.push({url,p});let data;
  if(url==='/api/automation')data={configured:false,choices:{},busy:false,services:{},credentials:{saved:false,locked:false,backend:'hikerapi'},needs_osintgram_credentials:false,llm:{enabled:false},messages:{}};
  else if(url==='/api/browser-pending')data=[];
  else if(url==='/api/search-connection')data={provider:p?.provider||'mwmbl',enabled:!!p?.enabled,requires_key:p?.provider&&p.provider!=='mwmbl',message:'Synthetic search',session_requests:0,session_limit:100};
  else if(url==='/api/instagram-login')data=auth();
  else if(url==='/api/instagram-login/start'){authPhase='two-factor-required';data=auth()}
  else if(url==='/api/instagram-login/code'){authPhase='connected';data=auth()}
  else if(url==='/api/cases/'+cid+'/review-plan')data={previous_run:rid,queries:[{terms:['Example','Person'],reason:'supplied tokens',previously_attempted:false}],next_steps:['Review public bio'],source_gaps:{status:'incomplete'}};
  else if(url==='/api/cases/'+cid+'/profile-capture')data={result:{},evidence:{id:'fixture'}};
  else if(url==='/api/cases/'+cid+'/aliases')data={aliases:p.aliases};
  else if(url==='/api/cases/'+cid+'/continue')data={id:newRid};
  else return new Promise(()=>{}); // unrelated startup reads stay offline/pending
  return {ok:true,json:async()=>data};
};
for(const match of html.matchAll(/<script src="\/([^"?]+)"/g))vm.runInContext(fs.readFileSync('ui/'+match[1],'utf8'),context,{filename:match[1]});
const el=id=>w.document.getElementById(id),event={preventDefault(){}};
async function flush(){for(let i=0;i<12;i++)await Promise.resolve()}
(async()=>{
  await flush();vm.runInContext("showConnectors=async()=>{};refreshReadiness=async()=>{};loadCaseEvidence=async()=>{};loadFindings=async()=>{};loadRuns=async()=>{};saveCase=async()=>{};pollCase=(id)=>globalThis.fixturePolled=id;currentCase='"+cid+"';",context);
  assert(el('instagram-connect'));assert(el('profile-evidence-form'));assert(el('assist-adaptive'));
  el('instagram-connect').onclick();el('instagram-operator').value='operatorfixture';el('instagram-password').value='synthetic-password';el('instagram-login-consent').checked=true;
  await el('instagram-login-form').onsubmit(event);assert.equal(el('instagram-password').value,'');assert.equal(el('instagram-code-form').hidden,false);
  el('instagram-code').value='123456';await el('instagram-code-form').onsubmit(event);assert.equal(el('instagram-code').value,'');assert.match(el('instagram-session-status').textContent,/Encrypted session saved/);
  assert.equal(calls.find(c=>c.url.endsWith('/start')).p.username,'operatorfixture');
  el('connection-provider').value='serper';el('connection-provider').onchange();assert.equal(el('connection-brave-settings').hidden,false);
  assert.equal(el('search-remember').checked,true);assert.match(el('connection-brave-settings').textContent,/restored after restarts and updates/);
  el('connection-key').value='synthetic-search-key';el('connection-enabled').checked=true;
  await el('connection-form').onsubmit(event);assert.equal(el('connection-key').value,'');assert(calls.some(c=>c.url==='/api/search-connection'&&c.p?.provider==='serper'&&c.p.remember));
  el('connection-key').value='must-not-cross-provider';el('connection-provider').value='mwmbl';el('connection-provider').onchange();assert.equal(el('connection-key').value,'');
  await el('connection-form').onsubmit(event);assert.equal(calls.filter(c=>c.url==='/api/search-connection'&&c.p?.provider==='mwmbl').at(-1).p.key,undefined);
  el('case-title').value='Synthetic case';const payload=vm.runInContext('casePayload()',context);assert.equal(payload.investigation.adaptive_queries,true);assert.equal(payload.investigation.ai_assessment,true);
  assert.equal(payload.investigation.platform_searches,4);assert.equal(el('search-result-limit').value,'10');
  assert.equal(payload.investigation.index_depth,20);assert.equal(payload.investigation.extra_snippets,false);assert.equal(payload.investigation.follow_indexed_links,false);
  el('alias-entry-handle').value='oldfixture';el('alias-entry-successor').value='https://instagram.com/newfixture';await el('alias-entry-save').onclick();assert.equal(el('alias-entry-handle').value,'');assert(calls.some(c=>c.url.endsWith('/aliases')&&c.p.aliases[0].successor==='https://instagram.com/newfixture'));
  await el('workflow-plan').onclick();assert.match(el('workflow-queries').textContent,/Example/);
  el('profile-reference').value='https://github.com/publicfixture';el('profile-biography').value='Reviewed public biography';el('profile-reviewed').checked=true;
  el('profile-evidence-form').onsubmit(event);await flush();assert(calls.some(c=>c.url.endsWith('/profile-capture')&&c.p.public_reviewed===true));
  await el('workflow-continue').onclick();assert(!calls.some(c=>c.url.endsWith('/continue')),'Continuation must require new run consent');
  el('workflow-continue-consent').checked=true;await el('workflow-continue').onclick();assert.equal(w.fixturePolled,newRid);assert(calls.some(c=>c.url.endsWith('/continue')&&c.p.previous_run===rid));
  dom.window.close();console.log('Research UI DOM fixtures passed: guided 2FA, input clearing, provider setup, profile evidence, bounded options and consented new-report continuation.');
})().catch(e=>{console.error(e);dom.window.close();process.exitCode=1});
