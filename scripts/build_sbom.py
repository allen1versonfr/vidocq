"""Inventory the main Python build environment; excludes private workspaces."""
from datetime import datetime,timezone
from importlib import metadata
from pathlib import Path
import hashlib,json,re,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from version import VERSION

def generate(output=Path('dist/Main-Python-SBOM.json')):
    root=Path(__file__).resolve().parents[1];components=[]
    for distribution in metadata.distributions():
        name=distribution.metadata.get('Name')
        if not name:continue
        normalized=re.sub(r'[-_.]+','-',name).lower()
        components.append({'type':'library','name':normalized,'version':distribution.version,'purl':'pkg:pypi/'+normalized+'@'+distribution.version})
    data={'bomFormat':'CycloneDX','specVersion':'1.5','version':1,'metadata':{'timestamp':datetime.now(timezone.utc).isoformat(),'component':{'type':'application','name':'Vidocq','version':VERSION},'properties':[{'name':'vidocq:scope','value':'Main Python build environment only; native libraries, model assets and isolated collectors have separate manifests/locks.'},{'name':'vidocq:lock_sha256','value':hashlib.sha256((root/'requirements-lock.txt').read_bytes()).hexdigest()}]},'components':sorted(components,key=lambda c:(c['name'],c['version']))}
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(data,indent=2),encoding='utf-8');return output
if __name__=='__main__':print(generate())
