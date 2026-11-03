"""Package independently authored companion files without upstream code."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

def package():
    root=Path(__file__).resolve().parents[1]
    output=root/'dist'/'Maigret-Bridge.zip'
    output.parent.mkdir(exist_ok=True)
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        for name in ('scripts/maigret_bridge.py','collector_policy.py','docs/ADDITIONAL_COLLECTORS.md','LICENSE'):
            if (root/name).exists():archive.write(root/name,name)
        archive.writestr('requirements-maigret.txt','maigret==0.6.6\n')
        archive.writestr('README.txt','Setup: docs/ADDITIONAL_COLLECTORS.md\nSeparate Python 3.12 and Maigret installation required.\n')
    return output

if __name__=='__main__':print(package())
