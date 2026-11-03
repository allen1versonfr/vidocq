"""Publish only after the Windows test/build/smoke steps have succeeded."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from version import VERSION

def gh(*args):
    return subprocess.check_output(['gh',*args],text=True)

tag='v'+VERSION
exe=Path('dist/Vidocq.exe')
data=exe.read_bytes();digest=hashlib.sha256(data).hexdigest()
Path('dist/SHA256SUMS.txt').write_text(digest+'  Vidocq.exe\n',encoding='utf-8')
Path('dist/BUILD_INFO.json').write_text(json.dumps({'name':'Vidocq','version':VERSION,'platform':'Windows 10/11 x64','windows_runtime_tested':True,'automated_tests':unittest.defaultTestLoader.discover('tests').countTestCases(),'frozen_smoke_test':True,'live_public_index_canaries':True,'phone_case_report_api_test':True,'replacement_restart_test':True,'failed_start_rollback_test':True,'size_bytes':len(data),'sha256':digest},indent=2),encoding='utf-8')
notes=Path('RELEASE_NOTES.md')
existing=subprocess.run(['gh','release','view',tag,'--json','isDraft'],capture_output=True,text=True)
if existing.returncode==0:
    assert json.loads(existing.stdout)['isDraft'], 'Refusing to overwrite a published version; bump version.py.'
else:
    gh('release','create',tag,'--draft','--target','main','--title','Vidocq '+VERSION,'--notes-file',str(notes))
gh('release','upload',tag,str(exe),'dist/SHA256SUMS.txt','dist/BUILD_INFO.json','--clobber')
for attempt in range(12):
    releases=json.loads(gh('api','repos/{owner}/{repo}/releases?per_page=100'))
    matching=[r for r in releases if r['tag_name']==tag]
    assert len(matching)==1, 'Cannot resolve release draft.'
    assets=matching[0]['assets']
    matched=[a for a in assets if a['name']=='Vidocq.exe']
    if len(matched)==1 and matched[0].get('digest')=='sha256:'+digest and matched[0]['size']==len(data):break
    time.sleep(5)
else:
    raise RuntimeError('GitHub asset digest did not match. Release remains a draft.')
gh('release','edit',tag,'--draft=false','--latest')
print('Published verified Vidocq '+VERSION+'; SHA-256 '+digest)
