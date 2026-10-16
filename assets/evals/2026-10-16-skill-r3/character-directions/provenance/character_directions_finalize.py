from pathlib import Path
import sys,json,hashlib,shutil
from PIL import Image,ImageDraw
ROOT=Path('/Users/yiouchen/.codex/worktrees/1834/tile-foundry')
OUT=ROOT/'assets/evals/2026-10-16-skill-r3/character-directions'
SKILL=ROOT/'assets/evals/2026-10-16-skill-r3/skill-snapshot'
sys.path.insert(0,str(SKILL/'scripts'))
from tile_tools import render_anchored_frames
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result=json.loads((OUT/'result.json').read_text())
frames=[Image.open(OUT/s['image']).convert('RGBA') for s in result['sprites']]
for dark in (False,True):
    name='dark' if dark else 'light'
    views,_=render_anchored_frames(frames,anchor=(96,248),dark=dark)
    grid=Image.new('RGBA',(4*256,2*384))
    for i,v in enumerate(views):
        draw=ImageDraw.Draw(v)
        draw.text((12,12),result['sprites'][i]['direction'],fill='#d5dfeb' if dark else '#24302c')
        v.save(OUT/f'previews/{i:02}-{name}.png')
        v.resize((512,768),Image.Resampling.NEAREST).save(OUT/f'previews/{i:02}-{name}-2x.png')
        grid.alpha_composite(v,((i%4)*256,(i//4)*384))
    grid.save(OUT/f'previews/placement-{name}.png')
    grid.resize((2048,1536),Image.Resampling.NEAREST).save(OUT/f'previews/placement-{name}-2x.png')
source=Image.open(OUT/'source-01.png').convert('RGBA')
for name,color in [('light','#f4f6ef'),('dark','#18222e')]:
    back=Image.new('RGBA',source.size,color);back.alpha_composite(source)
    back.save(OUT/f'previews/source-{name}.png')
# Raw source comparison and recorded registration at the same display point.
processing=json.loads((OUT/'processed/result.json').read_text())
commands=[{'command':f'{ROOT}/.venv/bin/python {SKILL}/scripts/tile_tools.py process-on-floor {OUT}/source-01.png {OUT}/guide.json {OUT}/processed --min-alpha 32 --registration floor-width','exitCode':0,'output':'process-on-floor: complete','recoveryUsed':False},{'command':f'{ROOT}/.venv/bin/python {SKILL}/scripts/assemble_result.py --input-result {OUT}/processed/result.json --registration {OUT}/registration.json --output {OUT}/result.json','exitCode':0,'output':{'kind':'directions','sprites':8}}]
(OUT/'processing-log.json').write_text(json.dumps({'status':'completed','generationCalls':1,'correctionCalls':0,'commands':commands,'sourcePreservedUnchanged':True,'sourceSHA256':sha(OUT/'source-01.png'),'processorSHA256':sha(SKILL/'scripts/tile_tools.py'),'assemblerSHA256':sha(SKILL/'scripts/assemble_result.py'),'processingResultSHA256':sha(OUT/'processed/result.json'),'registrationSHA256':sha(OUT/'registration.json'),'previewMethod':'Bundled render_anchored_frames at stored anchor; light/dark grid and magenta world-root marker. 2x uses nearest-neighbor display only.'},indent=2)+'\n')
checks=[]
for s in result['sprites']:
    p=OUT/s['image'];im=Image.open(p)
    assert im.size==(192,320)
    assert s['anchor']==[96,248]
    assert s['footprint']==[128,128]
    assert im.mode=='RGBA'
    assert im.getchannel('A').getbbox() is not None
    assert im.getchannel('A').getextrema()[0]==0
    checks.append({'id':s['id'],'direction':s['direction'],'image':s['image'],'size':list(im.size),'anchor':s['anchor'],'artRect':s['artRect'],'sha256':sha(p)})
recipe=json.loads((OUT/'generation-01.json').read_text())
assert recipe['sourceSHA256']==sha(OUT/'source-01.png')
assert recipe['referenceSHA256']['references/guide.png']==sha(OUT/'references/guide.png')
assert len(checks)==8
integrity={'status':'delivery-files-verified','independentVisualReview':'pending; executor has not graded artwork','sources':1,'generationCalls':1,'correctionCalls':0,'processing':'strict guide panels, floor-width registration, explicit reserved-color removal','sprites':checks,'resultSHA256':sha(OUT/'result.json'),'guideSHA256':sha(OUT/'guide.json'),'sourceSHA256':sha(OUT/'source-01.png')}
(OUT/'delivery-integrity.json').write_text(json.dumps(integrity,indent=2)+'\n')
for f in ['/tmp/character_directions_register_source.py','/tmp/character_directions_finalize.py']:
    shutil.copy2(f,OUT/'provenance'/Path(f).name)
# A static inspector preserves full-frame placement, with native and 2x images.
html='''<!doctype html><html><head><meta charset="utf-8"><title>Eight-direction player: delivery previews</title><style>body{font:16px system-ui;margin:24px;background:#23313f;color:#eee}img{display:block;max-width:none;margin:20px 0}a{color:#9ed5ff}h1{font-size:22px}section{overflow:auto;margin-bottom:32px;border:1px solid #52606a}p{max-width:70ch}</style></head><body><h1>Eight-direction player</h1><p>Row-major: north, northeast, east, southeast, south, southwest, west, northwest. Placement uses local ground anchor (96,248) with a 128px cell. Magenta crosses show the fixed world root. These previews are evidence for independent review.</p><p><a href="../source-01.png">Unchanged source</a> · <a href="../references/guide.png">Raster guide</a> · <a href="../result.json">Manifest</a></p>'''
for name in ['placement-light','placement-dark','placement-light-2x','placement-dark-2x','source-light','source-dark']:
    html+=f'<h2>{name}</h2><section><img src="{name}.png" alt="{name}"></section>'
html+='</body></html>'
(OUT/'previews/index.html').write_text(html)
# Inventory hashes are diagnostic evidence, not quality verdicts.
files={p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='artifact-hashes.json'}
(OUT/'artifact-hashes.json').write_text(json.dumps(files,indent=2)+'\n')
print(json.dumps({'generationCalls':1,'correctionCalls':0,'spriteCount':len(checks),'result':str(OUT/'result.json'),'submission':str(OUT/'submission.json'),'previews':str(OUT/'previews/index.html'),'sourceSHA256':sha(OUT/'source-01.png'),'resultSHA256':sha(OUT/'result.json'),'files':len(files)},indent=2))
