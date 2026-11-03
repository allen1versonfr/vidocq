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
(async()=>{await check('Only the selected public result.',true);await check('',false);await check('x'.repeat(12001),false);console.log('Browser capture selection, link scope, download and empty/oversize rejection passed.')})().catch(e=>{console.error(e);process.exitCode=1});
