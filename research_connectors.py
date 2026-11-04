"""Opt-in Steam API and local Osintgram 2.x adapters; never execute downloaded code."""
import json
import re
import secrets
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, HTTPRedirectHandler, ProxyHandler, build_opener

class ConnectorUnavailable(ValueError): pass

def is_steam_id(value):
    return isinstance(value,str) and bool(re.fullmatch(r'\d{17}',value)) and 76561197960265728<=int(value)<=76561202255233023

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Connector redirect refused; credentials were not forwarded.')

def normalize_steam(value):
    if not isinstance(value, str) or len(value)>240 or any(ord(c)<32 for c in value): raise ValueError('Enter a SteamID64 or Steam profile/vanity URL.')
    value=value.strip()
    if is_steam_id(value):return 'https://steamcommunity.com/profiles/'+value+'/'
    if '/' not in value and re.fullmatch(r'[A-Za-z0-9_-]{2,64}',value):return 'https://steamcommunity.com/id/'+value.lower()+'/'
    try:
        p=urlparse(value if '://' in value else 'https://'+value)
        if p.scheme not in ('https','http') or p.hostname not in ('steamcommunity.com','www.steamcommunity.com') or p.username or p.password or p.port is not None: raise ValueError()
        parts=p.path.strip('/').split('/')
        if len(parts)!=2 or parts[0] not in ('id','profiles'):raise ValueError()
        if parts[0]=='profiles' and not is_steam_id(parts[1]):raise ValueError()
        if parts[0]=='id' and not re.fullmatch(r'[A-Za-z0-9_-]{2,64}',parts[1]):raise ValueError()
        return 'https://steamcommunity.com/'+parts[0]+'/'+parts[1].lower()+'/'
    except ValueError:raise ValueError('Use a Steam profile URL, not a group, game or arbitrary website.') from None

def read_json(url, payload=None, local=False, timeout=20, local_key=None):
    """Only fixed destinations constructed by this module may be requested."""
    p=urlparse(url)
    allowed=(p.scheme=='http' and p.hostname=='127.0.0.1' and p.path in ('/api/about','/api/run','/api/cancel') and p.port and 1024<=p.port<=65535) if local else (p.scheme=='https' and p.hostname in ('api.steampowered.com','communitybanlist.com') and p.port is None)
    if not allowed or p.username or p.password: raise ValueError('Connector destination is not reviewed.')
    headers={'Accept':'application/json','User-Agent':'Vidocq research connector'}
    if local_key:headers['X-Vidocq-Key']=local_key
    data=None
    if payload is not None:headers['Content-Type']='application/json';data=json.dumps(payload).encode()
    try:
        with build_opener(ProxyHandler({}),NoRedirect()).open(Request(url,data=data,headers=headers),timeout=timeout) as response:
            raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError('Connector response exceeded 2 MB.')
        return json.loads(raw)
    except HTTPError as e:raise ConnectorUnavailable('Connector returned HTTP '+str(e.code)+'. Check access, quota and configuration; this is not a no-match result.') from None
    except (URLError,TimeoutError,OSError):raise ConnectorUnavailable('Connector could not be reached. Check configuration and access; this is not a no-match result.') from None
    except (json.JSONDecodeError,UnicodeError):raise ConnectorUnavailable('Connector returned unreadable data.') from None

