/* Run the extension action against selected-text fixtures without browser access. */
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
async function check(text,expected){
  const nodes={capture:{},status:{}},downloads=[];let captured;
  const context=vm.createContext({Blob,URL:class extends URL{static createObjectURL(blob){captured=blob;return 'blob:fixture'}static revokeObjectURL(){}},Set,Date,Error,setTimeout:fn=>fn(),
    location:{protocol:'https:',href:'https://example.org/search?q=example'},
    document:{title:'Reviewed search results',getElementById:id=>nodes[id],createElement:()=>({click(){downloads.push(this.download)}})},
    window:{getSelection:()=>({toString:()=>text,rangeCount:1,getRangeAt:()=>({cloneContents:()=>({querySelectorAll:()=>[{getAttribute:()=>'/bio'},{getAttribute:()=>'javascript:bad()'}]})})})},
    chrome:{tabs:{query:async()=>[{id:1}]},scripting:{executeScript:async opts=>[{result:opts.func()}]}}
  });
  vm.runInContext(fs.readFileSync('browser-extension/popup.js','utf8'),context);
  await nodes.capture.onclick();
  assert.equal(downloads.length,expected?1:0);
  if(expected){const data=JSON.parse(await captured.text());assert.equal(data.excerpt,text);assert.deepEqual(data.links,['https://example.org/bio']);assert.equal(data.schema,'vidocq-browser-v1');assert.match(nodes.status.textContent,/Saved locally/)}
  else assert.match(nodes.status.textContent,/Select/);
}
async function checkSend(text,caseId,expected){
  const nodes={capture:{},status:{},send:{},'case-id':{value:''}},opened=[],saved={};
  const context=vm.createContext({URL,Set,Date,Error,encodeURIComponent,localStorage:{getItem:()=>caseId,setItem:(k,v)=>saved[k]=v},
    location:{protocol:'https:',href:'https://example.org/bio'},document:{title:'Reviewed bio',getElementById:id=>nodes[id]},
    window:{open:uri=>opened.push(uri),getSelection:()=>({toString:()=>text,rangeCount:1,getRangeAt:()=>({cloneContents:()=>({querySelectorAll:()=>[{getAttribute:()=>'https://github.com/example'}]})})})},
    chrome:{tabs:{query:async()=>[{id:1}]},scripting:{executeScript:async opts=>[{result:opts.func()}]}}
  });
  vm.runInContext(fs.readFileSync('browser-extension/popup.js','utf8'),context);await nodes.send.onclick();
  assert.equal(opened.length,expected?1:0);
  if(expected){const uri=new URL(opened[0]),payload=JSON.parse(uri.searchParams.get('data'));assert.equal(uri.protocol,'vidocq-evidence:');assert.equal(payload.case_id,caseId);assert.equal(payload.data.excerpt,text);assert.deepEqual(payload.data.links,['https://github.com/example']);assert.equal(saved['vidocq-case-id'],caseId);assert.match(nodes.status.textContent,/review\/import/)}
}
(async()=>{await check('Only the selected public result.',true);await check('',false);await check('x'.repeat(12001),false);await checkSend('Reviewed public excerpt.','a'.repeat(24),true);await checkSend('Reviewed public excerpt.','bad',false);await checkSend('','a'.repeat(24),false);await checkSend('x'.repeat(6001),'a'.repeat(24),false);console.log('Browser export and native send: selected text, link scope, case IDs, empty/oversize rejection passed.')})().catch(e=>{console.error(e);process.exitCode=1});
