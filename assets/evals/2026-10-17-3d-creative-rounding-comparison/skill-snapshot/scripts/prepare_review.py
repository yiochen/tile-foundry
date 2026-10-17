#!/usr/bin/env python3
"""Prepare an unprimed visual-review packet; never calls a model or grades art."""
import argparse
import hashlib
import json
from pathlib import Path
from evaluate import contained, POLICY
from tile_tools import render_floor_repeat, write_json
from PIL import Image, ImageDraw
from review_playback import write_playback


def placement_preview(image, sprite, output, dark=False, repeats=1, footprint=None):
    """Show complete frames on a declared grid, with no past measurements/verdicts."""
    # Depth pieces share the object's registration but need not declare a logical
    # footprint of their own. Use the case grid for display, not invented metadata.
    px, py = sprite.get('footprint', footprint)
    ax, ay = sprite['anchor']
    margin = 24
    view = Image.new('RGBA',(image.width+(repeats-1)*px+2*margin,
                             image.height+(repeats-1)*py+2*margin),
                     '#18222e' if dark else '#f4f6ef')
    draw = ImageDraw.Draw(view)
    roots = []
    for row in range(repeats):
        for column in range(repeats):
            x,y = margin+column*px,margin+row*py
            root = (x+ax,y+ay);roots.append(root)
            left,top = root[0]-px/2,root[1]-py/2
            draw.rectangle((left,top,left+px-1,top+py-1),fill='#283543' if dark else '#dfe5dc',outline='#6b7f70')
            for dx in range(128,px,128):draw.line((left+dx,top,left+dx,top+py),fill='#6b7f70')
            for dy in range(128,py,128):draw.line((left,top+dy,left+px,top+dy),fill='#6b7f70')
    for row in range(repeats):
        for column in range(repeats):view.alpha_composite(image,(margin+column*px,margin+row*py))
    for x,y in roots:
        draw.line((x-6,y,x+6,y),fill='#b72e74');draw.line((x,y-6,x,y+6),fill='#b72e74')
    view.save(output)


