from pathlib import Path
from PIL import Image
import json, shutil
out=Path('/Users/yiouchen/.codex/worktrees/1834/tile-foundry/assets/evals/2026-10-16-skill-r3/animated-waves')
p=out/'previews'; (p/'initial-canvas').mkdir()
for image in p.glob('repeat-*.png'):shutil.move(str(image),p/'initial-canvas'/image.name)
r=json.loads((out/'result.json').read_text()); frames=[Image.open(out/s['image']).convert('RGBA') for s in r['sprites']]
for phase in range(12):
 for offset in [False,True]:
  canvas=Image.new('RGBA',(496,624),'#18222e')
  for row in range(3):
   for col in range(3):
    i=(phase+col+row*3)%12 if offset else phase
    root=(120+col*128,272+row*128); s=r['sprites'][i]
    canvas.alpha_composite(frames[i],(round(root[0]-s['anchor'][0]),round(root[1]-s['anchor'][1])))
  name=f'repeat-{phase:02}'+('-offset' if offset else '')+'.png'
  canvas.save(p/name)
  canvas.resize((992,1248),Image.Resampling.NEAREST).save(p/(Path(name).stem+'-2x.png'))
(out/'preview-processing-notes.json').write_text(json.dumps({'initialPreviewCanvas':[432,464],'correction':'Enlarged review canvas to include every complete 192x320 stored frame at 128px pitch, with 24px outer margin. No art, anchor, source or scale changed. Earlier previews retained in previews/initial-canvas.','currentPreviewCanvas':[496,624]},indent=2)+'\n')
