"""Package the user-installed Chrome/Firefox capture helper (no bundled upstream code)."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED

def package():
    root=Path(__file__).resolve().parents[1];output=root/'dist'/'Reviewed-Evidence-Extension.zip';output.parent.mkdir(exist_ok=True)
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        for name in ('manifest.json','popup.html','popup.js'):archive.write(root/'browser-extension'/name,name)
        archive.write(root/'docs/DISCOVERY_WORKBENCH.md','README.md')
    return output

if __name__=='__main__':print(package())
