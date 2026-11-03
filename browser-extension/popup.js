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
