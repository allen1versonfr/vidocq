"""Build isolated pinned Windows companions, with reproducible source/notices assets."""
import argparse,concurrent.futures,hashlib,json,os,shutil,subprocess,sys,urllib.request
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]
SOURCES={
 'harvester':('laramies/theHarvester','6790b147f52309e4eee22ed941db1d285ab2ec23','9bbc445917cda595b5173d1699da6b0b3eb30ecafb8358bcec202a8a34fad076'),
 'osintgram':('Datalux/Osintgram','a560498be79a3bf40d7f3b203ad174661b8e81e7','7d7ff80e16b2a1a923882a493e25a43caa5e0803eec0deb449b8ae28ceaeb2cb'),
 'photon':('s0md3v/Photon','c8d2566841d69a268b244609921143d84b72b0c6','440e730b243e43381f0972bccb7e6959bbfe5d0c713c271ed763ade9406272a8')}
EXTRAS=['pyinstaller==6.20.0','hikerapi==1.8.1','geopy==2.4.1','requests==2.32.5','tld==0.13.1','PySocks==1.7.1']

def run(command,**kwargs):subprocess.run([str(x) for x in command],check=True,cwd=ROOT,**kwargs)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--skip-sync',action='store_true');args=parser.parse_args()
 if sys.version_info[:2]!=(3,14):raise ValueError('Build companions with Python 3.14; the Vidocq app remains on 3.12.')
 work=ROOT/'.test-data';work.mkdir(exist_ok=True);out=ROOT/'build/assets/collectors';out.mkdir(parents=True,exist_ok=True)
 for kind,(repo,commit,expected) in SOURCES.items():
  archive=work/(kind+'-upstream.zip');source=work/(kind+'-source')
  if not archive.exists():urllib.request.urlretrieve('https://codeload.github.com/'+repo+'/zip/'+commit,archive)
  if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:raise ValueError('Pinned '+kind+' source checksum mismatch.')
  if not source.exists():
   source.mkdir()
   with ZipFile(archive) as z:
    for member in z.infolist():
     rel=Path(*Path(member.filename).parts[1:])
     if not rel.parts:continue
     target=(source/rel).resolve()
     if not target.is_relative_to(source.resolve()) or member.external_attr>>16&0o170000==0o120000:raise ValueError('Unsafe source archive.')
     if member.is_dir():target.mkdir(parents=True,exist_ok=True)
     else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(member))
 if not args.skip_sync:
  run([sys.executable,'-m','pip','install','uv==0.13.7'])
  env=dict(os.environ,UV_PROJECT_ENVIRONMENT=str(work/'harvester-env'))
  run([sys.executable,'-m','uv','sync','--frozen','--no-dev','--no-editable','--python',sys.executable,'--project',work/'harvester-source'],env=env)
  run([sys.executable,'-m','uv','pip','install','--python',work/'harvester-env/Scripts/python.exe',*EXTRAS])
 python=work/'harvester-env/Scripts/python.exe'
 def build(kind):
  options=[]
  if kind=='harvester':options=['--collect-all','theHarvester','--hidden-import','sqlalchemy.dialects.sqlite.aiosqlite','--collect-all','aiosqlite','--collect-all','greenlet']
  elif kind=='osintgram':options=['--paths',str(work/'osintgram-source'),'--collect-all','hikerapi','--collect-all','geopy']
  else:options=['--paths',str(work/'photon-source'),'--collect-all','core','--collect-all','plugins','--collect-all','tld','--add-data',str(work/'photon-source')+';photon']
  log=work/(kind+'-build.log')
  with log.open('w',encoding='utf-8') as stream:run([python,'-m','PyInstaller','--noconfirm','--clean','--onefile','--console','--name',kind,'--distpath',out,'--workpath',ROOT/'build/companion-work'/kind,'--specpath',ROOT/'build/companion-specs',*options,ROOT/'scripts'/(kind+'_companion.py')],stdout=stream,stderr=subprocess.STDOUT)
  exe=out/(kind+'.exe');return kind,{'sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'size':exe.stat().st_size,'commit':SOURCES[kind][1]}
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:manifest=dict(pool.map(build,SOURCES))
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 notices=[]
 for kind,(repo,commit,_) in SOURCES.items():
  license_file=work/(kind+'-source')/('LICENSE.md' if kind=='photon' else 'LICENSE')
  notices.append(kind+'\nhttps://github.com/'+repo+'/tree/'+commit+'\n\n'+license_file.read_text(encoding='utf-8'))
 (out/'LICENSES.txt').write_text('\n\n'.join(notices),encoding='utf-8')
 dist=ROOT/'dist';dist.mkdir(exist_ok=True)
 with ZipFile(dist/'Collectors-Source.zip','w',ZIP_DEFLATED) as z:
  for kind in SOURCES:z.write(work/(kind+'-upstream.zip'),kind+'-source.zip')
  for name in ['scripts/build_collectors.py','scripts/harvester_companion.py','scripts/osintgram_companion.py','scripts/photon_companion.py','scripts/collector_http.py','companion_scope.py','collector_policy.py','discovery_tools.py']:z.write(ROOT/name,name)
  z.writestr('BUILD.txt','Python 3.14 on Windows x64. Run python scripts/build_collectors.py. Each upstream ZIP is pinned and verified; theHarvester dependencies use its frozen uv.lock. Extra build/service pins: '+', '.join(EXTRAS)+'\nNo browser binaries are installed. Separate companion executables communicate over loopback IPC.\n')
 print(json.dumps({'built':manifest,'source_asset':'Collectors-Source.zip'}),flush=True)
if __name__=='__main__':main()
