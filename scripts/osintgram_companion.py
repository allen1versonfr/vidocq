"""GPL-3.0-only bridge to the pinned Osintgram public-profile service."""
import json,os,re,sys,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from companion_scope import OG_COMMANDS

def main():
    from scripts.collector_http import serve
    credentials=json.loads(sys.stdin.readline());token=credentials.get('hiker_key','')
    backend=credentials.get('backend','hikerapi')
    if backend not in ('hikerapi','instagrapi'):raise ValueError('Unsupported Instagram backend.')
    if backend=='hikerapi' and (not isinstance(token,str) or not 10<=len(token)<=1024):raise ValueError('Missing HikerAPI key.')
    os.environ.pop('HIKERAPI_TOKEN',None)
    from src.osint_service import OsintgramService
    from hikerapi import Client
    from scripts.instagram_session import Login,locked_client,ReconnectRequired
    if backend=='instagrapi':
        from instagrapi import Client as InstagramClient
        auth=Login(InstagramClient)
    else:auth=Login()
    if backend=='instagrapi' and credentials.get('session'):auth.restore(credentials)
    cancelled=set();cached={}
    def handle(path,p):
        if path=='/api/auth/status':return auth.status()
        if path=='/api/auth/start':
            if backend!='instagrapi':raise ValueError('Choose the guided login backend first.')
            return auth.start(p)
        if path=='/api/auth/code':return auth.code(p)
        if path=='/api/auth/cancel':return auth.cancel()
        if path=='/api/auth/session':return auth.export()
        if path=='/api/cancel':cancelled.add(p.get('run_id'));return {'cancelled':True}
        if path!='/api/run':raise ValueError('Unsupported route.')
        target=p.get('target');calls=p.get('calls');budget=p.get('max_items',5);job=p.get('run_id','')
        if not isinstance(target,str) or not re.fullmatch(r'[A-Za-z0-9_.]{1,30}',target):raise ValueError('Invalid supplied Instagram handle.')
        if not isinstance(calls,list) or not 1<=len(calls)<=4 or any(not isinstance(c,dict) or c.get('name') not in OG_COMMANDS for c in calls):raise ValueError('Unsupported public-profile command.')
        if type(budget) is not int or not 1<=budget<=5:raise ValueError('Use a 1–5 request budget.')
        if job in cancelled:raise ValueError('Run cancelled.')
        # Initialize without resolving a target so the budget applies to the first request too.
        if backend=='instagrapi':
            if auth.phase!='connected':raise ReconnectRequired('Connect your own operator session in Vidocq first.')
            from src.instagrapi_backend import InstagrapiClient
            client=InstagrapiClient.__new__(InstagrapiClient);client._cl=locked_client(auth.session,on_reconnect=auth.reconnect);client._cl.username=auth.username
        else:client=Client(token=token)
        try:
            service=OsintgramService(None,client);service.api.max_calls=budget;service.api.cache_store=cached;service.api.cache_ttl_seconds=3600
            class Cancellation:
                def is_set(self):return job in cancelled
            service.api.cancelled=Cancellation()
            service.target=target;service.user=service._fetch_user(target);service.target_id=service.user.get('pk');service.is_private=bool(service.user.get('is_private'))
            results=[]
            for call in calls:
                name=call['name']
                if backend=='instagrapi' and name=='get_account_about':results.append({'name':name,'is_error':True,'vidocq_reason':'About this account is unsupported by instagrapi; it needs the optional HikerAPI backend.','result':{'error':'Unsupported backend command.'}});continue
                if name!='get_user_info' and service.user.get('is_private') is not False:results.append({'name':name,'is_error':True,'result':{'error':'Private or unknown-privacy content is outside the permitted scope.'}});continue
                if job in cancelled:break
                try:
                    result=getattr(service,name)(**({'limit_posts':5} if name in ('get_captions','get_hashtags') else {}))
                    if name=='get_user_info':result['is_private']=service.user.get('is_private')
                    results.append({'name':name,'result':result})
                except Exception:results.append({'name':name,'is_error':True,'result':{'error':'Source unavailable, budget exceeded or access restricted.'}})
            return {'target':target,'backend':'Osintgram / '+backend,'api_calls_total':service.api_call_count,'tool_calls':results,'needs_reconnect':auth.phase=='reconnect-required'}
        except Exception as error:
            if backend=='instagrapi' and (auth.phase=='reconnect-required' or isinstance(error,ReconnectRequired) or type(error).__name__ in ('LoginRequired','ChallengeRequired','ChallengeUnknownStep','ChallengeRedirection')):auth.reconnect();raise ReconnectRequired('Session expired or challenged; reconnect explicitly in Vidocq.') from None
            raise
        finally:
            if backend=='hikerapi':client._client.close()
            else:
                client._cl.private.close();client._cl.public.close()
    serve('osintgram',handle,lambda:{'backend':backend,'needs_reconnect':auth.phase=='reconnect-required'})

if __name__=='__main__':main()