class ResearchConnectors:
    def __init__(self):
        self.lock=threading.RLock();self.steam_key='';self.steam_enabled=False;self.cbl=False
        self.osintgram_enabled=False;self.port=8000;self.requests={'steam':0,'osintgram':0};self.pending={};self.cancelled_runs=set()
        self.managed_key=None;self.managed_manager=None;self.managed_vault=None

    def status(self):
        with self.lock:return {'steam':{'enabled':self.steam_enabled,'configured':bool(self.steam_key),'session_requests':self.requests['steam'],'session_limit':100,'cbl':self.cbl},
                               'osintgram':{'enabled':self.osintgram_enabled,'port':self.port,'session_runs':self.requests['osintgram'],'session_limit':20},
                               'notice':'Steam queries go to Valve (and optionally CBL). Osintgram forwards Instagram lookups through its configured backend; provider charges and platform logging can apply. Keys remain in memory in Vidocq.'}

    def configure(self,p):
        with self.lock:
            enabled=p.get('steam_enabled',False);og=p.get('osintgram_enabled',False);cbl=p.get('cbl',False);port=p.get('osintgram_port',8000)
            if any(type(v) is not bool for v in (enabled,og,cbl)) or type(port) is not int or not 1024<=port<=65535:raise ValueError('Invalid connector settings.')
            candidate=p.get('steam_key',self.steam_key)
            if not isinstance(candidate,str) or (candidate and not re.fullmatch('[A-Fa-f0-9]{32}',candidate)):raise ValueError('A Steam Web API key has 32 hexadecimal characters.')
            if enabled and not candidate:raise ValueError('Enter your Steam Web API key before enabling Steam.')
            self.steam_key=candidate;self.steam_enabled=enabled;self.osintgram_enabled=og;self.port=port;self.cbl=cbl
        if self.managed_manager and (not og or port!=self.managed_manager.entries.get('osintgram',{}).get('port')):
            self.managed_manager.stop('osintgram');self.managed_manager=None;self.managed_key=None;self.managed_vault=None
        return self.status()

    def _reserve(self,kind):
        with self.lock:
            limit=100 if kind=='steam' else 20
            if self.requests[kind]>=limit:raise ConnectorUnavailable('Connector session limit reached; review provider usage before a new session.')
            self.requests[kind]+=1

    def steam(self,value,app_id=None):
        canonical=normalize_steam(value)
        with self.lock:key=self.steam_key;enabled=self.steam_enabled;cbl=self.cbl
        if not enabled or not key:raise ConnectorUnavailable('Steam was not queried: enable your Steam Web API connection.')
        if app_id is not None and (type(app_id) is not int or not 1<=app_id<=2147483647):raise ValueError('Invalid game AppID.')
        results=[]
        def request(path,params):
            self._reserve('steam')
            # The key is never placed in saved source references or exception messages.
            return read_json('https://api.steampowered.com/'+path+'?'+urlencode(dict(params,key=key)))
        parts=urlparse(canonical).path.strip('/').split('/');steamid=parts[1]
        if parts[0]=='id':
            resolved=request('ISteamUser/ResolveVanityURL/v1/',{'vanityurl':steamid})
            response=resolved.get('response',{}) if isinstance(resolved,dict) else {}
            if not isinstance(response,dict):raise ValueError('Steam resolution response was malformed.')
            steamid=str(response.get('steamid',''))
            if response.get('success')!=1 or not is_steam_id(steamid):raise ConnectorUnavailable('Steam vanity name did not resolve. This is not proof of identity or absence elsewhere.')
        reference='https://steamcommunity.com/profiles/'+steamid+'/'
        def collect(label,path,params,transform):
            try:
                data=request(path,params);rows=transform(data)
                results.append({'provider':label,'status':'ok' if rows else 'empty','source':'https://api.steampowered.com/'+path,'rows':rows})
            except ValueError as error:results.append({'provider':label,'status':'error','message':str(error),'rows':[]})
        def profile(data):
            response=data.get('response') if isinstance(data,dict) else None
            players=response.get('players') if isinstance(response,dict) else None
            if not isinstance(players,list):raise ValueError('Steam profile response was malformed.')
            selected=[p for p in players if isinstance(p,dict) and str(p.get('steamid'))==steamid]
            rows=[]
            for p in selected[:1]:
                allowed={k:p[k] for k in ('steamid','personaname','realname','profileurl','communityvisibilitystate','timecreated','loccountrycode') if k in p}
                rows.append({'title':'Steam profile: '+str(p.get('personaname',steamid))[:200],'detail':json.dumps(allowed,ensure_ascii=False)+'\nPublic profile fields; supplied account ownership is not verified.','reference':reference,'observations':{'reported_name':p.get('realname',''),'display_name':p.get('personaname',''),'country':p.get('loccountrycode','')},'identifiers':[{'kind':'steam','value':canonical}]})
            return rows
        def games(data,recent=False):
            response=data.get('response') if isinstance(data,dict) else None
            if not isinstance(response,dict) or type(response.get('game_count')) is not int or response['game_count']<0 or (response.get('game_count') and not isinstance(response.get('games'),list)):
                raise ValueError('Game library was not disclosed (private, unavailable or unexpected response). Do not interpret this as no games owned.')
            items=response.get('games') or []
            if not isinstance(items,list):raise ValueError('Steam returned a malformed games list.')
            selected=[g for g in items if isinstance(g,dict) and (app_id is None or g.get('appid')==app_id)]
            if app_id is not None and not selected:return [{'title':'Requested Steam game not listed','detail':'AppID '+str(app_id)+' was not listed in this returned library. Access and completeness limits apply.','reference':reference}]
            shown=[{k:g[k] for k in ('appid','name','playtime_forever','playtime_2weeks') if k in g} for g in selected[:100]]
            return [{'title':'Steam '+('recent games' if recent else 'game library'),'detail':json.dumps({'reported_game_count':response.get('game_count'),'shown':shown,'truncated':len(selected)>100,'playtime_units':'minutes'},ensure_ascii=False)+'\nPublic API response; no gameplay location or real identity inferred.','reference':reference}]
        collect('Steam public profile','ISteamUser/GetPlayerSummaries/v2/',{'steamids':steamid},profile)
        collect('Steam game library','IPlayerService/GetOwnedGames/v1/',{'steamid':steamid,'include_appinfo':1,'include_played_free_games':1},games)
        collect('Steam recent games','IPlayerService/GetRecentlyPlayedGames/v1/',{'steamid':steamid,'count':20},lambda d:games(d,True))
        if cbl:
            try:
                self._reserve('steam')
                query='query { steamUser(id: "'+steamid+'") { id name reputationPoints riskRating activeBans: bans(orderBy: "created", orderDirection: DESC, expired: false) { edges { node { id created expires reason banList { name organisation { name } } } } } expiredBans: bans(orderBy: "created", orderDirection: DESC, expired: true) { edges { node { id created expires reason banList { name organisation { name } } } } } } }'
                data=read_json('https://communitybanlist.com/graphql',{'query':query})
                if not isinstance(data,dict) or data.get('errors'):raise ValueError('CBL returned an error; no reputation conclusion was made.')
                payload=data.get('data')
                if not isinstance(payload,dict):raise ValueError('CBL returned an unexpected response, not a no-match result.')
                user=payload.get('steamUser')
                if user is not None and not isinstance(user,dict):raise ValueError('CBL returned an unexpected user record.')
                if isinstance(user,dict):
                    for field in ('activeBans','expiredBans'):
                        page=user.get(field) or {}
                        if not isinstance(page,dict):raise ValueError('CBL returned an unexpected ban-list format.')
                        edges=page.get('edges',[])
                        if isinstance(edges,list):user[field]={'returned_count':len(edges),'shown':edges[:20],'truncated':len(edges)>20,'notice':'Returned provider records only; completeness and allegations are not independently verified.'}
                results.append({'provider':'Community Ban List','status':'ok' if user else 'empty','source':'https://communitybanlist.com/graphql','rows':[{'title':'CBL provider record (unverified)','detail':json.dumps(user,ensure_ascii=False)+'\nThird-party provider rating only; not a Vidocq risk assessment or identity match.','reference':'https://communitybanlist.com/search/'+steamid}] if user else []})
            except ValueError as error:results.append({'provider':'Community Ban List','status':'error','message':str(error),'rows':[]})
        return {'results':results,'links':[]}

    def osintgram(self,handle,run_id,commands):
        from social_profiles import normalize_profile,profile_reference
        handle=normalize_profile('instagram',handle)
        allowed={'get_user_info','get_account_about','get_captions','get_hashtags'}
        if not isinstance(commands,list) or not commands or any(c not in allowed for c in commands):raise ValueError('Unsupported Osintgram commands.')
        commands=list(dict.fromkeys(['get_user_info']+commands))
        with self.lock:
            enabled=self.osintgram_enabled;port=self.port
            if run_id in self.cancelled_runs:raise ConnectorUnavailable('Osintgram run was cancelled before it started.')
        if not enabled:raise ConnectorUnavailable('Osintgram was not queried: enable the local Osintgram 2.x connection.')
        if self.managed_manager:
            self.managed_key,port=self.managed_manager.ensure('osintgram',self.managed_vault.osintgram());self.port=port
        base='http://127.0.0.1:'+str(port)
        def local_request(path,payload=None,timeout=20):
            return read_json(base+path,payload,local=True,timeout=timeout,**({'local_key':self.managed_key} if self.managed_key else {}))
        about=local_request('/api/about')
        if not isinstance(about,dict) or about.get('repository')!='https://github.com/Datalux/Osintgram':raise ValueError('The selected local service does not identify itself as Osintgram 2.x.')
        if about.get('needs_reconnect'):
            if self.managed_vault:self.managed_vault.invalidate_instagram()
            raise ConnectorUnavailable('Instagram session expired or was challenged. Reconnect explicitly in Search connection; no automatic login was attempted.')
        self._reserve('osintgram');job='vidocq-'+secrets.token_hex(12)
        with self.lock:self.pending[job]=(run_id,base)
        try:
            def fetch_calls(selected,budget):
                calls=[{'name':c,'args':{'limit_posts':5} if c in ('get_captions','get_hashtags') else {}} for c in selected]
                response=local_request('/api/run',{'target':handle,'calls':calls,'max_items':budget,'cache_ttl_seconds':3600,'run_id':job,'verbose':False},timeout=60)
                if not isinstance(response,dict) or not isinstance(response.get('target'),str) or response['target'].lower()!=handle or not isinstance(response.get('tool_calls'),list):raise ValueError('Osintgram returned an unexpected target or result format.')
                return response
            data=fetch_calls(['get_user_info'],5)
            # Do not ask an authenticated backend to retrieve private content, even if it can.
            profile=next((c.get('result') for c in data['tool_calls'] if isinstance(c,dict) and c.get('name')=='get_user_info' and not c.get('is_error')),None)
            if isinstance(profile,dict) and (not isinstance(profile.get('username'),str) or profile['username'].lower()!=handle):raise ValueError('Osintgram profile username did not match the requested account.')
            extra=[c for c in commands if c!='get_user_info']
            spent=data.get('api_calls_total');remaining=max(0,5-spent) if type(spent) is int and spent>=0 else 0
            with self.lock:cancelled=run_id in self.cancelled_runs
            if extra:
                reason=None
                if not isinstance(profile,dict) or profile.get('is_private') is not False:reason='Extra Osintgram commands were not run: profile privacy is private or unknown.'
                elif cancelled:reason='Extra Osintgram commands were not run: investigation was cancelled.'
                elif not remaining:reason='Extra Osintgram commands were not run: the profile request exhausted or did not report the request budget.'
                if reason:
                    data['tool_calls'].extend({'name':c,'is_error':True,'vidocq_reason':reason} for c in extra)
                else:
                    try:
                        additional=fetch_calls(extra,remaining)
                        data['tool_calls'].extend(additional['tool_calls'])
                        data['needs_reconnect']=bool(data.get('needs_reconnect') or additional.get('needs_reconnect'))
                        if type(additional.get('api_calls_total')) is int:data['api_calls_total']=spent+additional['api_calls_total']
                    except ValueError:
                        self._cancel_job(base,job)
                        data['tool_calls'].extend({'name':c,'is_error':True,'vidocq_reason':'Extra Osintgram commands failed; the completed profile result was retained.'} for c in extra)
            if data.get('needs_reconnect') and self.managed_vault:self.managed_vault.invalidate_instagram()
            results=[]
            for call in data['tool_calls']:
                if not isinstance(call,dict) or call.get('name') not in commands:continue
                name=call['name'];value=call.get('result')
                if call.get('is_error') or (isinstance(value,dict) and 'error' in value):
                    results.append({'provider':'Osintgram / '+name,'status':'error','message':call.get('vidocq_reason','Osintgram could not complete this command. Check its backend, quota and profile access.'),'rows':[]});continue
                if name=='get_user_info' and isinstance(value,dict):
                    fields=('id','username','full_name','biography','follower_count','following_count','media_count','is_private','is_business','is_verified','external_url','bio_links','public_email','public_phone_number','public_phone_country_code','category')
                    value={k:value[k] for k in fields if k in value}
                    phone=str(value.get('public_phone_number',''));country=str(value.get('public_phone_country_code',''))
                    if phone and country and not phone.startswith('+'):
                        from phone_lookup import inspect_phone
                        try:value['public_phone_e164']=inspect_phone('+'+country.lstrip('+')+phone)['e164']
                        except ValueError:pass
                if isinstance(value,list):value=value[:100]
                detail=json.dumps(value,ensure_ascii=False)
                truncated=len(detail)>11000;detail=detail[:11000]
                observations={'reported_name':value.get('full_name',''),'private_profile':value.get('is_private')} if name=='get_user_info' and isinstance(value,dict) else {}
                if name=='get_user_info' and isinstance(value,dict):
                    public_links=[]
                    for link in ([value.get('external_url')] if value.get('external_url') else [])+(value.get('bio_links',[]) if isinstance(value.get('bio_links'),list) else []):
                        url=link.get('url') if isinstance(link,dict) else link
                        if isinstance(url,str) and url.startswith('https://'):public_links.append(url[:2000])
                    observations['profile']={'platform':'instagram.com','handle':handle,'stable_id':str(value.get('id',''))[:128],'display_name':str(value.get('full_name',''))[:200],'biography':str(value.get('biography',''))[:6000],'links':public_links[:50]}
                results.append({'provider':'Osintgram / '+name,'source':base+'/api/run','status':'ok' if value else 'empty','rows':[{'title':'Instagram @'+handle+' · '+name,'detail':detail+('\nResult truncated to report limit.' if truncated else '')+'\nPublic data via configured Osintgram backend. Relevance and ownership remain unverified.','reference':profile_reference('instagram',handle),'observations':observations,'identifiers':[{'kind':'instagram','value':handle}]}] if value else []})
            if not results:raise ValueError('Osintgram returned no recognized command results.')
            return {'results':results,'links':[],'backend_requests':data.get('api_calls_total')}
        except ValueError:
            self._cancel_job(base,job)
            if self.managed_manager and self.managed_vault:
                try:
                    state=self.managed_manager.request('osintgram','/api/auth/status')
                    if state.get('needs_reconnect'):self.managed_vault.invalidate_instagram()
                except (ValueError,OSError):pass
            raise
        finally:
            with self.lock:self.pending.pop(job,None)

    def _cancel_job(self,base,job):
        try:read_json(base+'/api/cancel',{'run_id':job},local=True,timeout=5,local_key=self.managed_key if self.managed_manager else '')
        except ValueError:pass

    def cancel(self,run_id):
        with self.lock:
            self.cancelled_runs.add(run_id)
            jobs=[(job,base) for job,(owner,base) in self.pending.items() if owner==run_id]
        for job,base in jobs:self._cancel_job(base,job)

CLIENT=ResearchConnectors()
