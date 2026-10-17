"""Package complete Blender captures using the shared tilekit registration tools."""
import json
import hashlib
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from tilekit import Image, pack_atlas, alpha_bounds
sys.path.insert(0,str(ROOT/'skills/build-overlap-tiles/scripts'))
from extract_registered_sheet import extract

bundle=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'assets/blender/dancing-adventurer-v2'
meta=json.loads((bundle/'capture.json').read_text())
cols=6;rows=4;gutter=24;w=192;h=320
sheet=Image.new('RGBA',(cols*w+(cols+1)*gutter,rows*h+(rows+1)*gutter))
cells=[]
for i in range(24):
    path=bundle/f'capture/frame-{i:02d}.png'
    with Image.open(path) as image:
        image.load()
        assert image.size==(768,1280)
        assert not image.getchannel('A').crop((0,0,768,1)).getbbox()
        frame=image.resize((w,h),Image.Resampling.LANCZOS)
    x=gutter+(i%cols)*(w+gutter);y=gutter+(i//cols)*(h+gutter)
    sheet.paste(frame,(x,y))
    cells.append({'index':i,'rect':[x,y,x+w,y+h],'durationMs':1000/12})
sheet.save(bundle/'reskin-reference.png')
guide={'version':1,'kind':'rendered-3d-sheet','assetKind':'animation',
    'size':list(sheet.size),'frame':[w,h],'cellSize':128,'anchor':[96,248],
    'captureScale':1,'gutter':gutter,'columns':cols,'rows':rows,'cells':cells,
    'occupiedCells':[[0,0]],'elevationPx':0,'groundAnchorAlignment':'center',
    'projection':'character-orthographic','camera':meta['camera'],
    'captureProcessing':'Uniform whole-frame 4:1 LANCZOS from retained Cycles PNGs; no crop or pose fitting'}
(bundle/'guide.json').write_text(json.dumps(guide,indent=2)+'\n')
result=extract(bundle/'reskin-reference.png',bundle/'guide.json',bundle/'control',min_alpha=0)
items=[]
for entry in result['frames']:
    with Image.open(bundle/'control'/entry['image']) as frame:items.append((entry['id'],frame.copy(),entry))
atlas,atlas_meta=pack_atlas(items,columns=6,padding=4,extrusion=2,trim=False)
atlas.save(bundle/'control/atlas.png')
(bundle/'control/atlas.json').write_text(json.dumps(atlas_meta,indent=2)+'\n')
shutil.copy2(bundle/'capture/frame-00.png',bundle/'hero.png')
reference=ROOT/'assets/evals/2026-10-17-3d-creative-reskin-all/dancing-player/processed/frames/frame-00.png'
shutil.copy2(reference,bundle/'design-reference.png')
landmarks=json.loads((bundle/'landmarks.json').read_text())
max_foot_drift=max(abs(a-b) for row in landmarks for side in ['L','R']
                   for ar,br in zip(row['footMatrices'][side],landmarks[0]['footMatrices'][side]) for a,b in zip(ar,br))
assert max_foot_drift<1e-5, f'Planted foot transform moved: {max_foot_drift}'
checks={'frameCount':24,'fps':12,'footTransformMaxDelta':max_foot_drift,
    'rootPixelMaxDelta':max(abs(a-b) for row in landmarks for a,b in zip(row['root'],[96,248])),
    'panelBoundaryAlpha':result['panelIsolation']['panelBoundaryAlphaAfterThreshold'],
    'sourceCaptureScale':4,'perPoseFitting':False,'renderedAlphaPreserved':True,
    'designReference':{'path':'design-reference.png','role':'visual design target; not supplied to imagegen',
        'sha256':hashlib.sha256(reference.read_bytes()).hexdigest()}}
(bundle/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks,indent=2))
