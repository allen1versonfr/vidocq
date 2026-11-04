/* User-triggered activeTab only: no background collection, cookies, or host permissions. */
document.getElementById('capture').onclick=async()=>{
  const status=document.getElementById('status');
  try {
    const api=globalThis.browser||globalThis.chrome;
    const [tab]=await api.tabs.query({active:true,currentWindow:true});
    const [result]=await api.scripting.executeScript({target:{tabId:tab.id},func:()=>{
      if(location.protocol!=='https:')throw Error('Capture requires a public HTTPS page.');
      const selection=window.getSelection(),excerpt=selection.toString().trim();
      if(!excerpt||excerpt.length>12000)throw Error('Select 1–12,000 characters of public text first.');
      const links=new Set();
      for(let i=0;i<selection.rangeCount;i++){
        const fragment=selection.getRangeAt(i).cloneContents();
        for(const anchor of fragment.querySelectorAll('a[href]')){
          try{const url=new URL(anchor.getAttribute('href'),location.href);if(url.protocol==='https:'&&!url.username&&!url.password)links.add(url.href)}catch{}
        }
      }
      return {schema:'vidocq-browser-v1',title:document.title.slice(0,500),reference:location.href,excerpt,links:[...links].slice(0,200),captured_at:new Date().toISOString()};
    }});
    if(!result?.result)throw Error('Select public text on an accessible HTTPS page first.');
    const blob=new Blob([JSON.stringify(result.result,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download='vidocq-browser-capture.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    status.textContent='Saved locally. In Vidocq, choose Browser JSON and review/import this file into your case.';
  }catch(error){status.textContent=error.message||'Capture failed. Browser-protected pages cannot be captured.'}
};

const sendButton=document.getElementById('send');
if(sendButton){
  document.getElementById('case-id').value=localStorage.getItem('vidocq-case-id')||'';
  sendButton.onclick=async()=>{const status=document.getElementById('status');try{
    const caseId=document.getElementById('case-id').value.trim();if(!/^[0-9a-f]{24}$/.test(caseId))throw Error('Enter the case ID shown in Vidocq first.');
    const api=globalThis.browser||globalThis.chrome,[tab]=await api.tabs.query({active:true,currentWindow:true});
    const [result]=await api.scripting.executeScript({target:{tabId:tab.id},func:()=>{
      if(location.protocol!=='https:')throw Error('Choose a public HTTPS page.');
      const s=window.getSelection(),excerpt=s.toString().trim();if(!excerpt||excerpt.length>6000)throw Error('Select 1–6,000 characters first.');
      const links=new Set();for(let i=0;i<s.rangeCount;i++)for(const a of s.getRangeAt(i).cloneContents().querySelectorAll('a[href]')){try{const u=new URL(a.getAttribute('href'),location.href);if(u.protocol==='https:'&&!u.username&&!u.password)links.add(u.href)}catch{}}
      return {schema:'vidocq-browser-v1',title:document.title.slice(0,500),reference:location.href,excerpt,links:[...links].slice(0,50),captured_at:new Date().toISOString()};
    }});
    if(!result?.result)throw Error('Capture failed; select public text on an accessible page.');
    const uri='vidocq-evidence://capture?data='+encodeURIComponent(JSON.stringify({case_id:caseId,data:result.result}));
    if(uri.length>26000)throw Error('Select a smaller excerpt, or use JSON export.');
    localStorage.setItem('vidocq-case-id',caseId);window.open(uri,'_blank');status.textContent='Approve opening Vidocq if prompted, then review/import the pending capture there.';
  }catch(e){status.textContent=e.message}};
}
