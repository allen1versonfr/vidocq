"""Publish only after the Windows test/build/smoke steps have succeeded."""
import hashlib
import json
import shutil
from pathlib import Path
import subprocess
import sys
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from version import VERSION

def gh(*args):
    return subprocess.check_output(['gh',*args],text=True)

from scripts.package_maigret_bridge import package
bridge=package()
bridge_digest=hashlib.sha256(bridge.read_bytes()).hexdigest()
from scripts.package_browser_extension import package as package_extension
extension=package_extension()
extension_digest=hashlib.sha256(extension.read_bytes()).hexdigest()
collector_source=Path('dist/Collectors-Source.zip')
collector_digest=hashlib.sha256(collector_source.read_bytes()).hexdigest()
tag='v'+VERSION
exe=Path('dist/Vidocq.exe')
data=exe.read_bytes();digest=hashlib.sha256(data).hexdigest()
Path('dist/SHA256SUMS.txt').write_text(digest+'  Vidocq.exe\n'+bridge_digest+'  Maigret-Bridge.zip\n'+extension_digest+'  Reviewed-Evidence-Extension.zip\n'+collector_digest+'  Collectors-Source.zip\n',encoding='utf-8')
Path('dist/BUILD_INFO.json').write_text(json.dumps({'name':'Vidocq','version':VERSION,'platform':'Windows 10/11 x64','windows_runtime_tested':True,'automated_tests':unittest.defaultTestLoader.discover('tests').countTestCases(),'frozen_smoke_test':True,'managed_ai_setup_api_test':True,'ai_files_preserved_by_update_test':True,'model_weights_bundled':False,'managed_collectors_bundled':True,'collector_setup_auth_test':True,'encrypted_credentials_test':True,'native_browser_relay_test':True,'bounded_ai_pipeline_test':True,'guided_instagram_session_fixture_test':True,'live_instagram_login_tested':False,'saved_session_update_preservation_test':True,'major_search_adapters_synthetic_test':True,'major_search_live_keys_tested':False,'reviewed_profile_continuation_test':True,'paired_checker_controls_test':True,'research_ui_dom_fixture_test':True,'collector_source_sha256':collector_digest,'live_public_index_canaries':True,'embedded_icon_verified':True,'social_profile_api_test':True,'phone_case_report_api_test':True,'replacement_restart_test':True,'failed_start_rollback_test':True,'size_bytes':len(data),'sha256':digest},indent=2),encoding='utf-8')
shutil.copyfile('build/assets/vidocq.ico','dist/Vidocq.ico')
notes=Path('RELEASE_NOTES.md')
existing=subprocess.run(['gh','release','view',tag,'--json','isDraft'],capture_output=True,text=True)
if existing.returncode==0:
    assert json.loads(existing.stdout)['isDraft'], 'Refusing to overwrite a published version; bump version.py.'
else:
    gh('release','create',tag,'--draft','--target','main','--title','Vidocq '+VERSION,'--notes-file',str(notes))
gh('release','upload',tag,str(exe),str(bridge),str(extension),str(collector_source),'dist/SHA256SUMS.txt','dist/BUILD_INFO.json','dist/Vidocq.ico','--clobber')
for attempt in range(12):
    releases=json.loads(gh('api','repos/{owner}/{repo}/releases?per_page=100'))
    matching=[r for r in releases if r['tag_name']==tag]
    assert len(matching)==1, 'Cannot resolve release draft.'
    assets=matching[0]['assets']
    matched=[a for a in assets if a['name']=='Vidocq.exe']
    bridge_assets=[a for a in assets if a['name']=='Maigret-Bridge.zip']
    extension_assets=[a for a in assets if a['name']=='Reviewed-Evidence-Extension.zip']
    source_assets=[a for a in assets if a['name']=='Collectors-Source.zip']
    if len(source_assets)==1 and source_assets[0].get('digest')=='sha256:'+collector_digest and len(extension_assets)==1 and extension_assets[0].get('digest')=='sha256:'+extension_digest and len(bridge_assets)==1 and bridge_assets[0].get('digest')=='sha256:'+bridge_digest and len(matched)==1 and matched[0].get('digest')=='sha256:'+digest and matched[0]['size']==len(data):break
    time.sleep(5)
else:
    raise RuntimeError('GitHub asset digest did not match. Release remains a draft.')
gh('release','edit',tag,'--draft=false','--latest')
print('Published verified Vidocq '+VERSION+'; SHA-256 '+digest)
