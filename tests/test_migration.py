import sqlite3,tempfile,unittest
from pathlib import Path
import app
class MigrationTests(unittest.TestCase):
 def make_database(self,root,name,value):
  path=root/name;path.mkdir(parents=True,exist_ok=True)
  with sqlite3.connect(path/'workspace.sqlite3') as c:
   c.execute('CREATE TABLE saved (value TEXT)');c.execute('INSERT INTO saved VALUES (?)',(value,))
 def value(self,path):
  with sqlite3.connect(path/'workspace.sqlite3') as c:return c.execute('SELECT value FROM saved').fetchone()[0]
 def test_recent_notebook_copied_original_preserved(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);self.make_database(root,'AllSeeingEyes','recent');app.migrate_legacy_data(root/'Vidocq',root);self.assertEqual(self.value(root/'Vidocq'),'recent');self.assertEqual(self.value(root/'AllSeeingEyes'),'recent')
 def test_older_notebook_supported(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);self.make_database(root,'OSINTDesk','older');app.migrate_legacy_data(root/'Vidocq',root);self.assertEqual(self.value(root/'Vidocq'),'older')
 def test_existing_notebook_never_overwritten(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);self.make_database(root,'AllSeeingEyes','old');self.make_database(root,'Vidocq','current');app.migrate_legacy_data(root/'Vidocq',root);self.assertEqual(self.value(root/'Vidocq'),'current')
