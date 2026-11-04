"""Real packaged API checks with synthetic saved sessions; never logs into Instagram."""
import hashlib,json,time,urllib.error
from credential_vault import Vault

def check(request,root):
    def get(path,p=None):
        with request(path,p) as response:return json.load(response)
    def rejected(path,p):
        try:get(path,p);raise AssertionError('Missing consent or invalid payload accepted')
        except urllib.error.HTTPError as e:assert e.code==400
    def wait_setup():
        deadline=time.monotonic()+90
        while get('/api/automation')['busy']:
            assert time.monotonic()<deadline;time.sleep(.25)
    with request('/research-workflow.js') as response:assert b'instagram-login-form' in response.read()
    rejected('/api/instagram-login/start',{'username':'operatorfixture','password':'synthetic-password','consent':False})
    # Invalid username fails before creating an SDK client or making any login call,
    # while real companion startup imports the bundled pinned dependency.
    rejected('/api/instagram-login/start',{'username':'','password':'synthetic-password','consent':True})
    get('/api/automation',{'consent':True});wait_setup()
    vault=Vault(root/'data');session={'authorization_data':{'ds_user_id':'123456','sessionid':'synthetic-frozen-session-secret'},'cookies':{'ds_user_id':'123456','sessionid':'synthetic-frozen-session-secret'}}
    vault.save_instagram('operatorfixture',session)
    get('/api/automation',{'consent':True,'osintgram':True});wait_setup()
    state=get('/api/instagram-login');assert state['connected'] and state['saved'] and 'session' not in state and 'synthetic-frozen-session-secret' not in json.dumps(state)
    state=get('/api/search-connection',{'provider':'serper','key':'synthetic-frozen-search-key','enabled':False,'remember':True,'session_limit':3})
    assert state['provider']=='serper' and not state['enabled'] and 'synthetic-frozen-search-key' not in json.dumps(state)
    raw=(root/'data/credentials.dpapi').read_bytes();assert b'synthetic-frozen-session-secret' not in raw and b'synthetic-frozen-search-key' not in raw
    case=get('/api/cases',{'title':'Synthetic guided workflow','names':['Example Person'],'usernames':['publicfixture'],'investigation':{'enabled':True,'allow_maigret':False,'max_searches':8}})
    def run(path,p):
        started=get(path,p);deadline=time.monotonic()+30
        while True:
            report=get('/api/case-runs/'+started['id'])
            if report['status']=='complete':return report
            assert report['status'] in ('queued','running') and time.monotonic()<deadline;time.sleep(.1)
    first=run('/api/cases/'+case['id']+'/run',{'consent':True});original=json.dumps(first,sort_keys=True)
    path='/api/cases/'+case['id'];plan=get(path+'/review-plan',{});assert plan['previous_run']==first['id'] and plan['queries']
    payload={'consent':True,'public_reviewed':True,'reference':'https://github.com/publicfixture','display_name':'Example Person','handle':'publicfixture','stable_id':'1234','biography':'Public fixture bio links https://gitlab.com/linkedfixture','links':['https://gitlab.com/linkedfixture']}
    assert get(path+'/profile-capture',payload)['result']['profile']['stable_id']=='1234'
    rejected(path+'/profile-capture',{**payload,'consent':False})
    rejected(path+'/profile-capture',{'consent':True,'mode':'public-fetch','reference':'https://example.org/login'})
    rejected(path+'/continue',{'previous_run':first['id'],'consent':False})
    second=run(path+'/continue',{'previous_run':first['id'],'consent':True})
    assert second['continued_from']==first['id'] and second['profile_graph']['nodes'] and second['link_evidence']
    assert json.dumps(get('/api/case-runs/'+first['id']),sort_keys=True)==original
    get('/api/automation',{'consent':True});wait_setup();vault.invalidate_instagram()
    get('/api/automation',{'consent':True,'osintgram':True});wait_setup()
    expired=get('/api/instagram-login');assert expired['needs_reconnect'] and not expired['connected'] and not get('/api/automation')['credentials']['saved']
    get('/api/instagram-login/forget',{});assert not get('/api/instagram-login')['saved'];assert vault.search_key('serper')=='synthetic-frozen-search-key'
    get('/api/automation',{'consent':True});wait_setup()
    print('Frozen guided-session restore/forget, provider-key encryption, reviewed bio/ID/link graph and consented new-report continuation passed without Instagram login or paid queries.')
