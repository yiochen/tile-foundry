#!/usr/bin/env python3
"""Package unedited captures and build deterministic review previews, never fit sprites."""
import hashlib
import json
import math
import sys
from pathlib import Path
from PIL import Image, ImageDraw

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

def main(base, skill):
    base, skill = Path(base).resolve(), Path(skill).resolve()
    capture = json.loads((base/'render/capture.json').read_text())
    case = json.loads((base/'render/scene/case.json').read_text())
    result_path = base/'processed/result.json'
    result = json.loads(result_path.read_text())
    terrain = bool(case['expected'].get('fullBase'))
    result['workflow'] = 'fresh-direct-3d-control'
    result['provenance']['artwork'] = 'Procedural Three.js geometry and authored GLSL materials' if terrain else 'Freshly rendered existing procedural skinned adventurer, fixed camera/scale/root'
    result['provenance']['imageGenerationCalls'] = 0
    result['animationDesign'] = capture['animationDesign']
    for sprite in result['sprites']:
        sprite['role'] = 'terrain' if terrain else 'player'
    write(result_path, result)
    source = base/'source-01.png'
    recipe = {'tool':'Three.js WebGLRenderer + frozen extract_registered_sheet.py',
        'isImageModelCall':False, 'imageGenerationCalls':0,
        'prompt':'Deterministic direct 3D render control; no image prompt was sent. Freshly execute the retained editable scene with one fixed square-grid orthographic camera and root. Capture the complete transparent fixed-layout sheet, then supply that unchanged raster to the frozen registered-sheet extractor at alpha threshold zero. Source appearance and motion are authored geometry, materials and animation; no old PNG is an input.',
        'transparentBackground':True,'sourceSHA256':digest(source),
        'references':['source-01.png'], 'referenceSHA256':{'source-01.png':digest(source)},
        'referenceRoles':{'source-01.png':'Fresh authored 3D color capture actually supplied to deterministic fixed-sheet extraction; no image-model reference'},
        'deterministicInputs':{'scene':'render/scene.json','sourceCode':'render/scene/3d_controls_motion_scene.js','characterSourceCode':'render/scene/character_scene.js','cameraAndRig':'render/scene/rig.json','animation':'render/scene/poses.json'},
        'processorSHA256':digest(skill/'scripts/extract_registered_sheet.py'),
        'sourceCapture':'render/capture.json','commands':'commands.json'}
    write(base/'control-recipe.json', recipe)
    write(base/'control-provenance.json', {'mode':'fresh-direct-3d-control','imageGenerationCalls':0,'oldPNGReuse':False,'freshCapture':True,'alphaThreshold':0,'rendererMaskApplied':False,'perFrameFitting':False,'animationDesign':capture['animationDesign'],'actualSourceSHA256':digest(source),'capture':'render/capture.json','note':'Authored direct 3D output, not an AI reskin or twelve model-drawn phases.'})
    write(base/'submission.json', {'caseId':case['id'],'outputDirectory':str(base),'userPrompt':(base/'request.txt').read_text().rstrip('\n'),'sources':[{'image':'source-01.png','recipe':'control-recipe.json'}],'guide':'render/guide.json','guideSHA256':digest(base/'render/guide.json'),'result':'processed/result.json'})
    previews=base/'previews';previews.mkdir()
    images=[Image.open(base/'processed'/s['image']).convert('RGBA') for s in result['sprites']]
    def composite(frame,dark=False,repeats=1,offset=False):
        out=Image.new('RGBA',(192+(repeats-1)*128+48,320+(repeats-1)*128+48),'#19232e' if dark else '#f3f5ed')
        for row in range(repeats):
            for col in range(repeats):
                index=(frame+row*3+col*5)%len(images) if offset else frame
                out.alpha_composite(images[index],(24+col*128,24+row*128))
        return out
    # Every phase is inspectable at native and 2x, synchronized and offset neighbors.
    for index in range(len(images)):
        for dark in (False,True):
            view=composite(index,dark)
            view.save(previews/f'frame-{index:02}-{"dark" if dark else "light"}-native.png')
        if terrain:
            for offset in (False,True):
                view=composite(index,False,3,offset)
                stem=f'neighbors-{index:02}-{"offset" if offset else "sync"}'
                view.save(previews/(stem+'-native.png'))
                view.resize((view.width*2,view.height*2),Image.Resampling.NEAREST).save(previews/(stem+'-2x.png'))
    sheet=Image.open(base/'processed/sheet.png').convert('RGBA')
    for dark in (False,True):
        out=Image.new('RGBA',sheet.size,'#19232e' if dark else '#f3f5ed');out.alpha_composite(sheet)
        out.save(previews/f'sheet-{"dark" if dark else "light"}-native.png')
        out.resize((out.width*2,out.height*2),Image.Resampling.NEAREST).save(previews/f'sheet-{"dark" if dark else "light"}-2x.png')
    payload={'frames':[f'../processed/{s["image"]}' for s in result['sprites']], 'terrain':terrain, 'caseId':case['id'],'fps':12,'count':len(images)}
    html='''<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Direct 3D control playback</title><style>*{box-sizing:border-box}body{font:15px system-ui;margin:0;padding:20px;background:#eef1ea;color:#203443}h1{font-size:21px;margin:0 0 8px}p{margin:8px 0}button,select,input{font:inherit;margin:4px;padding:7px}main{display:flex;flex-wrap:wrap;gap:20px}.panel{background:white;padding:12px;border-radius:10px;max-width:100%;overflow:auto}canvas{display:block;image-rendering:pixelated;max-width:none}label{display:inline-block}small{display:block;margin-top:8px;max-width:70ch}</style><h1 id="title"></h1><p>Authored direct 3D control · fixed ground anchor (96,248) · 12 fps</p><div><button id="toggle">Pause</button><button id="previous">Previous</button><button id="next">Next</button><label>Phase <input id="phase" type="range" min="0" value="0"></label><label>Scale <select id="scale"><option value="1">1× native</option><option value="2">2× pixels</option></select></label><label>Background <select id="bg"><option value="light">Light</option><option value="dark">Dark</option></select></label><span id="status"></span></div><main><section class="panel"><b>Single tile / character</b><canvas id="single"></canvas></section><section class="panel" id="syncPanel"><b>3×3 synchronized neighbors</b><canvas id="sync"></canvas></section><section class="panel" id="offsetPanel"><b>3×3 offset phases: +3 per row, +5 per column</b><canvas id="offset"></canvas></section></main><small>Terrain motion is authored analytic shader translation with a stationary 16px edge transition. Character motion is authored skeletal joint curves. No image generation, per-frame fitting, color key, cropping, or AI reskin.</small><script>const data=PAYLOAD;let frame=0,playing=true,last=0,scale=1;const images=data.frames.map(src=>{const i=new Image();i.src=src;return i});document.getElementById('title').textContent=data.caseId;document.getElementById('phase').max=data.count-1;if(!data.terrain){document.getElementById('syncPanel').hidden=true;document.getElementById('offsetPanel').hidden=true;}function drawCanvas(id,repeats,offset){const c=document.getElementById(id);c.width=192+(repeats-1)*128+48;c.height=320+(repeats-1)*128+48;c.style.width=c.width*scale+'px';c.style.height=c.height*scale+'px';const ctx=c.getContext('2d');ctx.fillStyle=document.getElementById('bg').value==='dark'?'#19232e':'#f3f5ed';ctx.fillRect(0,0,c.width,c.height);for(let r=0;r<repeats;r++)for(let k=0;k<repeats;k++){const i=(frame+(offset?r*3+k*5:0))%data.count;if(images[i].complete)ctx.drawImage(images[i],24+k*128,24+r*128);}}function draw(){drawCanvas('single',1,false);if(data.terrain){drawCanvas('sync',3,false);drawCanvas('offset',3,true);}document.getElementById('phase').value=frame;document.getElementById('status').textContent='frame '+frame+' / '+(data.count-1);}function tick(t){if(playing&&t-last>=1000/12){frame=(frame+Math.floor((t-last)/(1000/12)))%data.count;last=t;draw();}requestAnimationFrame(tick)}document.getElementById('toggle').onclick=()=>{playing=!playing;document.getElementById('toggle').textContent=playing?'Pause':'Play'};document.getElementById('phase').oninput=e=>{playing=false;frame=+e.target.value;draw()};document.getElementById('previous').onclick=()=>{playing=false;frame=(frame+data.count-1)%data.count;draw()};document.getElementById('next').onclick=()=>{playing=false;frame=(frame+1)%data.count;draw()};document.getElementById('scale').onchange=e=>{scale=+e.target.value;draw()};document.getElementById('bg').onchange=draw;window.motionPlayer={get frame(){return frame},get playing(){return playing},setFrame(n){playing=false;frame=n%data.count;draw()},play(){playing=true;last=performance.now()},draw};Promise.all(images.map(i=>i.decode())).then(()=>{draw();last=performance.now();requestAnimationFrame(tick)});</script></html>'''.replace('PAYLOAD',json.dumps(payload))
    (previews/'playback.html').write_text(html)
    # Measured raster diagnostics do not substitute for independent visual review.
    motion=[]
    for i,image in enumerate(images):
        following=images[(i+1)%len(images)]
        a,b=image.convert('RGB'),following.convert('RGB')
        if terrain:
            a,b=a.crop((32,152,160,280)),b.crop((32,152,160,280))
        differences=[sum(abs(x-y) for x,y in zip(p,q))/3 for p,q in zip(a.getdata(),b.getdata())]
        motion.append({'from':i,'to':(i+1)%len(images),'meanRGBDelta':sum(differences)/len(differences),'changedPixelsOver8':sum(d>8 for d in differences)})
    write(previews/'motion-diagnostics.json',{'gating':False,'note':'Pixel deltas are diagnostics; review actual 12fps playback and final-to-first step.','transitions':motion})
    write(previews/'evidence-index.json',{'playback':'playback.html','allPhases':[f'frame-{i:02}-light-native.png' for i in range(len(images))], 'terrainNeighborEvidence':{'synchronized':[f'neighbors-{i:02}-sync-native.png' for i in range(len(images))],'offset':[f'neighbors-{i:02}-offset-native.png' for i in range(len(images))],'nativeAnd2x':True} if terrain else None,'animationSource':'../render/scene/poses.json','editableMaterials':'../render/scene/3d_controls_motion_scene.js','camera':'../render/scene/rig.json'})
    print(json.dumps({'caseId':case['id'],'sprites':len(images),'previews':str(previews)}))

if __name__=='__main__':main(*sys.argv[1:])
