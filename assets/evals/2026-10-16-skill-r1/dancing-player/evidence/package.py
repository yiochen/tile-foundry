from pathlib import Path
import sys, json, hashlib
sys.dont_write_bytecode = True
from PIL import Image, ImageDraw
out = Path(__file__).resolve().parents[1]
skill = out.parent/'skill-snapshot'
sys.path.insert(0, str(skill/'scripts'))
from tile_tools import clean_alpha, floor_anchor

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n')
source = out/'source-01.png'
guide = json.loads((out/'guide.json').read_text())
raw = Image.open(source).convert('RGBA')
cleaned, cleanup = clean_alpha(raw,32)
sx, sy = raw.width/guide['size'][0],raw.height/guide['size'][1]
rects = [tuple(round(c['rect'][i]*(sx if i%2==0 else sy)) for i in range(4)) for c in guide['cells']]
observations=[]
for i, rect in enumerate(rects):
    record={'index':i,'sourceRect':list(rect)}
    try:
        observed=floor_anchor(cleaned.crop(rect))
        record['floor']=observed
        record['observedSpan']=[observed['rect'][2]-observed['rect'][0], observed['rect'][3]-observed['rect'][1]]
    except ValueError as exc:
        record['detectorError']=str(exc)
    observations.append(record)
command=['.venv/bin/python','assets/evals/2026-10-16-skill-r1/skill-snapshot/scripts/tile_tools.py','process-on-floor','assets/evals/2026-10-16-skill-r1/dancing-player/source-01.png','assets/evals/2026-10-16-skill-r1/dancing-player/guide.json','assets/evals/2026-10-16-skill-r1/dancing-player/processed','--min-alpha','32','--fps','12']
diagnostic={'processor':'skill-snapshot/scripts/tile_tools.py','processorSHA256':sha(skill/'scripts/tile_tools.py'),'command':command,'attemptCount':1,'status':'refused','message':(out/'evidence/process-strict.log').read_text().strip(),'sourceSHA256':sha(source),'sourceSize':list(raw.size),'guideSHA256':sha(out/'guide.json'),'sourceToGuideScale':[sx,sy],'sourceAspectRoundingFraction':abs(sx/sy-1),'minAlpha':32,'cleanup':cleanup,'floorDetectorAlphaThreshold':64,'acceptedFloorAspectInterval':[.95,1.05],'panelObservations':observations,'followup':'Observations only. No retry, normalization, floor removal, manual registration, or sprites were produced.'}
save(out/'evidence/processing.json',diagnostic)
previews=out/'previews';previews.mkdir(exist_ok=True)
for name,color in [('light','#f4f6ef'),('dark','#18222e')]:
    view=Image.new('RGBA',raw.size,color);view.alpha_composite(raw)
    view.convert('RGB').save(previews/f'source-{name}.png')
# Registration overlay is a diagnostic display only; it does not alter source or registration.
overlay=Image.new('RGBA',raw.size,'#18222e');overlay.alpha_composite(raw)
draw=ImageDraw.Draw(overlay)
for i,(c,rect) in enumerate(zip(guide['cells'],rects)):
    draw.rectangle((rect[0],rect[1],rect[2]-1,rect[3]-1),outline='#7190ae',width=1)
    fr=c['floorRect'];x0=rect[0]+round(fr[0]*sx);y0=rect[1]+round(fr[1]*sy);x1=rect[0]+round(fr[2]*sx);y1=rect[1]+round(fr[3]*sy)
    draw.rectangle((x0,y0,x1-1,y1-1),outline='#ff66be',width=2)
    ax=rect[0]+round(c['anchor'][0]*sx);ay=rect[1]+round(c['anchor'][1]*sy)
    draw.line((ax-7,ay,ax+7,ay),fill='#ff66be',width=2);draw.line((ax,ay-7,ax,ay+7),fill='#ff66be',width=2)
    draw.text((rect[0]+4,rect[1]+4),str(i+1),fill='#ffffff')
