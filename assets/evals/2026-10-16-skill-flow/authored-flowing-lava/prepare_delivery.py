"""Reproducible packaging and ungraded preview generation; no source art edits."""
from pathlib import Path
import sys,json,hashlib,datetime
from PIL import Image,ImageDraw,ImageChops
OUT=Path(__file__).resolve().parent
SKILL=OUT.parent/'skill-snapshot'
sys.path.insert(0,str(SKILL/'scripts'))
from review_playback import write_playback
from prepare_review import placement_preview

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,obj): Path(p).write_text(json.dumps(obj,indent=2)+'\n')
result=json.loads((OUT/'result.json').read_text())
processed=json.loads((OUT/'processed/result.json').read_text())
recipe=json.loads((OUT/'generation-01.json').read_text())
write(OUT/'submission.json',{
 'caseId':'authored-flowing-lava','outputDirectory':str(OUT),
 'userPrompt':(OUT/'request.txt').read_text().rstrip('\n'),
 'sources':[{'image':'source-01.png','recipe':'generation-01.json','role':'appearance-material'}],
 'guide':'guide.json','guideSHA256':sha(OUT/'guide.json'),'result':'result.json'
})
# The exact processor output remains in processed/result.json. Canonical record
# additionally points to the complete provenance and authored template.
result['processingRecord']='processed/result.json'
result['sourceRecords']=[{'image':'source-01.png','role':'appearance-material','recipe':'generation-01.json'}]
result['templateGeometry']='template/geometry.json'
result['templateSVG']='template/shaded.svg'
result['processingPlan']='processing-plan.json'
result['visualReviewStatus']='pending independent reviewer; executor did not grade'
write(OUT/'result.json',result)
P=OUT/'previews';P.mkdir(exist_ok=True)
frames=[Image.open(OUT/s['image']).convert('RGBA') for s in result['sprites']]
for phase,(sprite,im) in enumerate(zip(result['sprites'],frames)):
 for dark in (False,True):
  theme='dark' if dark else 'light'
  path=P/f'cutout-{phase:02}-{theme}.png'
  placement_preview(im,sprite,path,dark=dark)
  with Image.open(path) as p: p.resize((p.width*2,p.height*2),Image.Resampling.NEAREST).save(P/f'cutout-{phase:02}-{theme}-2x.png')
  for offset in (False,True):
   label='offset' if offset else 'same'
   # Complete frames at stored roots and unaltered 128px pitch, row-major depth.
   view=Image.new('RGBA',(192+256+48,320+256+48),'#18222e' if dark else '#f4f6ef')
   draw=ImageDraw.Draw(view)
   for y in range(3):
    for x in range(3):
     X,Y=24+x*128+96,24+y*128+248
     draw.rectangle((X-64,Y-64,X+63,Y+63),fill='#283543' if dark else '#dfe5dc',outline='#6b7f70')
   for y in range(3):
    for x in range(3):
     f=(phase+x+y*3)%12 if offset else phase
     view.alpha_composite(frames[f],(24+x*128,24+y*128))
   draw=ImageDraw.Draw(view)
   for y in range(3):
    for x in range(3):
     X,Y=24+x*128+96,24+y*128+248
     draw.line((X-5,Y,X+5,Y),fill='#b72e74');draw.line((X,Y-5,X,Y+5),fill='#b72e74')
   target=P/f'repeat-{label}-{phase:02}-{theme}.png'
   view.save(target)
   view.resize((view.width*2,view.height*2),Image.Resampling.NEAREST).save(P/f'repeat-{label}-{phase:02}-{theme}-2x.png')
