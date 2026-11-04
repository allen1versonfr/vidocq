"""GPL-3.0-only bridge to the pinned Osintgram public-profile service."""
import json,os,re,sys,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from companion_scope import OG_COMMANDS

def main():
    from scripts.collector_http import serve
    credentials=json.loads(sys.stdin.readline());token=credentials.get('hiker_key','')
    if not isinstance(token,str) or not 10<=len(token)<=1024:raise ValueError('Missing HikerAPI key.')
    os.environ.pop('HIKERAPI_TOKEN',None)
    from src.osint_service import OsintgramService
    from hikerapi import Client
    cancelled=set();cached={}
    def handle(path,p):
        if path=='/api/cancel':cancelled.add(p.get('run_id'));return {'cancelled':True}
        if path!='/api/run':raise ValueError('Unsupported route.')
        target=p.get('target');calls=p.get('calls');budget=p.get('max_items',5);job=p.get('run_id','')
        if not isinstance(target,str) or not re.fullmatch(r'[A-Za-z0-9_.]{1,30}',target):raise ValueError('Invalid supplied Instagram handle.')
        if not isinstance(calls,list) or not 1<=len(calls)<=4 or any(not isinstance(c,dict) or c.get('name') not in OG_COMMANDS for c in calls):raise ValueError('Unsupported public-profile command.')
        if type(budget) is not int or not 1<=budget<=5:raise ValueError('Use a 1–5 request budget.')
        if job in cancelled:raise ValueError('Run cancelled.')
        # Initialize without resolving a target so the budget applies to the first request too.
        client=Client(token=token)
        try:
            service=OsintgramService(None,client);service.api.max_calls=budget;service.api.cache_store=cached;service.api.cache_ttl_seconds=3600
            class Cancellation:
                def is_set(self):return job in cancelled
            service.api.cancelled=Cancellation()
            service.target=target;service.user=service._fetch_user(target);service.target_id=service.user.get('pk');service.is_private=bool(service.user.get('is_private'))
            results=[]
            for call in calls:
                name=call['name']
                if name!='get_user_info' and service.user.get('is_private') is not False:results.append({'name':name,'is_error':True,'result':{'error':'Private or unknown-privacy content is outside the permitted scope.'}});continue
                if job in cancelled:break
                try:
                    result=getattr(service,name)(**({'limit_posts':5} if name in ('get_captions','get_hashtags') else {}))
                    if name=='get_user_info':result['is_private']=service.user.get('is_private')
                    results.append({'name':name,'result':result})
                except Exception:results.append({'name':name,'is_error':True,'result':{'error':'Source unavailable, budget exceeded or access restricted.'}})
            return {'target':target,'backend':'Osintgram / HikerAPI','api_calls_total':service.api_call_count,'tool_calls':results}
        finally:client._client.close()
    serve('osintgram',handle)

if __name__=='__main__':main()
