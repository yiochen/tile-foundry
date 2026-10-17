"""Preserve failed fixed-frame character delivery and create raw source diagnostics."""
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ERROR='Generated whole-sheet aspect differs from guide beyond one source pixel; no axis stretching'

def write(path,data):
    (ROOT/path).write_text(json.dumps(data,indent=2)+'\n')

def preview(im,name):
    for label,color in [('light','#eee9df'),('dark','#19212d')]:
        bg=Image.new('RGBA',im.size,color);bg.alpha_composite(im)
        bg.convert('RGB').save(ROOT/'previews'/f'{name}-{label}-source-native.png')

def main():
    sources=[]
    for n,role,part in [(1,'stool','stool'),(2,'character','character')]:
        im=Image.open(ROOT/f'source-{n:02}.png').convert('RGBA');sources.append(im)
        recipe=json.loads((ROOT/f'generation-{n:02}.json').read_text())
        recipe['sourceSHA256']=SHA(ROOT/f'source-{n:02}.png')
        recipe['referenceSHA256']={p:SHA(ROOT/p) for p in recipe['references']}
        recipe['sourceSize']=list(im.size)
        recipe['processing']={'guide':f'guides/{part}.json','command':f'.venv/bin/python assets/evals/2026-10-17-3d-creative-reskin-all/skill-snapshot/scripts/extract_registered_sheet.py {ROOT.relative_to(Path.cwd())}/source-{n:02}.png {ROOT.relative_to(Path.cwd())}/guides/{part}.json {ROOT.relative_to(Path.cwd())}/processed-{n:02} --kind object --min-alpha 32',
                'status':'success' if n==1 else 'rejected','result':'processed-01/result.json' if n==1 else None,
                **({'error':ERROR} if n==2 else {})}
        write(f'generation-{n:02}.json',recipe)
        preview(im,f'{part}-original')
    # This is a source-space diagnostic only: same original source origins, no
    # resampling, no accepted runtime transform, no normalized character file.
    raw=Image.new('RGBA',(max(i.width for i in sources),max(i.height for i in sources)))
    for im in sources:raw.alpha_composite(im,(0,0))
    raw.save(ROOT/'previews/raw-source-overlay.png');preview(raw,'raw-source-overlay')
    result={'version':2,'kind':'layered','projection':'top-down-oblique-square-grid','cellSize':128,
            'groundAnchorAlignment':'center','workflow':'3d-imagegen-reskin','sprites':[],
            'processingFailure':{'source':'source-02.png','guide':'guides/character.json','reason':ERROR,
                                 'sourceSize':list(sources[1].size),'guideSize':[384,640],
                                 'requiredTolerancePx':1,'delivery':'source-only; no normalized character or recomposed runtime candidate'},
            'declaredGeometry':{'frame':[192,320],'anchor':[96,248],'footprint':[128,128],
                 'occupiedCells':[[0,0]],'nominalStandingHeightPx':160,'supportElevationPx':48,
                 'supportElevationBakedIntoArt':True,'attachmentPoint':[96,220.48],
                 'elevationOffsetAppliedDuringRecompositionPx':0},
            'availableIndependentProcessing':{'stool':{'source':'source-01.png','result':'processed-01/result.json','role':'retained successful individual extraction; incomplete case delivery'}},
            'provenance':{'imageGenerationCalls':2,'reskinSources':['source-01.png','source-02.png'],
                 'geometryReferenceRun':'2026-10-17-3d-control-all','stage':'3d-capture-then-imagegen',
                 'geometryReference':'provenance/reused-geometry.json'},'independentReviewPending':True}
    write('result.json',result)
    write('submission.json',{'caseId':'seated-character-separated','outputDirectory':str(ROOT),
          'userPrompt':(ROOT/'request.txt').read_text().rstrip('\n'),
          'sources':[{'image':f'source-{n:02}.png','recipe':f'generation-{n:02}.json','role':r} for n,r in [(1,'stool'),(2,'character-only')]],
          'guide':'guide.json','guideSHA256':SHA(ROOT/'guide.json'),'result':'result.json','deliveryStatus':'source-only-processing-failure'})
    write('previews/preview-recipe.json',{'script':'../art/assemble_and_preview.py','sourceImages':['../source-01.png','../source-02.png'],
          'rawOverlay':{'operation':'alpha composite unmodified generated source canvases at identical original top-left origins',
                        'sourceSizes':[list(i.size) for i in sources],'offsetsPx':[[0,0],[0,0]],'resampling':False,
                        'purpose':'Unregistered source diagnostic only; character extraction failed; never a runtime candidate'},
          'runtimeRecompositionAvailable':False,'reason':ERROR,'fallback':False})
    processor=ROOT.parent/'skill-snapshot/scripts/extract_registered_sheet.py'
    write('provenance/processing-error.json',{'source':'../source-02.png','processor':{'name':processor.name,'sha256':SHA(processor),'frozenRun':'2026-10-17-3d-creative-reskin-all'},'kind':'object','minAlpha':32,'exitCode':1,'error':ERROR,'retry':False,'recovery':False})
    write('execution.json',{'workflow':'3d-imagegen-reskin','status':'complete-source-only-processing-failure',
          'plannedImageGenerationCalls':2,'imageGenerationCalls':2,'completedImageGenerationCalls':2,
          'attemptPolicy':'one stool and one character-only attempt; no retries/fallback',
          'minAlpha':32,'guideAuthoredBeforeGeneration':True,
          'extractions':[{'source':'source-01.png','status':'success','result':'processed-01/result.json'},
                         {'source':'source-02.png','status':'rejected','error':ERROR}],
          'sourceOnlyFailure':True,'independentReviewPending':True})

if __name__=='__main__':main()