# All-frame contact sheets show the complete stored frame, without trimming.
for dark in (False,True):
 theme='dark' if dark else 'light'
 sheet=Image.new('RGBA',(4*192,3*320),'#18222e' if dark else '#f4f6ef')
 for i,im in enumerate(frames):sheet.alpha_composite(im,((i%4)*192,(i//4)*320))
 sheet.save(P/f'contact-sheet-{theme}.png')
 sheet.resize((sheet.width*2,sheet.height*2),Image.Resampling.NEAREST).save(P/f'contact-sheet-{theme}-2x.png')
write_playback(result['sprites'],[OUT/s['image'] for s in result['sprites']],P/'playback.html',terrain=True)
# Exact APNG timing is not used as authority; browser playback follows 12 fps.
# Retain an overview indexed by frame and theme for review navigation.
links=['<!doctype html><meta charset="utf-8"><title>Lava review previews</title><style>body{font:16px system-ui;margin:24px}img{max-width:100%;image-rendering:pixelated}a{display:block;margin:8px}</style><h1>Ungraded lava review evidence</h1><a href="playback.html">12 fps registered playback</a>']
for i in range(12):
 links.append(f'<h2>Frame {i}</h2>')
 for name in [f'cutout-{i:02}-light',f'cutout-{i:02}-dark',f'repeat-same-{i:02}-light',f'repeat-offset-{i:02}-light']:
  links.append(f'<a href="{name}-2x.png">{name} at 2×</a><img src="{name}.png">')
(P/'index.html').write_text('\n'.join(links))
# Delivery integrity diagnostics are facts and deliberately contain no grade.
alpha=Image.open(OUT/'template/shaded.png').convert('RGBA').getchannel('A').tobytes()
source=Image.open(OUT/'source-01.png')
checks={
 'sourceSize':list(source.size),'sourceFullyOpaque':source.convert('RGBA').getchannel('A').getextrema()==(255,255),
 'sourceSHA256':sha(OUT/'source-01.png'),'matchesGenerationRecipe':sha(OUT/'source-01.png')==recipe['sourceSHA256'],
 'frameCount':len(frames),'frameSizes':[list(i.size) for i in frames],
 'anchors':[s['anchor'] for s in result['sprites']],
 'fps':result['fps'],'durationMs':[s['durationMs'] for s in result['sprites']],
 'runtimeSheetSize':list(Image.open(OUT/'processed/sheet.png').size),
 'allAlphaMatchesAuthoredTemplate':all(i.getchannel('A').tobytes()==alpha for i in frames),
 'distinctFrameCount':len({i.tobytes() for i in frames}),
 'authoredLoopPhase12MatchesPhase0':processed['materialProcessing']['translation']['frame12EqualsFrame0'],
 'visualConclusions':'none; independent visual review pending'
}
write(OUT/'delivery-diagnostics.json',checks)
# Source/reference/tool and processing evidence is bundled with hashes.
write(OUT/'processing-evidence.json',{
 'generationCalls':1,'correctiveGenerationCalls':0,'generationTool':'image_gen.imagegen',
 'toolInputs':'tool-inputs-01.json','sourceOriginalPath':recipe['sourceOriginalPath'],
 'sourceSHA256':recipe['sourceSHA256'],'unchangedSourcePreserved':True,
 'referencesActuallySupplied':[],
 'inspectedNotSupplied':[{'image':'provenance/perspective-reference-inspected-not-supplied.jpg','SHA256':sha(OUT/'provenance/perspective-reference-inspected-not-supplied.jpg'),'role':'projection convention'}],
 'commands':[
 'python skill-snapshot/scripts/guide_tools.py floor authored-flowing-lava/guide',
 'python skill-snapshot/scripts/svg_tools.py template authored-flowing-lava/template --height 32 --palette lava --plain --terrain',
 'python skill-snapshot/scripts/material_flow.py compose authored-flowing-lava/template authored-flowing-lava/source-01.png authored-flowing-lava/processed --strength .7 --edge-band 16',
 'python skill-snapshot/scripts/assemble_result.py --input-result authored-flowing-lava/processed/result.json --registration authored-flowing-lava/registration.json --output authored-flowing-lava/result.json',
 'python authored-flowing-lava/prepare_delivery.py'],
 'commandBaseDirectory':str(OUT.parent),'pythonInterpreter':str(OUT.parents[3]/'.venv/bin/python'),
 'processingParameters':processed['materialProcessing'],'sourceMapping':processed['provenance'],
 'retainedScripts':['prepare_delivery.py'],'authoredGeometry':'template/geometry.json',
 'geometryAuthority':'Authored SVG, not model drawn geometry. Texture material is not claimed geometrically exact.'
})
write(OUT/'artifact-hashes.json',{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='artifact-hashes.json'})
print(json.dumps(checks,indent=2))
