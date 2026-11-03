"""Reproducible Vidocq vector mark and multi-resolution Windows icon."""
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
SVG='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><rect x="8" y="8" width="240" height="240" rx="55" fill="#172638"/><path d="M155 155L200 201" stroke="#d4b170" stroke-width="26" stroke-linecap="round"/><circle cx="112" cy="110" r="59" fill="#172638" stroke="#d4b170" stroke-width="16"/><path d="M83 91L112 133L141 91" fill="none" stroke="#d4b170" stroke-width="15" stroke-linecap="round" stroke-linejoin="round"/></svg>'''

def build(output=None):
    output=Path(output or ROOT/'build/assets');output.mkdir(parents=True,exist_ok=True)
    # Draw at 4x, then downsample each ICO frame for smooth small Windows sizes.
    scale=4;im=Image.new('RGBA',(1024,1024));d=ImageDraw.Draw(im)
    box=lambda b:tuple(int(v*scale) for v in b)
    navy='#172638';gold='#d4b170'
    d.rounded_rectangle(box((8,8,248,248)),radius=55*scale,fill=navy)
    d.line(box((155,155,200,201)),fill=gold,width=26*scale)
    for x,y in ((155,155),(200,201)):d.ellipse(box((x-13,y-13,x+13,y+13)),fill=gold)
    d.ellipse(box((45,43,179,177)),fill=gold);d.ellipse(box((61,59,163,161)),fill=navy)
    d.line([(83*scale,91*scale),(112*scale,133*scale),(141*scale,91*scale)],fill=gold,width=15*scale,joint='curve')
    for x,y in ((83,91),(112,133),(141,91)):d.ellipse(box((x-7.5,y-7.5,x+7.5,y+7.5)),fill=gold)
    im.resize((256,256),Image.Resampling.LANCZOS).save(output/'vidocq.ico',sizes=[(n,n) for n in (16,20,24,32,40,48,64,128,256)])
    im.resize((512,512),Image.Resampling.LANCZOS).save(output/'vidocq.png')
    return output/'vidocq.ico'
if __name__=='__main__':
    (ROOT/'ui/vidocq-icon.svg').write_text(SVG,encoding='utf-8')
    print(build())
