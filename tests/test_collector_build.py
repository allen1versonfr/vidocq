import io,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.build_collectors import freeze

class BuildIsolationTests(unittest.TestCase):
    def test_parallel_builds_use_distinct_caches_and_failures_surface_the_log(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            with patch('scripts.build_collectors.run') as run:
                for kind in ('harvester','photon','osintgram'):freeze(['synthetic-build'],kind,work)
                caches=[c.kwargs['env']['PYINSTALLER_CONFIG_DIR'] for c in run.call_args_list]
                self.assertEqual(len(set(caches)),3)
            def failed(command,**kwargs):
                kwargs['stdout'].write('Synthetic collector build error.');kwargs['stdout'].flush()
                raise subprocess.CalledProcessError(1,command)
            output=io.StringIO()
            with patch('scripts.build_collectors.run',side_effect=failed),patch('sys.stderr',output):
                with self.assertRaises(subprocess.CalledProcessError):freeze(['synthetic-build'],'photon',work)
            self.assertIn('Synthetic collector build error.',output.getvalue())
