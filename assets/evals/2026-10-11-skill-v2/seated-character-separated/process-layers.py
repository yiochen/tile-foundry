#!/usr/bin/env python3
from pathlib import Path
import sys,json,traceback
from PIL import Image
D=Path(__file__).resolve().parent
S=D.parent/'skill-snapshot/scripts';sys.path.insert(0,str(S))
from tile_tools import load_rgba,process_floor_object,floor_anchor,write_json
(D/'processing').mkdir(exist_ok=True);(D/'sprites').mkdir(exist_ok=True)
records=[]
for name in ('stool','character'):
 image=load_rgba(D/f'source-{name}.png')
 rec={'source':f'source-{name}.png','sourceSize':list(image.size),'alphaExtrema':list(image.getchannel('A').getextrema())}
 try:
  rec['floorObservation']=floor_anchor(image)
  output,info=process_floor_object(image,[123,209,75])
  output.save(D/'sprites'/f'{name}.png')
  info.update(image=f'../sprites/{name}.png',id=name)
  write_json(D/'processing'/f'{name}.json',info)
  rec.update(outcome='processed',processing=info)
 except Exception as e:
  rec.update(outcome='processing-failed',error=str(e),traceback=traceback.format_exc())
  write_json(D/'processing'/f'{name}-failure.json',rec)
 records.append(rec)
write_json(D/'processing/diagnostic.json',{'version':2,'records':records,'repairPolicy':'No alpha fitting, geometric warp, source redraw or generation retry.'})
print(json.dumps(records,indent=2))
raise SystemExit(1 if any(r['outcome']=='processing-failed' for r in records) else 0)
