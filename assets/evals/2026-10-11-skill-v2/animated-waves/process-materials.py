#!/usr/bin/env python3
"""Attempt the frozen authored-SVG material pipeline without alpha repair."""
from pathlib import Path
import sys,json,traceback
from PIL import Image
D=Path(__file__).resolve().parent
S=D.parent/'skill-snapshot/scripts';sys.path.insert(0,str(S))
from svg_tools import compose
source=Image.open(D/'source-material.png').convert('RGBA')
guide=json.loads((D/'guide.json').read_text())
(D/'processing').mkdir(exist_ok=True)
records=[];failed=[]
sx,sy=source.width/guide['size'][0],source.height/guide['size'][1]
if abs(sx/sy-1)>.01:
 failed.append('Generated canvas aspect differs from authored guide; no distorted sampling performed.')
else:
 for c in guide['cells']:
  rect=[round(v*(sx if j%2==0 else sy)) for j,v in enumerate(c['materialRect'])]
  sample=source.crop(rect);p=D/'processing'/f'material-{c["index"]:02}.png';sample.save(p)
  rec={'index':c['index'],'authoredMaterialRect':c['materialRect'],'actualSourceRect':rect,'sampleSize':list(sample.size),'alphaExtrema':list(sample.getchannel('A').getextrema()),'sampling':'Predetermined interior material window; sprite geometry comes solely from authored SVG faces'}
  try:
   # compose refuses any material alpha below 255; never coerce alpha.
   compose(D/'template',p,D/'sprites'/f'frame-{c["index"]:02}.png',strength=.7)
   rec['outcome']='composited'
  except Exception as e:
   rec['outcome']='processing-failed';rec['error']=str(e);failed.append(f'frame {c["index"]}: {e}')
  records.append(rec)
report={'version':2,'sourceSize':list(source.size),'guideSize':guide['size'],'sourceUniformScale':sx,'materialSamplingRecords':records,'failures':failed,'spritesCreated':len(list((D/'sprites').glob('*.png'))) if (D/'sprites').exists() else 0,'repairPolicy':'No alpha coercion, axis stretching, sample-window fitting, or generation retry.'}
(D/'processing/diagnostic.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(1 if failed else 0)
