from pathlib import Path
import hashlib,json,subprocess,sys
from PIL import Image,ImageDraw
root=Path('/Users/yiouchen/.codex/worktrees/1834/tile-foundry/assets/evals/2026-10-16-skill-r3/animated-lava')
skill=root.parent/'skill-snapshot'
repo=root.parents[3]
py='/Users/yiouchen/.codex/worktrees/1834/tile-foundry/.venv/bin/python'
sys.path.insert(0,str(skill/'scripts'))
from review_playback import write_playback
result=json.loads((root/'result.json').read_text())
prev=root/'previews';prev.mkdir(exist_ok=True)
frames=result['sprites'];images=[Image.open(root/s['image']).convert('RGBA') for s in frames]
write_playback(frames,[root/s['image'] for s in frames],prev/'playback.html',terrain=True)
logs=[]
for i,s in enumerate(frames):
 cmd=[py,str(repo/'tools/tilekit.py'),'check-solid',str(root/s['image']),str(prev/f'coverage-{i:02}.json'),'--anchor','96','312','--pitch','128','128','--body-rect','32','152','160','312','--preview']
 r=subprocess.run(cmd,capture_output=True,text=True)
 logs.append({'argv':cmd,'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
# Complete frames on light/dark at native scale and 2x. No trim or refit.
for dark,color in ((False,'#f4f6ef'),(True,'#18222e')):
 sheet=Image.new('RGBA',(4*192,3*344),color)
 draw=ImageDraw.Draw(sheet)
 for i,im in enumerate(images):
  x=(i%4)*192;y=(i//4)*344
  sheet.alpha_composite(im,(x,y))
  X=x+96;Y=y+248
  draw.line((X-5,Y,X+5,Y),fill='#b72e74');draw.line((X,Y-5,X,Y+5),fill='#b72e74')
  draw.text((x+8,y+324),f'{i+1:02} / 12 - anchor (96,248)',fill='white' if dark else 'black')
 name='frames-dark' if dark else 'frames-light'
 sheet.convert('RGB').save(prev/f'{name}-native.png')
 sheet.resize((sheet.width*2,sheet.height*2),Image.Resampling.NEAREST).convert('RGB').save(prev/f'{name}-2x.png')
# 3x3 registered terrain placement at every phase, both same and offset neighbors.
# Root origin accommodates complete frame bounds and lets rear rows be occluded naturally.
for phase in range(12):
 for offset in (False,True):
  canvas=Image.new('RGBA',(496,624),'#f4f6ef')
  draw=ImageDraw.Draw(canvas)
  for y in range(3):
   for x in range(3):
    rx=120+x*128;ry=272+y*128
    draw.rectangle((rx-64,ry-64,rx+64,ry+64),outline='#789080')
  for y in range(3):
   for x in range(3):
    j=(phase+(x+y*3 if offset else 0))%12
    canvas.alpha_composite(images[j],(24+x*128,24+y*128))
  for y in range(3):
   for x in range(3):
    rx=120+x*128;ry=272+y*128
    draw.line((rx-5,ry,rx+5,ry),fill='#b72e74');draw.line((rx,ry-5,rx,ry+5),fill='#b72e74')
  label='offset' if offset else 'sync'
  canvas.convert('RGB').save(prev/f'repeat-{label}-{phase:02}-native.png')
  canvas.resize((992,1248),Image.Resampling.NEAREST).convert('RGB').save(prev/f'repeat-{label}-{phase:02}-2x.png')
(root/'preview-commands.json').write_text(json.dumps(logs,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=Image.open(root/'template/shaded.png').convert('RGBA')
evidence={
 'generationCalls':1,'sourceUnchangedSHA256':sha(root/'source-01.png'),
 'guideSHA256':sha(root/'guide.json'),'resultSHA256':sha(root/'result.json'),
 'processingMethod':'frozen material_animation.py + assemble_result.py; tilekit.py check-solid diagnostic previews',
 'source':{'size':list(Image.open(root/'source-01.png').size),'fullyOpaque':Image.open(root/'source-01.png').convert('RGBA').getchannel('A').getextrema()==(255,255)},
 'spriteSHA256':{s['id']:sha(root/s['image']) for s in frames},
 'frames':[{'id':s['id'],'size':list(im.size),'anchor':s['anchor'],'footprint':s['footprint'],'elevationPx':s['elevationPx'],'durationMs':s['durationMs'],'alphaIdenticalToTemplate':im.getchannel('A').tobytes()==base.getchannel('A').tobytes(),'artBoundsLTRB':im.getchannel('A').getbbox()} for s,im in zip(frames,images)],
 'previews':'previews/playback.html; all 12 native and 2x same-phase/offset-phase repeat images; complete-frame light/dark sheets',
 'independentVisualReview':'pending; no self-grade or review.json authored'}
(root/'processing-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
print(json.dumps({'frames':len(frames),'allAlphaPreserved':all(f['alphaIdenticalToTemplate'] for f in evidence['frames']),'tilekitCommandExitCodes':[r['exitCode'] for r in logs],'previewDirectory':str(prev)},indent=2))
