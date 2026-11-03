"""Optional Brave web-index retrieval. Never fetches original result URLs."""
import html,json,os,re,threading
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
        self.key=os.environ.get('VIDOCQ_BRAVE_API_KEY','');self.enabled=bool(self.key)
        self.lock=threading.RLock();self.requests=0
    def status(self):
        with self.lock:return {'configured':bool(self.key),'enabled':self.enabled,'provider':'Brave Search API','session_requests':self.requests,'session_limit':100,'message':'Connected for index searches.' if self.key and self.enabled else 'General web search is not connected. No web results can be retrieved until you add and enable your own API key.'}
    def configure(self,data):
        if not isinstance(data,dict) or type(data.get('enabled')) is not bool:raise ValueError('Choose whether web search is enabled.')
        key=data.get('key')
        with self.lock:
            if key is not None:
                if not isinstance(key,str) or len(key)>500 or (key and not re.fullmatch(r'[A-Za-z0-9._-]+',key)):raise ValueError('Invalid API key format.')
                self.key=key
            if data['enabled'] and not self.key:raise ValueError('Enter a Brave Search API key before enabling web search.')
            self.enabled=data['enabled']
        return self.status()
    def search(self,value,site=None):
        if site is not None and site not in ('instagram.com','tiktok.com','vsco.co'):raise ValueError('Unsupported social index scope.')
        with self.lock:
            if not self.enabled or not self.key:raise SearchNotConfigured('Web search was not run: connect your own Brave Search API key in Search connection. Wikipedia/news indexes do not cover most people or identifiers.')
            if self.requests>=100:raise SearchLimit('Session search limit reached (100 API calls). Check your provider usage before reconnecting in a new app session.')
            key=self.key;self.requests+=1
        query='"'+str(value).replace('"','').replace('\\','')+'"'
        if site:query='site:'+site+' '+query
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