overlay.convert('RGB').save(previews/'source-guide-overlay.png')
html='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Dance source evidence</title><style>body{margin:24px;font:16px/1.5 system-ui;background:#eceff0;color:#17212a}img{display:block;max-width:100%;height:auto}section{margin:24px 0}button{padding:8px 12px;margin-right:8px}h1{font-size:24px}h2{font-size:18px}</style><h1>Dance source evidence</h1><p>One original generated sheet. These previews display the source with its calibration floors. No processed sprites or runtime loop were produced.</p><button onclick="document.querySelector('#source').src='source-light.png'">Light</button><button onclick="document.querySelector('#source').src='source-dark.png'">Dark</button><button onclick="document.querySelector('#source').style.maxWidth='none'">Original pixels</button><button onclick="document.querySelector('#source').style.maxWidth='100%'">Fit screen</button><section><img id="source" src="source-light.png" alt="Original dance source over a light background"></section><h2>Authored registration overlay</h2><p>Pink squares and crosses show the authored floors and ground roots, mapped by whole-sheet scale. The source artwork is unchanged.</p><img src="source-guide-overlay.png" alt="Original source with authored guide floor rectangles and root crosses">'''
(previews/'index.html').write_text(html+'\n')
authored_path=out/'generation-01-authored.json'
rich=json.loads((authored_path if authored_path.exists() else out/'generation-01.json').read_text())
save(out/'generation-01-authored.json',rich)
ref='references/guide.png'
recipe={'version':1,'prompt':rich['exactPrompt'],'tool':'image_gen.imagegen','transparentBackground':True,'sourceSHA256':sha(source),'references':[ref],'referenceSHA256':{ref:sha(out/ref)},'referenceRoles':{ref:'authored pose/layout edit target; reserved calibration squares and fixed root registration'},'toolInput':'tool-input-01.json','authoredRecord':'generation-01-authored.json','actualGenerationCalls':1,'attempt':1,'seed':None,'seedNote':'Not exposed by built-in tool'}
save(out/'generation-01.json',recipe)
result={'version':2,'kind':'animation','status':'blocked','diagnostic':'The only generated source was refused by process-on-floor: calibration floor aspect is outside its square tolerance. No safely registered floor-free sprites were produced.','projection':'top-down-oblique-square-grid','cellSize':128,'heightAxis':[0,-1],'elevationScale':1,'groundAnchorAlignment':'center','fps':12,'frameOrder':'row-major','loop':True,'sprites':[],'requestedGeometry':{'frameCount':12,'frame':[192,320],'groundAnchor':[96,248],'footprint':[128,128],'occupiedCells':[[0,0]],'nominalStandingHeight':160,'durationMs':1000/12,'sourceColumns':4,'sourceRows':3},'registration':'registration.json','processingEvidence':'evidence/processing.json','processorLog':'evidence/process-strict.log','previews':['previews/source-light.png','previews/source-dark.png','previews/source-guide-overlay.png','previews/index.html'],'geometryDeclaration':'Authored requested geometry is retained separately. No frame geometry or root compliance is claimed for the failed source.'}
save(out/'result.json',result)
submission={'caseId':'dancing-player','outputDirectory':str(out),'userPrompt':(out/'request.txt').read_text().rstrip('\n'),'sources':[{'image':'source-01.png','recipe':'generation-01.json','role':'whole-asset'}],'guide':'guide.json','guideSHA256':sha(out/'guide.json'),'result':'result.json','status':'blocked','diagnostic':'Calibration floor not square enough for supported extraction; see evidence/processing.json.','actualGenerationCalls':1}
save(out/'submission.json',submission)
save(out/'evidence/tool-response.json',{'keys':['image_url','output_hint'],'image_url':'Base64 PNG omitted from response metadata; original tool PNG copied unchanged as source-01.png','sourceSHA256':sha(source),'originalToolPath':rich['sourceImages'][0]['originalToolPath'],'output_hint':'Generated images are saved to /Users/yiouchen/.codex/generated_images/01a14397-1b81-7900-8064-243267fa374b as /Users/yiouchen/.codex/generated_images/01a14397-1b81-7900-8064-243267fa374b/exec-425ee148-152f-4111-a9e3-26671af01a3d.png by default.\nIf you need to use a generated image at another path, copy it and leave the original in place unless the user explicitly asks you to delete it.\nThe generated image is already displayed to the user. There is no need to render it in the final response as a Markdown image or file link.'})
print(json.dumps({'status':'blocked','generationCalls':1,'processedSprites':0,'firstMeasuredFloor':observations[0],'result':'result.json','submission':'submission.json'},indent=2))
