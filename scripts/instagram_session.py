"""GPL-3.0-only guided operator login; no implicit login during target lookup."""
import copy,json,queue,re,secrets,threading,time

class ReconnectRequired(ValueError):pass
class ManualChallenge(ValueError):pass
SESSION_FIELDS=('uuids','mid','ig_u_rur','ig_www_claim','authorization_data','cookies','last_login','device_settings','user_agent','country','country_code','locale','timezone_offset')

def clean_session(value):
    if not isinstance(value,dict) or len(json.dumps(value))>200000:raise ValueError('Invalid Instagram session.')
    value={k:copy.deepcopy(v) for k,v in value.items() if k in SESSION_FIELDS}
    auth=value.get('authorization_data',{});cookies=value.get('cookies',{})
    if not isinstance(auth,dict) or not isinstance(cookies,dict) or not str(auth.get('ds_user_id') or cookies.get('ds_user_id','')).isdigit() or not (auth.get('sessionid') or cookies.get('sessionid')):raise ValueError('Instagram session is missing authentication. Reconnect explicitly.')
    return value

def locked_client(session,factory=None,on_reconnect=None):
    if factory is None:
        from instagrapi import Client
        factory=Client
    client=factory();settings=clean_session(session);settings.update(session_retry_total=0,public_request_retries_count=0,request_timeout=15);client.set_settings(settings);client.password=''
    client.private.trust_env=False;client.public.trust_env=False
    def deny(*args,**kwargs):
        if on_reconnect:on_reconnect()
        raise ReconnectRequired('Session expired or challenged. Reconnect explicitly in Vidocq; no automatic login was attempted.')
    for name in ('login','login_legacy','login_by_sessionid','relogin','bloks_caa_login','challenge_resolve','challenge_code_handler'):setattr(client,name,deny)
    original=getattr(client,'private_request',None)
    if original:
        def read_only(endpoint,*args,**kwargs):
            if not isinstance(endpoint,str) or not re.fullmatch(r'(users/[A-Za-z0-9_.]+/(usernameinfo|info)/|feed/user/[0-9]+/)',endpoint) or kwargs.get('login'):raise ReconnectRequired('Endpoint outside the approved read-only profile scope; no automatic authentication or account action was attempted.')
            try:return original(endpoint,*args,**kwargs)
            except Exception as error:
                if on_reconnect and type(error).__name__ in ('LoginRequired','ChallengeRequired','ChallengeUnknownStep','ChallengeRedirection'):on_reconnect()
                raise
        client.private_request=read_only
    return client

class Login:
    def __init__(self,factory=None):
        self.factory=factory;self.lock=threading.RLock();self.worker=None;self.phase='idle';self.message='Connect your own operator account. This is session login, not OAuth.';self.username='';self.session=None;self.id='';self.codes=queue.Queue();self.cancelled=threading.Event();self.deadline=0
    def status(self):
        with self.lock:return {'phase':self.phase,'message':self.message,'username':self.username,'login_id':self.id,'busy':bool(self.worker and self.worker.is_alive()),'connected':self.phase=='connected','needs_reconnect':self.phase=='reconnect-required'}
    def restore(self,credentials):
        if credentials.get('needs_reconnect'):self.username=credentials.get('username','');self.reconnect();return
        self.session=clean_session(credentials['session']);self.username=credentials.get('username','');self.phase='connected';self.id=secrets.token_hex(12);self.message='Saved operator session loaded. No network login ran.'
    def start(self,p):
        if p.get('consent') is not True:raise ValueError('Approve signing in to your own Instagram account. Login/security alerts can reach that account.')
        user=p.get('username','');password=p.get('password','')
        if not isinstance(user,str) or not re.fullmatch(r'[A-Za-z0-9_.]{1,30}',user) or not isinstance(password,str) or not 1<=len(password)<=1024:raise ValueError('Enter your operator username and password.')
        with self.lock:
            if self.worker and self.worker.is_alive():raise ValueError('A login is already in progress.')
            self.cancelled.clear();self.codes=queue.Queue();self.session=None;self.username=user;self.id=secrets.token_hex(12);self.phase='signing-in';self.message='Signing in to your operator account…';self.deadline=time.monotonic()+300
            self.worker=threading.Thread(target=self._login,args=(user,password),daemon=True);self.worker.start()
        return self.status()
    def _login(self,user,password):
        client=None
        try:
            if self.factory is None:
                from instagrapi import Client
                factory=Client
            else:factory=self.factory
            client=factory();client.request_timeout=15;client.login_flow=lambda:None;client.private.trust_env=False;client.public.trust_env=False
            def challenge(*a,**kw):raise ManualChallenge('Complete the account challenge in Instagram, then reconnect. Vidocq does not solve challenges or request recovery codes.')
            client.challenge_resolve=challenge;client.challenge_code_handler=challenge
            try:success=client.login(user,password)
            except Exception as error:
                if type(error).__name__!='TwoFactorRequired':raise
                with self.lock:self.phase='two-factor-required';self.message='Enter the 2FA code for your operator account. No subject credentials are needed.'
                try:code=self.codes.get(timeout=max(.1,self.deadline-time.monotonic()))
                except queue.Empty:raise ReconnectRequired('Login expired. Start again explicitly.') from None
                if self.cancelled.is_set() or code is None:raise ReconnectRequired('Login cancelled.')
                with self.lock:self.phase='signing-in';self.message='Checking the supplied 2FA code…'
                success=client.login(user,password,verification_code=code)
            if not success:raise ReconnectRequired('Instagram did not establish a session. Check your account in Instagram and reconnect.')
            session=clean_session(client.get_settings())
            if self.cancelled.is_set() or time.monotonic()>self.deadline:raise ReconnectRequired('Login cancelled or expired.')
            with self.lock:self.session=session;self.phase='connected';self.message='Connected. Password discarded; save the encrypted session in Vidocq.'
        except ManualChallenge:
            with self.lock:self.phase='challenge-required';self.message='Complete the challenge directly in Instagram, then start login again. No automatic challenge or recovery flow is used.'
        except Exception:
            with self.lock:self.session=None;self.phase='cancelled' if self.cancelled.is_set() else 'failed';self.message='Login cancelled.' if self.cancelled.is_set() else 'Instagram login failed or expired. Check your credentials/2FA and account in Instagram, then reconnect explicitly.'
        finally:
            password=''
            if client:
                client.password=''
                try:client.private.close();client.public.close()
                except Exception:pass
    def code(self,p):
        code=p.get('code','')
        if self.phase!='two-factor-required' or p.get('login_id')!=self.id or not isinstance(code,str) or not re.fullmatch(r'[0-9]{6,8}',code):raise ValueError('Enter the current 6–8 digit operator 2FA code.')
        self.codes.put(code);return self.status()
    def cancel(self):
        self.cancelled.set();self.codes.put(None)
        with self.lock:self.session=None;self.phase='cancelled';self.message='Login cancelled; no session saved.'
        return self.status()
    def reconnect(self):
        with self.lock:self.session=None;self.phase='reconnect-required';self.message='Instagram session expired or was challenged. Reconnect explicitly; no automatic login was attempted.'
    def export(self):
        if self.phase!='connected' or not self.session:raise ValueError('No connected Instagram session.')
        return {'username':self.username,'session':copy.deepcopy(self.session),'login_id':self.id}
