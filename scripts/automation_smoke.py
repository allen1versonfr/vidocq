"""Frozen setup/credential and reviewed browser relay checks; no subject queries."""
import json,subprocess,time,urllib.request,urllib.error
from urllib.parse import quote

def check(request,root,exe,env):
    with request('/automation.js') as response:assert b'og-credentials-form' in response.read()
    with request('/api/automation') as response:state=json.load(response)
    assert state['needs_osintgram_credentials'] and not state['credentials']['saved']
    assert all(v['bundled'] for v in state['services'].values())
    try:request('/api/automation',{'consent':False});raise AssertionError('Setup accepted missing consent')
    except urllib.error.HTTPError as e:assert e.code==400
    secret='synthetic-provider-key-not-valid-for-lookups'
    with request('/api/automation/credentials',{'hiker_key':secret}) as response:
        saved=json.load(response);assert saved['saved'] and secret not in json.dumps(saved)
    choices={'consent':True,'harvester':True,'photon':True,'osintgram':True}
    deadline=time.monotonic()+90
    while True:
        with request('/api/automation') as response:state=json.load(response)
        if not state['busy']:break
        assert time.monotonic()<deadline;time.sleep(.25)
    with request('/api/automation',choices) as response:json.load(response)
    while True:
        with request('/api/automation') as response:state=json.load(response)
        if not state['busy']:break
        assert time.monotonic()<deadline;time.sleep(.25)
    assert all(v['running'] for v in state['services'].values()),state
    assert secret not in json.dumps(state) and secret.encode() not in (root/'data/credentials.dpapi').read_bytes()
    with request('/api/automation/licenses') as response:assert 'GNU' in json.load(response)['text']
    with request('/api/collectors') as response:collectors=json.load(response)
    with request('/api/connectors') as response:connectors=json.load(response)
    for port in [collectors['harvester']['port'],connectors['osintgram']['port']]:
        try:urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/api/about',timeout=5);raise AssertionError('Companion exposed unauthenticated data')
        except urllib.error.HTTPError as e:assert e.code in (401,403)
    with request('/api/cases',{'title':'Synthetic native browser relay','usernames':['publicfixture']}) as response:case=json.load(response)
    capture={'case_id':case['id'],'data':{'schema':'vidocq-browser-v1','title':'Selected public fixture','reference':'https://example.org/about','excerpt':'Reviewed source text with a published account link.','links':['https://github.com/example']}}
    relay=json.loads((root/'data/browser-relay.json').read_text(encoding='utf-8'))
    relay_url='http://127.0.0.1:'+str(relay['port'])+'/api/browser-relay'
    for headers in [{},{'X-Vidocq-Relay':relay['key'],'Origin':'https://example.org'}]:
        try:urllib.request.urlopen(urllib.request.Request(relay_url,data=json.dumps(capture).encode(),headers=headers),timeout=5);raise AssertionError('Untrusted relay accepted')
        except urllib.error.HTTPError as e:assert e.code==403
    uri='vidocq-evidence://capture?data='+quote(json.dumps(capture))
    subprocess.run([str(exe),'--browser-capture',uri],env=env,timeout=90,check=True)
    with request('/api/browser-pending') as response:pending=json.load(response)
    assert len(pending)==1 and pending[0]['case_id']==case['id']
    try:request('/api/browser-capture/review',{'id':pending[0]['id'],'consent':False});raise AssertionError('Unreviewed capture committed')
    except urllib.error.HTTPError as e:assert e.code==400
    with request('/api/browser-capture/review',{'id':pending[0]['id'],'consent':True}) as response:assert response.status==201
    with request('/api/browser-pending') as response:assert json.load(response)==[]
    with request('/api/checker-controls') as response:assert json.load(response)
    with request('/api/automation',{'consent':True}) as response:json.load(response)
    deadline=time.monotonic()+30
    while True:
        with request('/api/automation') as response:state=json.load(response)
        if not state['busy']:break
        assert time.monotonic()<deadline;time.sleep(.25)
    assert not any(v['running'] for v in state['services'].values())
    with request('/api/automation/credentials',{'forget':True}) as response:assert not json.load(response)['saved']
    print('Frozen bundled collector setup/authentication, encrypted credential save/forget and native browser relay/review passed; no provider lookups ran.')
