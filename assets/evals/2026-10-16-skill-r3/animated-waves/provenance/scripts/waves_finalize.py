from pathlib import Path
import json,hashlib,sys,shutil,subprocess
from PIL import Image,ImageDraw
root=Path('/Users/yiouchen/.codex/worktrees/1834/tile-foundry')
out=root/'assets/evals/2026-10-16-skill-r3/animated-waves'
skill=root/'assets/evals/2026-10-16-skill-r3/skill-snapshot'
sys.path.insert(0,str(skill/'scripts'))
from review_playback import write_playback
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,indent=2)+'\n')
args=json.loads((out/'tool-inputs-01.json').read_text())
recipe={'prompt':args['prompt'],'tool':'image_gen.imagegen','transparentBackground':False,
 'sourceSHA256':sha(out/'source-01.png'),'references':['references/material-atlas-guide.png'],
 'referenceSHA256':{'references/material-atlas-guide.png':sha(out/'references/material-atlas-guide.png')},
 'referenceRoles':{'references/material-atlas-guide.png':'layout edit target: twelve opaque square appearance-material samples'},
 'actualToolInputs':'tool-inputs-01.json','sourceRole':'appearance-material','generationCallCount':1,
 'toolOutputOriginalPath':'/Users/yiouchen/.codex/generated_images/01a143a5-d451-7d41-bc2c-d8389edb569b/exec-fb1011d1-1472-4a2e-a3cd-40ed45b382be.png'}
write(out/'generation-01.json',recipe)
write(out/'submission.json',{'caseId':'animated-waves','outputDirectory':str(out),
 'userPrompt':(out/'request.txt').read_text().rstrip('\n'),
 'sources':[{'image':'source-01.png','recipe':'generation-01.json','role':'appearance-material'}],
 'guide':'guide.json','guideSHA256':sha(out/'guide.json'),'result':'result.json'})
result=json.loads((out/'result.json').read_text())
preview=out/'previews'; preview.mkdir(exist_ok=True)
frames=[Image.open(out/s['image']).convert('RGBA') for s in result['sprites']]
paths=[out/s['image'] for s in result['sprites']]
write_playback(result['sprites'],paths,preview/'playback.html',terrain=True)
# Retain complete stored frames for contrast inspection; no alpha trimming.
for dark,bg in [(False,'#f4f6ef'),(True,'#18222e')]:
 sheet=Image.new('RGBA',(4*192,3*320),bg)
 for i,im in enumerate(frames):
  x=(i%4)*192;y=(i//4)*320
  sheet.alpha_composite(im,(x,y))
  draw=ImageDraw.Draw(sheet)
  draw.line((x+91,y+248,x+101,y+248),fill='#dd2470',width=1)
  draw.line((x+96,y+243,x+96,y+253),fill='#dd2470',width=1)
 sheet.save(preview/('cutouts-dark.png' if dark else 'cutouts-light.png'))
# Placement is worldGround minus stored local root. Rows paint back to front.
for phase in range(12):
 for offset in [False,True]:
  canvas=Image.new('RGBA',(432,464),'#18222e')
  for row in range(3):
   for col in range(3):
    i=(phase+col+row*3)%12 if offset else phase
    ground=(88+col*128,152+row*128)
    s=result['sprites'][i]
    xy=(round(ground[0]-s['anchor'][0]),round(ground[1]-s['anchor'][1]))
    canvas.alpha_composite(frames[i],xy)
  name=f'repeat-{phase:02}'+('-offset' if offset else '')+'.png'
  canvas.save(preview/name)
  canvas.resize((864,928),Image.Resampling.NEAREST).save(preview/(Path(name).stem+'-2x.png'))
# The unmodified 4x3 runtime sheet plus nominal timing remain authoritative.
source=Image.open(out/'source-01.png').convert('RGBA')
proc=json.loads((out/'processed/result.json').read_text())
alpha=frames[0].getchannel('A').tobytes()
evidence={'generationCalls':1,'sourcePNG':{'path':'source-01.png','sha256':sha(out/'source-01.png'),
 'size':list(source.size),'alphaExtrema':list(source.getchannel('A').getextrema())},
 'processing':{'processor':'frozen scripts/material_animation.py compose','exitCode':0,'strength':.7,
 'frameCount':len(frames),'uniformSourceScale':proc['uniformSourceScale'],'sourceRects':proc['sourceRects'],
 'alphaPreserved':all(im.getchannel('A').tobytes()==alpha for im in frames),
 'allFramesSize':[192,320],'allFramesAnchor':[96,248],'footprint':[128,128],
 'topRect':[32,152,160,280],'frontRect':[32,280,160,312],
 'anchorConversion':proc['anchorConversion'],'fps':12,'durationMs':1000/12,
 'motion':'Only the 12 supplied atlas phases; no synthesized motion or interpolation'},
 'validationScope':'Delivery integrity only; no self-grade or visual pass/fail assessment',
 'previewPaths':['previews/playback.html','previews/cutouts-light.png','previews/cutouts-dark.png'],
 'files':{s['image']:sha(out/s['image']) for s in result['sprites']}}
write(out/'processing-evidence.json',evidence)
print(json.dumps({'submission':str(out/'submission.json'),'frames':len(frames),'sourceSize':list(source.size),'previews':len(list(preview.glob('*')))}))
