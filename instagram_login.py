"""Main-app facade. Session export stays on authenticated local IPC, never UI APIs."""
import threading

class InstagramLogin:
    def __init__(self,automation):self.automation=automation;self.saved_login='';self.lock=threading.RLock();self.last={'phase':'idle','busy':False,'connected':False,'message':'Connect your own operator account; this uses an Instagram session, not OAuth.'}
    def status(self):
        with self.lock:
            entry=self.automation.manager.entries.get('osintgram')
            if not entry or entry['process'].poll() is not None:return {**self.last,'busy':False,'connected':False,'saved':self.automation.vault.status()['instagram_saved']}
            state=self.automation.manager.request('osintgram','/api/auth/status')
            if state.get('needs_reconnect') and not self.automation.vault.status().get('instagram_needs_reconnect'):self.automation.vault.invalidate_instagram()
            if state['connected'] and state['login_id']!=self.saved_login:
                credentials=self.automation.manager.request('osintgram','/api/auth/session',{})
                self.automation.vault.save_instagram(credentials['username'],credentials['session']);self.saved_login=state['login_id']
                self.automation.choices['osintgram']=True;self.automation.save()
                connectors=self.automation.connectors;connectors.port=entry['port'];connectors.managed_key=entry['key'];connectors.managed_manager=self.automation.manager;connectors.managed_vault=self.automation.vault;connectors.osintgram_enabled=True
            self.last=state
            return {**state,'saved':self.automation.vault.status()['instagram_saved']}
    def action(self,action,p):
        with self.lock:
            if self.automation.status()['busy']:raise ValueError('Wait for tool setup to finish before connecting Instagram.')
            if action=='start':
                if p.get('consent') is not True:raise ValueError('Approve signing in to your own operator account first.')
                self.automation.connectors.osintgram_enabled=False;self.automation.manager.stop('osintgram')
                self.automation.manager.ensure('osintgram',{'backend':'instagrapi'});self.saved_login=''
                self.automation.manager.request('osintgram','/api/auth/start',p)
            elif action=='code':self.automation.manager.request('osintgram','/api/auth/code',p)
            elif action=='cancel':
                self.automation.manager.stop('osintgram');self.last={'phase':'cancelled','busy':False,'connected':False,'message':'Login/service stopped. Any previously saved encrypted session is preserved; use Forget to remove it.'};return self.status()
            elif action=='forget':
                self.automation.manager.stop('osintgram');self.automation.connectors.osintgram_enabled=False
                self.automation.vault.forget_instagram();self.last={'phase':'idle','busy':False,'connected':False,'message':'Operator session forgotten locally. No remote account action was performed.'};return self.status()
            else:raise ValueError('Unsupported Instagram login action.')
            return self.status()
