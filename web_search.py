"""Free anonymous Mwmbl search with optional Brave web-index retrieval. Never fetches original result URLs."""
import copy,html,json,os,re,threading,time
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode,urlparse
from urllib.request import Request,HTTPRedirectHandler,build_opener
from version import VERSION

class SearchNotConfigured(ValueError):pass
class SearchLimit(ValueError):pass
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Search API redirected; the key was not forwarded.')

class WebSearch:
    def __init__(self):
        self.key=os.environ.get('VIDOCQ_BRAVE_API_KEY','');self.enabled=bool(self.key);self.provider='brave' if self.key else 'mwmbl'
        self.lock=threading.RLock();self.requests=0;self.free_lock=threading.Lock();self.next_free=0;self.cooldown_until=0;self.cache={}
    def label(self):
        return 'Brave web index' if self.provider=='brave' else 'Mwmbl free web index'
    def status(self):
        with self.lock:
            ready=self.provider=='mwmbl' or bool(self.key)
            message=('Free Mwmbl search enabled. No account, key or payment is used; its smaller index may miss accounts.' if self.enabled else 'Free Mwmbl search is available. Enable it without an account, key or payment.') if self.provider=='mwmbl' else ('Optional Brave search enabled; your provider plan applies.' if self.enabled and self.key else 'Brave is optional. Add its key or choose free Mwmbl search.')
            return {'configured':ready and self.enabled,'key_configured':bool(self.key),'enabled':self.enabled,'provider':self.provider,'provider_name':'Mwmbl anonymous API' if self.provider=='mwmbl' else 'Brave Search API','requires_key':self.provider=='brave','session_requests':self.requests,'session_limit':100,'message':message,'free_cooldown_seconds':max(0,round(self.cooldown_until-time.monotonic()))}
    def configure(self,data):
        if not isinstance(data,dict) or type(data.get('enabled')) is not bool:raise ValueError('Choose whether web search is enabled.')
        key=data.get('key')
        with self.lock:
            provider=data.get('provider','brave' if key else self.provider)
            if provider not in ('mwmbl','brave'):raise ValueError('Choose free Mwmbl or optional Brave search.')
            if key is not None and (not isinstance(key,str) or len(key)>500 or (key and not re.fullmatch(r'[A-Za-z0-9._-]+',key))):raise ValueError('Invalid API key format.')
            new_key=self.key if key is None else key
            if data['enabled'] and provider=='brave' and not new_key:raise ValueError('Brave needs its API key. Choose free Mwmbl to search without one.')
            self.key=new_key;self.provider=provider;self.enabled=data['enabled']
        return self.status()
    def _free_search(self,query,site):
        source='https://api.mwmbl.org/api/v2/search/?'+urlencode({'q':query})
        with self.free_lock:
            if time.monotonic()<self.cooldown_until:raise SearchLimit('Free search is cooling down after a provider rate/quota limit. No request sent; this is not a no-match result.')
            cached=self.cache.get(query)
            if cached and time.monotonic()-cached[0]<900:return source,copy.deepcopy(cached[1])
            if self.requests>=100:raise SearchLimit('Session search limit reached (100 requests).')
            delay=self.next_free-time.monotonic()
            if delay>0:time.sleep(delay)
            self.next_free=time.monotonic()+1.1
            self.requests+=1
            req=Request(source,headers={'User-Agent':'Vidocq/'+VERSION+' (+https://github.com/allen1versonfr/vidocq)','Accept':'application/json'})
            try:
                with build_opener(NoRedirect()).open(req,timeout=20) as response:raw=response.read(2_000_001)
                if len(raw)>2_000_000:raise ValueError('Free search response exceeded its size limit.')
                try:data=json.loads(raw)
                except (ValueError,UnicodeError):raise ValueError('Free search returned unreadable JSON, not a no-match result.') from None
                if not isinstance(data,dict) or data.get('query')!=query or not isinstance(data.get('results'),list) or type(data.get('number_of_results')) is not int or data['number_of_results']!=len(data['results']):raise ValueError('Free search returned an unexpected response, not a no-match result.')
                rows=[];seen=set()
                for item in data['results']:
                    if not isinstance(item,dict) or not all(isinstance(item.get(k),str) for k in ('url','title','content')):raise ValueError('Free search returned malformed result data.')
                    url=item['url'];p=urlparse(url)
                    if len(url)>2000 or p.scheme not in ('https','http') or not p.hostname or p.username or p.password:continue
                    if site and not (p.hostname==site or p.hostname.endswith('.'+site)):continue
                    if url in seen:continue
                    seen.add(url)
                    text=lambda x:html.unescape(re.sub('<[^>]+>','',x))
                    rows.append({'title':text(item['title'])[:500],'detail':text(item['content'])[:4000] or 'No index snippet supplied.','reference':url,'index_engine':str(item.get('engine','mwmbl'))[:80]})
                    if len(rows)==10:break
                self.cache[query]=(time.monotonic(),copy.deepcopy(rows))
                return source,rows
            except HTTPError as error:
                if error.code==429:
                    header=(error.headers or {}).get('Retry-After','60')
                    cooldown=max(60,int(header)) if str(header).isdigit() else 60
                    self.cooldown_until=time.monotonic()+cooldown
                    raise SearchLimit('Free search provider rate/monthly quota limit reached. No payment was attempted; wait for its quota to reset or review prepared search links.') from None
                raise ValueError('Free search unavailable (HTTP '+str(error.code)+'). This is not a no-match result.') from None
            except (URLError,TimeoutError,OSError):raise ValueError('Free search could not be reached. This is not a no-match result.') from None
    def search_terms(self,terms):
        if not isinstance(terms,list) or not 1<=len(terms)<=4 or any(not isinstance(t,str) or not t.strip() or len(t)>120 or any(ord(c)<32 for c in t) for t in terms):raise ValueError('Invalid context search terms.')
        return self.search('',terms=terms)
    def search(self,value,site=None,terms=None):
        if site is not None and site not in ('instagram.com','tiktok.com','vsco.co','steamcommunity.com'):raise ValueError('Unsupported social index scope.')
        with self.lock:
            if not self.enabled:raise SearchNotConfigured('Web search was not run: enable free Mwmbl search in Search connection. Brave is optional; no payment is needed for Mwmbl.')
            provider=self.provider
            if provider=='brave' and not self.key:raise SearchNotConfigured('Brave is not configured. Choose free Mwmbl or add your optional Brave key.')
            if self.requests>=100:raise SearchLimit('Session search limit reached (100 API calls). Check your provider usage before reconnecting in a new app session.')
            key=self.key
            if provider=='brave':self.requests+=1
        query='"'+str(value).replace('"','').replace('\\','')+'"'
        if terms is not None:query=' '.join('"'+str(t).replace('"','').replace('\\','')+'"' for t in terms)
        if site:query='site:'+site+' '+query
        if provider=='mwmbl':return self._free_search(query,site)
        source='https://api.search.brave.com/res/v1/web/search?'+urlencode({'q':query,'count':10,'safesearch':'moderate','text_decorations':'false'})
        req=Request(source,headers={'User-Agent':'Vidocq/'+VERSION,'Accept':'application/json','X-Subscription-Token':key})
        try:
            with build_opener(NoRedirect()).open(req,timeout=15) as response:raw=response.read(2_000_001)
            if len(raw)>2_000_000:raise ValueError('Search response exceeded its size limit.')
            try:data=json.loads(raw)
            except (ValueError,UnicodeError):raise ValueError('Search provider returned an unreadable response, not a no-match result.') from None
            if not isinstance(data,dict) or 'error' in data or not isinstance(data.get('query'),dict):raise ValueError('Search provider returned an unexpected response, not a no-match result.')
            web=data.get('web')
            if web is None:results=[]
            elif not isinstance(web,dict) or not isinstance(web.get('results'),list):raise ValueError('Search provider returned an unexpected web-result format.')
            else:results=web['results']
            rows=[]
            for item in results[:10]:
                if not isinstance(item,dict):continue
                url=str(item.get('url',''));p=urlparse(url)
                if p.scheme not in ('https','http') or not p.hostname or p.username or p.password:continue
                if site and not (p.hostname==site or p.hostname.endswith('.'+site)):continue
                text=lambda x:html.unescape(re.sub('<[^>]+>','',str(x)))
                rows.append({'title':text(item.get('title','Indexed page'))[:500],'detail':text(item.get('description','No index snippet supplied.'))[:4000], 'reference':url[:2000]})
            return source,rows
        except HTTPError as error:
            if error.code in (401,403):raise ValueError('Search API key or plan was rejected. Check your Brave Search subscription and key; this is not a no-match result.') from None
            if error.code==429:raise ValueError('Search API quota/rate limit reached. Check provider usage; the query did not complete.') from None
            raise ValueError('Search provider unavailable (HTTP '+str(error.code)+'). Query did not complete.') from None
        except (URLError,TimeoutError,OSError):raise ValueError('Could not reach the search API. Check network/proxy settings; the query did not complete.') from None

CLIENT=WebSearch()

def outcome(coverage,records):
    if any(x.get('origin')=='retrieved' for x in records):return 'records-found','Index records returned. Identity relevance still needs review.'
    remote=[x for x in coverage if x.get('provider')!='Offline phone metadata']
    failed=any(x.get('status')=='error' for x in remote)
    searched=any(x.get('status') in ('ok','empty') for x in remote)
    if not searched and failed:return 'sources-unavailable','Searches failed or were unavailable. Zero returned records does not mean no information exists.'
    if not searched:return 'not-searched','No online result search completed. Connect web search or review the prepared links; this is not a no-match conclusion.'
    if failed:return 'incomplete','Some indexes returned no matches and others failed. The report is incomplete.'
    return 'no-matches-in-searched-sources','No matches were returned by the indexes that completed. This does not establish absence elsewhere.'