def prepare_review(run_root, case_id, output):
    run_root, output = Path(run_root).resolve(), Path(output).resolve()
    run = json.loads((run_root/'run.json').read_text())
    suite_path = contained(run_root, run['suite'])
    if hashlib.sha256(suite_path.read_bytes()).hexdigest() != run['suiteSHA256']:
        raise ValueError('Frozen eval suite was modified')
    case = next(c for c in json.loads(suite_path.read_text())['cases'] if c['id'] == case_id)
    base = (run_root/case['outputSubdir']).resolve()
    submission = json.loads(contained(base, 'submission.json').read_text())
    result_path = contained(base, submission['result'])
    result = json.loads(result_path.read_text())
    guide = contained(base, submission['guide'])
    guide_record = json.loads(guide.read_text())
    sprites = result.get('sprites', []) + result.get('depthPieces', [])
    assets = [{'role':'source', 'sourceRole':s.get('role','whole-asset'),
               'path':str(contained(base, s['image']))} for s in submission['sources']]
    for source in submission['sources']:
        recipe_path = contained(base, source['recipe'])
        recipe = json.loads(recipe_path.read_text())
        assets += [{'role':'input-reference',
                    'path':str(contained(recipe_path.parent,p,base))} for p in recipe.get('references',[])]
    if guide_record.get('kind') == 'rendered-3d-sheet':
        # These are authored capture views, not past result screenshots or grades.
        for reference in guide_record.get('authoredRenders',[]):
            if reference.get('role') in ('neutral-standing','rigged-reference','floor-registration',
                                          'neutral-standing-on-floor'):
                path=contained(guide.parent,reference['image'],base)
                if path.suffix.lower() == '.png':
                    assets.append({'role':reference['role'],'path':str(path)})
    assets += [{'role':'processed', 'id':s['id'], 'path':str(contained(result_path.parent,s['image'],base))} for s in sprites]
    operations = []
    for sprite in sprites:
        registration = sprite.get('registration',{})
        method = registration.get('method')
        processing = sprite.get('processing',{})
        processing = processing if isinstance(processing,dict) else {}
        if processing.get('anchorMode') == 'Measured calibration-floor center, independent of feet or cutout bounds':
            method = 'measured-calibration-floor'
        if processing.get('method') == 'Whole square material, uniform resampling; no crop or guessed-color removal':
            method = 'uniform-square-resampling'
        if method not in ('authored-svg-faces','measured-calibration-floor','authored-source-canvas',
                          'authored-3d-projection','uniform-square-resampling'):
            method = 'unspecified'
        if processing.get('alphaPreserved') and 'templateNearEdgeAnchor' in processing:
            method = 'authored-svg-faces'
        normalization = (sprite.get('normalization',{}) if method == 'authored-3d-projection'
                         else processing.get('normalization',processing))
        operation = {'sprite':sprite['id'],'registrationMethod':method}
        if 'registrationBasis' in processing:
            operation['registrationBasis']=processing['registrationBasis']
        operation['transform'] = {k:normalization[k] for k in ('sourceSize','sourceRect','anchorSource','scale','subpixelShift') if k in normalization}
        if method == 'authored-3d-projection':
            operation['transform'].update({k:normalization[k] for k in
                ('sourceOrigin','anchorIn','anchorOut','perPoseFitting') if k in normalization})
            operation['sourceRect']=registration.get('sourceRect')
            operation['cleanup']={k:result.get('cleanup',{})[k] for k in
                ('minAlpha','removedAlphaMass','rendererMaskApplied','colorKeyApplied') if k in result.get('cleanup',{})}
        chroma = processing.get('chroma',{})
        if 'keyRGB' in chroma:operation['keyRGB'] = chroma['keyRGB']
        uv=processing.get('uvShift',{})
        if uv:
            operation['uvShift']={k:uv[k] for k in ('phase','appliedXPixels','appliedYPixels') if type(uv.get(k)) in (int,float)}
        operations.append(operation)
        if method == 'authored-svg-faces':
            geometry_name=registration.get('guide')
            if not geometry_name:
                # Standard material helper preserves its processor result separately.
                for candidate in base.glob('*/result.json'):
                    metadata=json.loads(candidate.read_text())
                    record=metadata.get('provenance',{}).get('templateGeometry',{})
                    corresponding=[f for f in metadata.get('frames',[]) if
                                   (candidate.parent/f.get('image','')).resolve()==
                                   (result_path.parent/sprite['image']).resolve()]
                    if record.get('path') and corresponding:
                        geometry_name=str((candidate.parent/record['path']).resolve().relative_to(base))
                        break
            if not geometry_name:continue
            geometry = contained(result_path.parent,geometry_name,base)
            # Geometry definitions/raster precede material compositing; omit
            # measured coverage and result commentary from the review packet.
            template = geometry.parent/'template.png'
            if template.is_file():
                assets.append({'role':'authored-geometry','path':str(contained(geometry.parent,'template.png',base))})
    if case['kind']=='animation' and result.get('sprites'):
        path=output/'playback.html'
        output.mkdir(parents=True,exist_ok=True)
        frames=result['sprites']
        write_playback(frames,[contained(result_path.parent,s['image'],base) for s in frames],path,
                       terrain=bool(case['expected'].get('fullBase')))
        assets.append({'role':'motion-preview','path':str(path)})
    # Do not forward arbitrary cached previews: gallery screenshots and result
    # prose can expose old verdicts. Rebuild only artwork/registration views.
    output.mkdir(parents=True,exist_ok=True)
    for index,sprite in enumerate(sprites):
        with Image.open(contained(result_path.parent,sprite['image'],base)) as image:
            for dark in (False,True):
                path = output/f'placement-{index}-{"dark" if dark else "light"}.png'
                placement_preview(image.convert('RGBA'),sprite,path,dark,footprint=case['expected']['footprint'])
                assets.append({'role':'placement-preview','path':str(path)})
            if case['expected'].get('fullBase'):
                path = output/f'neighbors-{index}.png'
                placement_preview(image.convert('RGBA'),sprite,path,repeats=3,footprint=case['expected']['footprint'])
                assets.append({'role':'neighbor-preview','path':str(path)})
    if case['kind'] == 'floor' and sprites:
        with Image.open(contained(result_path.parent,sprites[0]['image'],base)) as image:
            for count in (3,5):
                path = output/f'repeat-{count}.png'
                path.parent.mkdir(parents=True,exist_ok=True)
                render_floor_repeat(image.convert('RGBA'),repeats=count).save(path)
                assets.append({'role':f'repeat-{count}', 'path':str(path)})
    template = {'policy':POLICY, 'reviewerType':'llm', 'reviewer':'', 'independent':True,
                'spriteSHA256':{s['id']:hashlib.sha256(contained(result_path.parent,s['image'],base).read_bytes()).hexdigest() for s in sprites},
                'sourceSHA256':{s['image']:hashlib.sha256(contained(base,s['image']).read_bytes()).hexdigest() for s in submission['sources']},
                'resultSHA256':hashlib.sha256(result_path.read_bytes()).hexdigest(),
                'guideSHA256':hashlib.sha256(guide.read_bytes()).hexdigest(),
                'checks':{key:{'pass':None,'note':'','evidence':[]} for key in case['visualChecks']}}
    geometry_keys = ('kind','projection','cellSize','heightAxis','elevationScale','groundAnchorAlignment',
                     'fps','frameOrder','supportCells','overheadCells','centerCellWalkable',
                     'supportElevationBakedIntoArt')
    sprite_keys = ('id','image','size','anchor','footprint','occupiedCells','elevationPx','index',
                   'durationMs','direction','role','supportElevationPx','supportElevationBakedIntoArt','drawOrder')
    registration = {k:result[k] for k in geometry_keys if k in result}
    for key in ('sprites','depthPieces'):
        registration[key] = [{k:s[k] for k in sprite_keys if k in s} for s in result.get(key,[])]
    packet = {'policy':POLICY, 'caseId':case_id, 'request':submission['userPrompt'],
              'criteria':case['visualChecks'], 'registration':registration,'operations':operations,
              'guide':str(guide), 'assets':list({(a['role'],a['path']):a for a in assets}.values()),
              'instructions':str(Path(__file__).resolve().parents[1]/'references/visual-review.md')}
    if result.get('workflow')=='authored-periodic-material-flow':
        design=result.get('animationDesign',{})
        processor=run_root/'skill-snapshot/scripts/material_flow.py'
        packet['animationOperations']={'authorship':'authored-periodic-texture-translation',
            'source':'one generated appearance material',
            'parameters':{k:design[k] for k in ('translationPerCycleNormalized','periodFrames','stationaryEdgeBlendPx',
                'strength','boundaryReferencePhase','durationMs') if type(design.get(k)) in (int,float)},
            'translationAxis':'x',
            'processor':str(processor),'processorSHA256':hashlib.sha256(processor.read_bytes()).hexdigest()}
    write_json(output/'packet.json',packet)
    write_json(output/'review-template.json',template)
    return packet


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root',type=Path,required=True)
    parser.add_argument('--case',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    packet = prepare_review(args.run_root,args.case,args.output)
    print(json.dumps({'caseId':args.case,'packet':str(args.output/'packet.json'),'images':len(packet['assets'])}))
