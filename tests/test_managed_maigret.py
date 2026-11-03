import json
import unittest
from unittest.mock import patch,MagicMock

from additional_collectors import AdditionalCollectors
from managed_maigret import ManagedMaigret

class ManagedMaigretTests(unittest.TestCase):
    def test_setup_is_authenticated_idempotent_and_stops_when_disabled(self):
        client=AdditionalCollectors()
        try:
            first=client.setup_maigret();process=client.manager.process;key=client.manager.key
            self.assertTrue(first['managed_maigret']['running']);self.assertTrue(first['maigret']['enabled'])
            self.assertNotIn(key,json.dumps(first));self.assertEqual(first['maigret']['session_requests'],0)
            client.setup_maigret();self.assertIs(client.manager.process,process)
            client.configure({'maigret_enabled':False})
            self.assertIsNotNone(process.poll());self.assertFalse(client.status()['managed_maigret']['running'])
        finally:
            if client.manager:client.manager.stop()

    def test_dead_process_can_be_replaced_without_leaking_old_token(self):
        manager=ManagedMaigret()
        try:
            old_key,_=manager.ensure();old=manager.process
            old.terminate();old.wait(timeout=10)
            new_key,_=manager.ensure()
            self.assertNotEqual(old_key,new_key);self.assertIsNot(manager.process,old)
            self.assertEqual(manager.status()['state'],'ready')
        finally:manager.stop()

    def test_disabled_managed_service_is_restarted_for_reenabled_lookup(self):
        client=AdditionalCollectors()
        try:
            client.setup_maigret();client.configure({'maigret_enabled':False})
            client.configure({'maigret_enabled':True})
            self.assertTrue(client.managed)
            # The restarted real child receives an empty site response through a
            # mocked search transport, so no public account is queried.
            from additional_collectors import transport as real_transport
            def local_transport(url,*args,**kwargs):
                if url.endswith('/api/search'):
                    return {'username':'synthetic','results':[{'site':'GitHub','status':'Available'}]}
                return real_transport(url,*args,**kwargs)
            with patch('additional_collectors.transport',side_effect=local_transport):
                result=client.maigret('synthetic','test',['GitHub'])
            self.assertTrue(client.manager.status()['running']);self.assertEqual(result['results'][0]['status'],'empty')
        finally:
            if client.manager:client.manager.stop()

    def test_companion_stops_after_forced_parent_exit(self):
        import subprocess,sys,tempfile,time,socket
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            marker=Path(folder)/'ready.json'
            code="from managed_maigret import ManagedMaigret; import json,time; from pathlib import Path; m=ManagedMaigret(); m.ensure(); Path("+repr(str(marker))+").write_text(json.dumps({'port':m.port,'pid':m.process.pid})); time.sleep(120)"
            parent=subprocess.Popen([sys.executable,'-c',code],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            child=None
            try:
                deadline=time.monotonic()+75
                while not marker.exists() and parent.poll() is None and time.monotonic()<deadline:time.sleep(.1)
                self.assertTrue(marker.exists(),'Managed service parent did not become ready')
                child=json.loads(marker.read_text());parent.terminate();parent.wait(timeout=10)
                deadline=time.monotonic()+10
                while time.monotonic()<deadline:
                    with socket.socket() as connection:
                        connection.settimeout(.5)
                        if connection.connect_ex(('127.0.0.1',child['port']))!=0:break
                    time.sleep(.1)
                else:self.fail('Orphan companion did not stop')
            finally:
                if parent.poll() is None:parent.terminate();parent.wait(timeout=10)
                if child:
                    import psutil
                    try:psutil.Process(child['pid']).terminate()
                    except psutil.NoSuchProcess:pass

    def test_start_failure_cleans_state(self):
        manager=ManagedMaigret();process=MagicMock();process.poll.return_value=1
        with patch('managed_maigret.subprocess.Popen',return_value=process):
            with self.assertRaisesRegex(ValueError,'could not start'):manager.ensure()
        self.assertEqual(manager.key,'');self.assertIsNone(manager.process);self.assertIsNone(manager.port)

    def test_switching_to_manual_service_stops_managed_child(self):
        client=AdditionalCollectors()
        try:
            client.setup_maigret();process=client.manager.process
            client.configure({'maigret_key':'manual-companion-key-123','maigret_port':8001})
            self.assertIsNotNone(process.poll());self.assertTrue(client.enabled['maigret'])
            self.assertEqual(client.keys['maigret'],'manual-companion-key-123')
        finally:
            if client.manager:client.manager.stop()
