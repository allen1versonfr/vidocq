"""Real Windows frozen executable and helper replacement/rollback checks."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

exe = Path('dist/Vidocq.exe').resolve()
env = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT='1')
with tempfile.TemporaryDirectory(prefix='Vidocq-ci-') as temp:
    root = Path(temp)
    env['VIDOCQ_DATA'] = str(root/'data')
    smoke = root/'smoke.json'
    subprocess.run([str(exe), '--smoke-test', str(smoke)], env=env, check=True, timeout=120)
    assert json.loads(smoke.read_text()) == {'ok':True, 'version':'2.3.0'}
    for scenario in ('success', 'rollback'):
        folder=root/scenario;folder.mkdir()
        target=folder/'Vidocq.exe';shutil.copyfile(exe,target)
        staged=folder/'candidate.exe'
        if scenario=='success':shutil.copyfile(exe,staged)
        else:staged.write_bytes(b'MZ'+b'not-a-real-executable'*100)
        ready=folder/'ready';result=folder/'result.json';check=folder/'child.json'
        data=staged.read_bytes()
        job={'target':str(target),'staged':str(staged),'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),
             'parent_pid':0,'ready':str(ready),'result':str(result),'version':'2.3.0',
             'launch_args':['--smoke-test',str(check)]}
        jobfile=folder/'job.json';jobfile.write_text(json.dumps(job))
        helper=folder/'helper.exe';shutil.copyfile(exe,helper)
        process=subprocess.run([str(helper),'--apply-update',str(jobfile)],env=env,timeout=180)
        assert process.returncode==(0 if scenario=='success' else 1), (scenario,process.returncode)
        assert json.loads(result.read_text())['status']==('updated' if scenario=='success' else 'failed')
        assert hashlib.sha256(target.read_bytes()).digest()==hashlib.sha256(exe.read_bytes()).digest()
        deadline=time.monotonic()+90
        while not check.exists() and time.monotonic()<deadline:time.sleep(.5)
        assert check.exists(),f'{scenario}: restarted executable did not complete smoke test'
        # The child writes its marker just before exit; allow Windows to release the file.
        time.sleep(2)
    print('Frozen imports/UI/database, executable replacement/restart, and failed-launch rollback passed.')
