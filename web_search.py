"""Free anonymous Mwmbl search with optional Brave web-index retrieval. Never fetches original result URLs."""
import copy,html,json,os,re,threading,time
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode,urlparse
from urllib.request import Request,HTTPRedirectHandler,build_opener,ProxyHandler
from version import VERSION

class SearchNotConfigured(ValueError):pass
class SearchLimit(ValueError):pass
class IndexResult(tuple):
    """Backward-compatible (source, rows) with request-local adapter diagnostics."""
    def __new__(cls,source,rows,diagnostics):
        result=super().__new__(cls,(source,rows));result.diagnostics=diagnostics;return result
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Search API redirected; the key was not forwarded.')

class WebSearch:
    def __init__(self):
        self.key=os.environ.get('VIDOCQ_BRAVE_API_KEY','');self.enabled=bool(self.key);self.provider='brave' if self.key else 'mwmbl'
        self.lock=threading.RLock();self.requests=0;self.free_lock=threading.Lock();self.next_free=0;self.cooldown_until=0;self.cache={}
        self.other_keys={};self.session_limit=100
    def label(self):
        return {'brave':'Brave web index','mwmbl':'Mwmbl free web index','serper':'Serper Google results','serpapi':'SerpApi Google results'}[self.provider]
    def status(self):
        with self.lock:
            ready=self.provider=='mwmbl' or bool(self.other_keys.get(self.provider) if self.provider in ('serper','serpapi') else self.key)
            message=('Free Mwmbl search enabled. No account, key or payment is used; its smaller index may miss accounts.' if self.enabled else 'Free Mwmbl search is available. Enable it without an account, key or payment.') if self.provider=='mwmbl' else ('Optional Brave search enabled; your provider plan applies.' if self.enabled and self.key else 'Brave is optional. Add its key or choose free Mwmbl search.')
            if self.provider in ('serper','serpapi'):message=self.label()+(' enabled; your provider quota/charges apply.' if self.enabled and ready else ' needs your own API key. A free allowance is not unlimited access.')
            return {'configured':ready and self.enabled,'key_configured':ready if self.provider!='mwmbl' else bool(self.key),'enabled':self.enabled,'provider':self.provider,'provider_name':self.label(),'requires_key':self.provider!='mwmbl','session_requests':self.requests,'session_limit':self.session_limit,'message':message,'free_cooldown_seconds':max(0,round(self.cooldown_until-time.monotonic()))}
    def configure(self,data):
        if not isinstance(data,dict) or type(data.get('enabled')) is not bool:raise ValueError('Choose whether web search is enabled.')
        key=data.get('key')
        with self.lock:
            provider=data.get('provider','brave' if key else self.provider)
            if provider not in ('mwmbl','brave','serper','serpapi'):raise ValueError('Choose a supported search provider.')
            if key is not None and (not isinstance(key,str) or len(key)>500 or (key and not re.fullmatch(r'[A-Za-z0-9._-]+',key))):raise ValueError('Invalid API key format.')
            new_key=(self.other_keys.get(provider,'') if provider in ('serper','serpapi') else self.key) if key is None else key
            if data['enabled'] and provider!='mwmbl' and not new_key:raise ValueError('This provider needs its API key. Choose free Mwmbl to search without one.')
            limit=data.get('session_limit',self.session_limit)
            if type(limit) is not int or not 1<=limit<=100:raise ValueError('Choose a search session request cap from 1 to 100.')
            self.session_limit=limit
            if provider in ('serper','serpapi'):self.other_keys[provider]=new_key
            else:self.key=new_key
            if key is not None:self.cache.clear()
            self.provider=provider;self.enabled=data['enabled']
        return self.status()
    def _free_search(self,query,site):
        source='https://api.mwmbl.org/api/v2/search/?'+urlencode({'q':query})
        with self.free_lock:
            if time.monotonic()<self.cooldown_until:raise SearchLimit('Free search is cooling down after a provider rate/quota limit. No request sent; this is not a no-match result.')
            cached=self.cache.get(query)
            if cached and time.monotonic()-cached[0]<900:return source,copy.deepcopy(cached[1])
            if self.requests>=self.session_limit:raise SearchLimit('Configured session search limit reached.')
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
        if not isinstance(terms,list) or not 1<=len(terms)<=4 or any(not isinstance(t,str) or not t.strip() or len(t)>2000 or any(ord(c)<32 for c in t) for t in terms) or sum(len(t) for t in terms)>2200:raise ValueError('Invalid context search terms.')
        return self.search('',terms=terms)
    def search(self,value,site=None,terms=None):
        if site is not None and site not in ('instagram.com','tiktok.com','vsco.co','steamcommunity.com'):raise ValueError('Unsupported social index scope.')
        with self.lock:
            if not self.enabled:raise SearchNotConfigured('Web search was not run: enable free Mwmbl search in Search connection. Brave is optional; no payment is needed for Mwmbl.')
            provider=self.provider
            key=self.other_keys.get(provider,'') if provider in ('serper','serpapi') else self.key
            if provider!='mwmbl' and not key:raise SearchNotConfigured('Search provider is not configured. Choose free Mwmbl or add your own key.')
        query='"'+str(value).replace('"','').replace('\\','')+'"'
        if terms is not None:query=' '.join('"'+str(t).replace('"','').replace('\\','')+'"' for t in terms)
        if site:query='site:'+site+' '+query
        if provider=='mwmbl':return self._free_search(query,site)
        if provider in ('serper','serpapi'):return self._major_search(provider,key,query,site)
        source='https://api.search.brave.com/res/v1/web/search?'+urlencode({'q':query,'count':10,'safesearch':'moderate','text_decorations':'false'})
        identity=('brave',query,site)
        with self.lock:
            cached=self.cache.get(identity)
            if cached and time.monotonic()-cached[0]<900:
                rows,diagnostics=copy.deepcopy(cached[1]);diagnostics['cache_hit']=True
                return IndexResult(source,rows,diagnostics)
            if time.monotonic()<self.cooldown_until:raise SearchLimit('Brave search is cooling down after a quota/rate error; no request sent.')
            if self.requests>=self.session_limit:raise SearchLimit('Configured session search limit reached. Check your provider usage.')
            self.requests+=1
        req=Request(source,headers={'User-Agent':'Vidocq/'+VERSION,'Accept':'application/json','X-Subscription-Token':key})
        try:
            with build_opener(ProxyHandler({}),NoRedirect()).open(req,timeout=15) as response:raw=response.read(2_000_001)
            if len(raw)>2_000_000:raise ValueError('Search response exceeded its size limit.')
            try:data=json.loads(raw)
            except (ValueError,UnicodeError):raise ValueError('Search provider returned an unreadable response, not a no-match result.') from None
            if not isinstance(data,dict) or 'error' in data or not isinstance(data.get('query'),dict):raise ValueError('Search provider returned an unexpected response, not a no-match result.')
            web=data.get('web')
            if web is None:results=[]
            elif not isinstance(web,dict) or not isinstance(web.get('results'),list):raise ValueError('Search provider returned an unexpected web-result format.')
            else:results=web['results']
            rows=[];excluded={'malformed':0,'unsafe_url':0,'outside_scope':0,'duplicate':0};seen=set()
            for rank,item in enumerate(results[:10],1):
                if not isinstance(item,dict):excluded['malformed']+=1;continue
                url=str(item.get('url',''));p=urlparse(url)
                try:invalid_port=p.port is not None
                except ValueError:invalid_port=True
                if len(url)>2000 or p.scheme not in ('https','http') or not p.hostname or p.username or p.password or invalid_port:excluded['unsafe_url']+=1;continue
                if site and not (p.hostname==site or p.hostname.endswith('.'+site)):excluded['outside_scope']+=1;continue
                if url in seen:excluded['duplicate']+=1;continue
                seen.add(url)
                text=lambda x:html.unescape(re.sub('<[^>]+>','',str(x)))
                rows.append({'title':text(item.get('title','Indexed page'))[:500],'detail':text(item.get('description','No index snippet supplied.'))[:4000], 'reference':url,'index_rank':rank})
            diagnostics={'provider_rows':len(results),'examined_rows':min(10,len(results)),'retained_rows':len(rows),'excluded':excluded,'cache_hit':False,'query_mode':'quoted-terms','result_limit':10}
            with self.lock:self.cache[identity]=(time.monotonic(),copy.deepcopy((rows,diagnostics)))
            return IndexResult(source,rows,diagnostics)
        except HTTPError as error:
            if error.code in (401,403):raise ValueError('Search API key or plan was rejected. Check your Brave Search subscription and key; this is not a no-match result.') from None
            if error.code==429:
                self.cooldown_until=time.monotonic()+60
                raise SearchLimit('Search API quota/rate limit reached. Check provider usage; the query did not complete.') from None
            raise ValueError('Search provider unavailable (HTTP '+str(error.code)+'). Query did not complete.') from None
        except (URLError,TimeoutError,OSError):raise ValueError('Could not reach the search API. Check network/proxy settings; the query did not complete.') from None

    def _major_search(self,provider,key,query,site):
        identity=(provider,query)
        endpoint='https://google.serper.dev/search' if provider=='serper' else 'https://serpapi.com/search.json'
        source=endpoint+'?'+urlencode({'q':query,'engine':'google'})
        with self.lock:
            if time.monotonic()<self.cooldown_until:raise SearchLimit('Search provider is cooling down after a rate/quota error.')
            cached=self.cache.get(identity)
            if cached and time.monotonic()-cached[0]<900:return source,copy.deepcopy(cached[1])
            if self.requests>=self.session_limit:raise SearchLimit('Configured session search limit reached.')
            self.requests+=1
        if provider=='serper':req=Request(endpoint,data=json.dumps({'q':query,'num':10}).encode(),headers={'X-API-KEY':key,'Content-Type':'application/json'})
        else:req=Request(source+'&'+urlencode({'api_key':key,'num':10,'safe':'active'}),headers={'Accept':'application/json'})
        try:
            with build_opener(ProxyHandler({}),NoRedirect()).open(req,timeout=20) as response:raw=response.read(2_000_001)
            if len(raw)>2_000_000:raise ValueError('Search response exceeded its size limit.')
            data=json.loads(raw)
            if not isinstance(data,dict) or 'error' in data or not isinstance(data.get('search_metadata',{}),dict) or data.get('search_metadata',{}).get('status')=='Error':raise ValueError('Provider returned an error; this is not an empty result.')
            items=data.get('organic' if provider=='serper' else 'organic_results')
            if items is None:
                info=data.get('search_information');info=info if isinstance(info,dict) else {}
                explicit_empty=(provider=='serper' and isinstance(data.get('searchParameters'),dict)) or (provider=='serpapi' and info.get('organic_results_state')=='Fully empty')
                if not explicit_empty:raise ValueError('Search provider returned an unexpected response.')
                items=[]
            if not isinstance(items,list):raise ValueError('Malformed search results.')
            rows=[]
            for item in items[:10]:
                if not isinstance(item,dict) or not isinstance(item.get('link'),str) or not isinstance(item.get('title'),str):raise ValueError('Malformed search result item.')
                url=item['link'];p=urlparse(url)
                if len(url)>2000 or p.scheme not in ('https','http') or not p.hostname or p.username or p.password or (site and not (p.hostname==site or p.hostname.endswith('.'+site))):continue
                text=lambda v:html.unescape(re.sub('<[^>]+>','',str(v)))
                rows.append({'title':text(item['title'])[:500],'detail':text(item.get('snippet','No index snippet supplied.'))[:4000],'reference':url})
            with self.lock:self.cache[identity]=(time.monotonic(),copy.deepcopy(rows))
            return source,rows
        except HTTPError as error:
            if error.code in (401,403):raise ValueError('Search provider rejected the key/plan. No automatic paid fallback was attempted.') from None
            if error.code==429:self.cooldown_until=time.monotonic()+60;raise SearchLimit('Search provider quota/rate limit reached; query incomplete.') from None
            raise ValueError('Search provider unavailable (HTTP '+str(error.code)+').') from None
        except (URLError,TimeoutError,OSError):raise ValueError('Search provider could not be reached; query incomplete.') from None
        except (json.JSONDecodeError,UnicodeError):raise ValueError('Search provider returned unreadable JSON.') from None

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
