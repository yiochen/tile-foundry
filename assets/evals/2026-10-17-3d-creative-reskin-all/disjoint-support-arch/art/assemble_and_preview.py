"""Assemble complete AI depth pieces at unchanged authored roots; no fitting."""
import copy
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SHA = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def write(path, data):
    (ROOT / path).write_text(json.dumps(data, indent=2) + "\n")

def cutout(image, name):
    for label, color in [('light', '#eee9df'), ('dark', '#19212d')]:
        bg = Image.new('RGBA', image.size, color)
        bg.alpha_composite(image)
        bg.convert('RGB').save(ROOT / 'previews' / f'{name}-{label}-native.png')
        bg.resize((image.width*2, image.height*2), Image.Resampling.NEAREST).convert('RGB').save(ROOT/'previews'/f'{name}-{label}-2x.png')

def main():
    (ROOT/'sprites').mkdir(exist_ok=True)
    pieces = []
    layers = []
    for number, name, zrange, order in [(1,'arch-rear',[-.5,0],0),(2,'arch-front',[0,.5],2)]:
        im = Image.open(ROOT/f'processed-{number:02}/frames/frame-00.png').convert('RGBA')
        im.save(ROOT/f'sprites/{name}.png')
        processed = json.loads((ROOT/f'processed-{number:02}/result.json').read_text())
        entry = copy.deepcopy(processed['sprites'][0])
        entry.update(id=name, image=f'sprites/{name}.png', role='arch-depth-piece', footprint=[384,128],
                     occupiedCells=[[0,0],[2,0]], supportCells=[[0,0],[2,0]],
                     overheadCells=[[0,0],[1,0],[2,0]], drawOrder=order,
                     worldZInterval=zrange, worldXInterval=[-1.5,1.5], worldYInterval=[0,1.25],
                     transform={'offsetPx':[0,0], 'groundAnchor':[256,312], 'elevationOffsetAppliedPx':0},
                     reskinSource=f'source-{number:02}.png', reskinRecipe=f'generation-{number:02}.json',
                     geometryReference=f'references/{name}-3d.png',
                     processingResult=f'processed-{number:02}/result.json',
                     derivation='Complete independent 3D depth piece reskinned by one imagegen call; fixed authored frame extraction; no raster slicing')
        entry['registration']['guide']=f'guides/{name}.json'
        pieces.append(entry)
        layers.append(im)
        cutout(im,name)
        recipe=json.loads((ROOT/f'generation-{number:02}.json').read_text())
        recipe['sourceSHA256']=SHA(ROOT/f'source-{number:02}.png')
        recipe['referenceSHA256']={p:SHA(ROOT/p) for p in recipe['references']}
        recipe['processing']={'guide':f'guides/{name}.json','command':f'.venv/bin/python assets/evals/2026-10-17-3d-creative-reskin-all/skill-snapshot/scripts/extract_registered_sheet.py {ROOT.relative_to(Path.cwd())}/source-{number:02}.png {ROOT.relative_to(Path.cwd())}/guides/{name}.json {ROOT.relative_to(Path.cwd())}/processed-{number:02} --kind object --min-alpha 32','result':f'processed-{number:02}/result.json'}
        write(f'generation-{number:02}.json',recipe)
    whole=Image.new('RGBA',(512,448))
    for layer in layers:whole.alpha_composite(layer,(0,0))
    whole.save(ROOT/'sprites/whole.png')
    box=whole.getchannel('A').getbbox()
    sprite={'id':'disjoint-support-arch','image':'sprites/whole.png','size':[512,448],
            'anchor':[256,312],'footprint':[384,128],'occupiedCells':[[0,0],[2,0]],
            'supportCells':[[0,0],[2,0]],'overheadCells':[[0,0],[1,0],[2,0]],'elevationPx':160,
            'artRect':[box[0],box[1],box[2]-box[0],box[3]-box[1]],
            'reskinSources':['source-01.png','source-02.png'],
            'composition':{'operation':'alpha composite complete rear then front AI depth pieces',
                           'inputs':['sprites/arch-rear.png','sprites/arch-front.png'],'offsetsPx':[[0,0],[0,0]],
                           'commonGroundAnchor':[256,312],'elevationOffsetAppliedPx':0},
            'registration':{'method':'authored-3d-projection','guide':'guide.json','scope':'Authored roots and frame only; generated geometry requires independent visual review'}}
    result={'version':2,'kind':'object','projection':'top-down-oblique-square-grid','cellSize':128,
            'groundAnchorAlignment':'center','heightAxis':[0,-1],'elevationScale':1,
            'workflow':'3d-imagegen-reskin','sprites':[sprite],'depthPieces':pieces,
            'supportCells':[[0,0],[2,0]],'overheadCells':[[0,0],[1,0],[2,0]],
            'processing':{'operation':'frozen fixed-sheet extraction then authored composition',
                          'minAlpha':32,'perPieceFit':False,'crop':False,'silhouetteMask':False,
                          'colorKey':False,'sourcePixelsRetainedExceptDeclaredGlobalAlphaThreshold':True},
            'provenance':{'imageGenerationCalls':2,'reskinSources':['source-01.png','source-02.png'],
                          'geometryReferenceRun':'2026-10-17-3d-control-all','stage':'3d-capture-then-imagegen',
                          'geometryReference':'provenance/reused-geometry.json'},'independentReviewPending':True}
    write('result.json',result)
    write('submission.json',{'caseId':'disjoint-support-arch','outputDirectory':str(ROOT),'userPrompt':(ROOT/'request.txt').read_text().rstrip('\n'),
          'sources':[{'image':f'source-{n:02}.png','recipe':f'generation-{n:02}.json','role':name} for n,name in [(1,'rear-depth-piece'),(2,'front-depth-piece')]],
          'guide':'guide.json','guideSHA256':SHA(ROOT/'guide.json'),'result':'result.json'})
    cutout(whole,'depth-pieces-recomposed')
    actor_records=[]
    for position,z in [('behind',-.8),('center',0),('foreground',.8)]:
        actorpath=f'geometry-reference/render/actor-{position}.png'
        actor=Image.open(ROOT/actorpath).convert('RGBA')
        sequence=[actor,*layers] if position=='behind' else [layers[0],actor,layers[1]] if position=='center' else [*layers,actor]
        out=Image.new('RGBA',(512,448))
        for item in sequence:out.alpha_composite(item,(0,0))
        cutout(out,f'depth-pieces-actor-{position}')
        actor_records.append({'position':position,'worldZ':z,'reference':'../'+actorpath,'role':'Reused separate 3D diagnostic actor only; arch pieces are new AI artwork','offsetPx':[0,0]})
    write('previews/preview-recipe.json',{'script':'../art/assemble_and_preview.py','candidateArt':['../sprites/arch-rear.png','../sprites/arch-front.png'],
          'placement':'All complete 512x448 frames composite at origin, common stored ground root (256,312)','fitting':False,'diagnosticActors':actor_records})
    write('execution.json',{'workflow':'3d-imagegen-reskin','status':'complete-pending-independent-review',
          'plannedImageGenerationCalls':2,'imageGenerationCalls':2,'completedImageGenerationCalls':2,
          'attemptPolicy':'one attempt per planned piece; no retries or fallback','minAlpha':32,
          'guideAuthoredBeforeGeneration':True,'extractions':[{'source':f'source-{n:02}.png','status':'success','result':f'processed-{n:02}/result.json'} for n in [1,2]],
          'processingClaims':'Fixed registration only; AI geometry and art quality not self-graded','independentReviewPending':True})

if __name__=='__main__':main()
