from pathlib import Path
import sys,json,hashlib
from PIL import Image,ImageDraw
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/'skill-snapshot/scripts'))
from tile_tools import floor_anchor,clean_alpha

def write(path,data):path.write_text(json.dumps(data,indent=2)+'\n')
source=Image.open(OUT/'source-01.png').convert('RGBA')
guide=Image.open(OUT/'guide.png').convert('RGBA')
layout=json.loads((OUT/'guide.json').read_text())
sx=source.width/layout['size'][0];sy=source.height/layout['size'][1]
cleaned,cleanup=clean_alpha(source,32)
measurements=[]
for cell in layout['cells']:
    rect=tuple(round(v*(sx if i%2==0 else sy)) for i,v in enumerate(cell['rect']))
    try:
        observation=floor_anchor(cleaned.crop(rect))
        measurements.append({'index':cell['index'],'direction':cell['direction'],'sourceRect':list(rect),'floorDetectorObservation':observation,'squareAspectAcceptedByProcessor':.95<=observation['aspect']<=1.05})
    except Exception as exc:
        measurements.append({'index':cell['index'],'direction':cell['direction'],'sourceRect':list(rect),'error':str(exc)})
write(OUT/'floor-diagnostics.json',{'method':'Frozen floor_anchor observations on known registered panels after clean_alpha(min_alpha=32); diagnostics only, no normalization or geometry repair','sourceDimensions':list(source.size),'guideScale':[sx,sy],'alphaCleanup':cleanup,'panels':measurements})
for name,color in [('light','#f4f6ef'),('dark','#18222e')]:
    for role,img in [('source',source),('guide',guide)]:
        view=Image.new('RGBA',img.size,color);view.alpha_composite(img)
        view.convert('RGB').save(OUT/f'previews/{role}-{name}-native.png')
        view.resize((img.width*2,img.height*2),Image.Resampling.NEAREST).convert('RGB').save(OUT/f'previews/{role}-{name}-2x.png')
# Source geometry overlay is a diagnostic, separate from unmodified and background-only previews.
overlay=Image.new('RGBA',source.size,(0,0,0,0));draw=ImageDraw.Draw(overlay)
for cell in layout['cells']:
    l,t,r,b=[round(v*(sx if i%2==0 else sy)) for i,v in enumerate(cell['rect'])]
    draw.rectangle([l,t,r-1,b-1],outline='#b82e74',width=2)
    ax=l+96*sx;ay=t+248*sy
    draw.line([ax-8,ay,ax+8,ay],fill='#b82e74',width=2);draw.line([ax,ay-8,ax,ay+8],fill='#b82e74',width=2)
    fl=l+32*sx;ft=t+184*sy;fr=l+160*sx;fb=t+312*sy
    draw.rectangle([round(fl),round(ft),round(fr)-1,round(fb)-1],outline='#e3a221',width=2)
view=Image.new('RGBA',source.size,'#f4f6ef');view.alpha_composite(source);view.alpha_composite(overlay)
view.convert('RGB').save(OUT/'previews/source-authored-registration.png')
previews=[p.relative_to(OUT).as_posix() for p in sorted((OUT/'previews').glob('*.png'))]
write(OUT/'previews/index.json',{'images':previews,'nativeSourceSize':list(source.size),'nativeGuideSize':list(guide.size),'twoXResampling':'nearest neighbor','runtimePlacementAvailable':False,'reason':'Deterministic extraction failed; no generated sprite placement can be shown. Authored roots in the registration overlay are intended constraints, not fitted character contact points.'})
result=json.loads((OUT/'result.json').read_text());result['previews']=previews;result['floorDiagnosticEvidence']='floor-diagnostics.json';write(OUT/'result.json',result)
recipe=json.loads((OUT/'generation-01.json').read_text());recipe['toolResponseRecord']='tool-response-01.json';write(OUT/'generation-01.json',recipe)
print(json.dumps({'floorDiagnostics':measurements,'previews':previews},indent=2))
