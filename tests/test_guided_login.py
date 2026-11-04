import copy,json,os,tempfile,time,unittest
from unittest.mock import MagicMock,patch
from credential_vault import Vault
from scripts.instagram_session import Login,locked_client,clean_session,ReconnectRequired
from instagram_login import InstagramLogin

SESSION={'authorization_data':{'ds_user_id':'123456','sessionid':'synthetic-session-secret'},'cookies':{'ds_user_id':'123456','sessionid':'synthetic-session-secret'},'uuids':{},'device_settings':{},'password':'must-not-survive'}
class TwoFactorRequired(Exception):pass
class FakeClient:
    def __init__(self):self.password='';self.private=MagicMock();self.public=MagicMock();self.calls=[]
    def set_settings(self,value):self.settings=copy.deepcopy(value)
    def login(self,user,password,verification_code=''):
        self.calls.append((user,password,verification_code))
        if not verification_code:raise TwoFactorRequired()
        return verification_code=='123456'
    def get_settings(self):return SESSION

class GuidedLoginTests(unittest.TestCase):
    def wait(self,login,phase):
        deadline=time.monotonic()+2
        while login.phase!=phase and time.monotonic()<deadline:time.sleep(.01)
        self.assertEqual(login.phase,phase)
    def test_two_factor_explicit_login_session_export_and_password_discard(self):
        client=FakeClient();login=Login(lambda:client)
        login.start({'username':'operatorfixture','password':'synthetic-password','consent':True});self.wait(login,'two-factor-required')
        self.assertNotIn('synthetic-password',json.dumps(login.status()))
        with self.assertRaises(ValueError):login.code({'login_id':'wrong','code':'123456'})
        login.code({'login_id':login.id,'code':'123456'});login.worker.join(2);self.wait(login,'connected')
        exported=login.export();self.assertNotIn('password',exported['session']);self.assertEqual(client.password,'')
        self.assertEqual(len(client.calls),2);self.assertTrue(client.public.close.called)
    def test_cancel_and_bad_credentials_never_export_a_session(self):
        login=Login(FakeClient)
        with self.assertRaises(ValueError):login.start({'username':'operatorfixture','password':'secret','consent':False})
        login.start({'username':'operatorfixture','password':'secret','consent':True});self.wait(login,'two-factor-required');login.cancel();login.worker.join(2)
        with self.assertRaises(ValueError):login.export()
        self.assertEqual(login.phase,'cancelled')
    def test_readonly_restore_never_calls_login_and_reconnect_blocks_auto_auth(self):
        client=FakeClient();client.login=MagicMock()
        readonly=locked_client(SESSION,lambda:client);self.assertNotIn('password',readonly.settings)
        with self.assertRaises(ReconnectRequired):readonly.login('anything','anything')
        with self.assertRaises(ReconnectRequired):readonly.challenge_resolve()
        with self.assertRaises(ReconnectRequired):readonly.login_legacy('anything','anything')
        client=FakeClient();client.private_request=MagicMock(return_value={'user':{}});readonly=locked_client(SESSION,lambda:client)
        self.assertEqual(readonly.private_request('users/publicfixture/usernameinfo/'),{'user':{}})
        with self.assertRaises(ReconnectRequired):readonly.private_request('direct_v2/threads/broadcast/text/')
        login=Login();login.restore({'username':'operatorfixture','session':SESSION});login.reconnect()
        with self.assertRaises(ValueError):login.export()
    def test_invalid_session_rejected_and_only_auth_settings_are_retained(self):
        with self.assertRaises(ValueError):clean_session({'cookies':{}})
        clean=clean_session({**SESSION,'proxy':'https://elsewhere.example','api_base':'https://elsewhere.example'})
        self.assertNotIn('proxy',clean);self.assertNotIn('api_base',clean)
    def test_connector_records_expiry_before_another_target_request(self):
        from research_connectors import ResearchConnectors,ConnectorUnavailable
        client=ResearchConnectors();client.configure({'osintgram_enabled':True});client.managed_manager=MagicMock();client.managed_vault=MagicMock();client.managed_manager.ensure.return_value=('synthetic-local-key',12345)
        with patch('research_connectors.read_json',return_value={'repository':'https://github.com/Datalux/Osintgram','needs_reconnect':True}) as request:
            with self.assertRaises(ConnectorUnavailable):client.osintgram('publicfixture','run',['get_user_info'])
            self.assertEqual(request.call_count,1);self.assertTrue(request.call_args.args[0].endswith('/api/about'));client.managed_vault.invalidate_instagram.assert_called_once()
    def test_expiry_flag_survives_wrapped_error_and_blocks_restoration(self):
        class LoginRequired(Exception):pass
        login=Login();login.restore({'username':'operatorfixture','session':SESSION})
        client=FakeClient();client.private_request=MagicMock(side_effect=LoginRequired('Expired'))
        readonly=locked_client(SESSION,lambda:client,on_reconnect=login.reconnect)
        # Upstream adapters can catch this exception and return an error body.
        try:readonly.private_request('users/publicfixture/usernameinfo/')
        except LoginRequired:pass
        self.assertEqual(login.phase,'reconnect-required');self.assertIsNone(login.session)
        restored=Login();restored.restore({'username':'operatorfixture','session':SESSION,'needs_reconnect':True})
        self.assertEqual(restored.phase,'reconnect-required')
        with self.assertRaises(ValueError):restored.export()
    def test_partial_public_result_retains_expiry_from_extra_command(self):
        from research_connectors import ResearchConnectors
        client=ResearchConnectors();client.configure({'osintgram_enabled':True});client.managed_manager=MagicMock();client.managed_vault=MagicMock();client.managed_manager.ensure.return_value=('synthetic-local-key',12345)
        responses=[{'repository':'https://github.com/Datalux/Osintgram'},{'target':'publicfixture','api_calls_total':1,'tool_calls':[{'name':'get_user_info','result':{'username':'publicfixture','is_private':False,'full_name':'Example Person'}}]},{'target':'publicfixture','api_calls_total':1,'tool_calls':[{'name':'get_captions','is_error':True}],'needs_reconnect':True}]
        with patch('research_connectors.read_json',side_effect=responses):result=client.osintgram('publicfixture','run',['get_user_info','get_captions'])
        self.assertEqual(result['results'][0]['status'],'ok');self.assertEqual(result['results'][1]['status'],'error');client.managed_vault.invalidate_instagram.assert_called_once()
    @unittest.skipUnless(os.name=='nt','Windows DPAPI')
    def test_vault_separates_search_keys_and_instagram_and_survives_reopen(self):
        with tempfile.TemporaryDirectory() as temp:
            vault=Vault(temp);vault.save('synthetic-hiker-key');vault.save_search('serper','synthetic-search-key');vault.save_instagram('operatorfixture',clean_session(SESSION))
            self.assertEqual(Vault(temp).osintgram()['backend'],'instagrapi');self.assertNotIn('search_keys',vault.osintgram())
            raw=vault.path.read_bytes()
            for secret in ['synthetic-session-secret','synthetic-hiker-key','synthetic-search-key']:self.assertNotIn(secret.encode(),raw)
            vault.forget_osintgram();self.assertFalse(vault.status()['saved']);self.assertEqual(vault.search_key('serper'),'synthetic-search-key')
    @unittest.skipUnless(os.name=='nt','Windows DPAPI')
    def test_persisted_expiry_requires_explicit_new_session(self):
        with tempfile.TemporaryDirectory() as temp:
            vault=Vault(temp);vault.save_instagram('operatorfixture',clean_session(SESSION));vault.invalidate_instagram()
            self.assertTrue(Vault(temp).osintgram()['needs_reconnect']);self.assertFalse(vault.status()['saved'])
            vault.save_instagram('operatorfixture',clean_session(SESSION));self.assertTrue(vault.status()['saved']);self.assertFalse(vault.status()['instagram_needs_reconnect'])
    @unittest.skipUnless(os.name=='nt','Windows DPAPI')
    def test_main_facade_saves_session_but_returns_only_public_status(self):
        with tempfile.TemporaryDirectory() as temp:
            automation=MagicMock();automation.vault=Vault(temp);automation.choices={};automation.manager.entries={'osintgram':{'key':'synthetic-local-key','port':12345,'process':MagicMock()}}
            automation.manager.entries['osintgram']['process'].poll.return_value=None
            state={'phase':'connected','connected':True,'busy':False,'login_id':'fixture','username':'operatorfixture','message':'Connected'}
            automation.manager.request.side_effect=lambda kind,path,*a:state if path=='/api/auth/status' else {'username':'operatorfixture','session':clean_session(SESSION),'login_id':'fixture'}
            facade=InstagramLogin(automation);result=facade.status();facade.status()
            self.assertNotIn('synthetic-session-secret',json.dumps(result));self.assertNotIn('session',result)
            self.assertEqual(automation.vault.osintgram()['session']['cookies']['sessionid'],'synthetic-session-secret')
            self.assertEqual(sum(c.args[1]=='/api/auth/session' for c in automation.manager.request.call_args_list),1)
