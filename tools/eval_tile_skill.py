#!/usr/bin/env python3
"""Grade fresh skill outputs or replay saved artifacts; visual review is independent."""
import argparse
import colorsys
import hashlib
import json
from pathlib import Path
from PIL import Image
from tilekit import (load_rgba,prepare_floor_material,process_object_sheet,
                     render_floor_repeat,render_anchored_frames,write_json)

ROOT=Path(__file__).resolve().parents[1]
CASES=ROOT/'skills/build-overlap-tiles/evals/cases.json'


def reserved_hue_residual(image,chroma):
    """Count clearly visible key-hue pixels, without mistaking a hand for a floor."""
    kh=colorsys.rgb_to_hsv(*(c/255 for c in chroma['keyRGB']))[0]
    count=0;left,top,right,bottom=chroma['region']
    for y in range(top,bottom):
        for x in range(left,right):
            r,g,b,a=image.getpixel((x,y))
            if a<64:continue
            h,s,_=colorsys.rgb_to_hsv(r/255,g/255,b/255)
            distance=abs(h-kh)*360;distance=min(distance,360-distance)
            if distance<18 and s>.2:count+=1
    return count


def evaluate(case,submission_path,review_path=None,output_path=None):
    submission_path=Path(submission_path);base=submission_path.parent
    checks=[];artifacts={};submission={}
    def check(name,passed,detail):
        checks.append({'check':name,'pass':bool(passed),'detail':detail})
    def read(path):return json.loads(Path(path).read_text())
    try:
        submission=read(submission_path)
        check('case-and-user-prompt',submission.get('caseId')==case['id'] and submission.get('userPrompt')==case['prompt'],submission.get('userPrompt'))
        source=base/submission['source'];recipe_path=base/submission['generationRecipe']
        recipe=read(recipe_path);source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
        check('unchanged-generated-source',source_hash==recipe.get('sourceSHA256'),source_hash)
        check('actual-expanded-prompt',isinstance(recipe.get('prompt'),str) and bool(recipe['prompt'].strip()),'Exact nonempty prompt retained')
        refs=recipe.get('references',[])
        reference_paths=[recipe_path.parent/r for r in refs]
        check('sole-preserved-reference',len(refs)==1 and all(p.is_file() for p in reference_paths),refs)
        guide=read(base/submission['guide']);result_path=base/submission['result'];result=read(result_path)
        check('result-kind',result.get('kind')==case['kind'],result.get('kind'))
        expected=case['expected']
        with Image.open(source) as opened:raw=opened.convert('RGBA')
        preview_dir=Path(output_path).parent/(Path(output_path).stem+'-review') if output_path else None
        if preview_dir:preview_dir.mkdir(parents=True,exist_ok=True)
        if case['kind']=='floor':
            image=load_rgba(result_path.parent/result['image'])
            check('runtime-ground-geometry',list(image.size)==expected['size'] and result.get('size')==expected['size'] and result.get('anchor')==expected['anchor'] and result.get('footprint')==expected['footprint'],{'size':list(image.size),'anchor':result.get('anchor')})
            check('opaque-full-ground-square',image.getchannel('A').getextrema()[0]>=expected['minimumAlpha'],image.getchannel('A').getextrema())
            replay,meta=prepare_floor_material(raw)
            check('complete-material-without-crop',image.tobytes()==replay.tobytes() and result.get('sourceSize')==meta['sourceSize'] and guide.get('kind')=='floor','Reproduces uniform resampling of the untouched complete square')
            check('opaque-generation-mode',recipe.get('transparentBackground') is False,recipe.get('transparentBackground'))
            if preview_dir:
                path=preview_dir/'repeat.png';render_floor_repeat(image).save(path);artifacts['repeat']=str(path)
        else:
            frames=result.get('frames',[])
            check('six-frames-in-guide-order',len(frames)==expected['frames'] and [f.get('index') for f in frames]==list(range(expected['frames'])),len(frames))
            check('declared-sheet-and-timing',result.get('sheet',{}).get('columns')==expected['columns'] and result.get('sheet',{}).get('rows')==expected['rows'] and all(abs(f.get('durationMs',0)-expected['durationMs'])<.01 for f in frames),result.get('sheet'))
            check('center-ground-placement',result.get('groundAnchorAlignment')=='center' and result.get('cellSize')==128,result.get('groundAnchorAlignment'))
            threshold=frames[0]['cleanup']['minAlpha']
            drift=result.get('panelIsolation')=='transparent-separators'
            replay=process_object_sheet(raw,guide,threshold,drift)
            check('source-gutters-isolated',True,'Source cuts use strict panels or fully transparent separator lines; no cleaned art is clipped')
            outputs=[];geometry=True;calibration=True;residuals=[]
            for frame,(replayed,measured) in zip(frames,replay):
                image=load_rgba(result_path.parent/frame['image']);outputs.append(image)
                geometry &= list(image.size)==expected['size'] and frame.get('size')==expected['size'] and frame.get('anchor')==expected['anchor'] and frame.get('footprint')==expected['footprint']
                calibration &= frame.get('floor')==measured['floor'] and frame.get('normalization')==measured['normalization'] and frame.get('sourceRect')==measured['sourceRect'] and image.tobytes()==replayed.tobytes()
                residuals.append(reserved_hue_residual(image,frame['chroma']))
            check('full-frames-and-fixed-anchors',geometry,'Every frame retains 192x320, footprint128, and anchor96,248')
            check('floor-derived-scale-and-position',calibration,'Independent source replay matches measured floor, normalization, panel cuts, and output pixels; no foot fitting')
            check('reserved-floor-hue-removed',all(n==0 for n in residuals),{'strongKeyHuePixelsPerFrame':residuals,'note':'Non-key hands/shoes at floor corners are preserved; pale spill is reviewed visually'})
            check('explicit-recorded-key',all(f.get('chroma',{}).get('keyRGB')==guide['keyRGB'] for f in frames),guide.get('keyRGB'))
            check('transparent-generation-mode',recipe.get('transparentBackground') is True,recipe.get('transparentBackground'))
            sheet=load_rgba(result_path.parent/result['sheet']['image'])
            sheet_ok=list(sheet.size)==[expected['columns']*192,expected['rows']*320]
            for i,image in enumerate(outputs):
                x=(i%expected['columns'])*192;y=(i//expected['columns'])*320
                sheet_ok &= sheet.crop((x,y,x+192,y+320)).tobytes()==image.tobytes()
            check('sheet-reconstructs-every-frame',sheet_ok,'No trim drift or overlapping frames')
            if preview_dir:
                for dark in (False,True):
                    label='dark' if dark else 'light';views,strip=render_anchored_frames(outputs,dark=dark)
                    strip_path=preview_dir/f'anchored-{label}.png';strip.save(strip_path)
                    gif_path=preview_dir/f'dance-{label}.gif'
                    views[0].convert('RGB').save(gif_path,save_all=True,append_images=[v.convert('RGB') for v in views[1:]],duration=expected['durationMs'],loop=0,disposal=2)
                    artifacts[label+'Strip']=str(strip_path);artifacts[label+'Animation']=str(gif_path)
    except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:
        check('artifact-processing',False,str(exc))
    visual=[]
    if review_path:
        try:
            review=read(review_path)
            for key,description in case['visualChecks'].items():
                item=review.get('checks',{}).get(key,{})
                visual.append({'check':key,'pass':item.get('pass') is True and bool(item.get('note')),'detail':item.get('note',description)})
        except (OSError,ValueError,TypeError) as exc:
            visual.append({'check':'independent-review','pass':False,'detail':str(exc)})
    automatic_pass=bool(checks) and all(c['pass'] for c in checks)
    status='failed' if not automatic_pass or (visual and not all(c['pass'] for c in visual)) else 'passed' if visual else 'needs-visual-review'
    report={'version':1,'caseId':case['id'],'userPrompt':case['prompt'],'status':status,
        'automaticChecks':checks,'visualChecks':visual,'reviewArtifacts':artifacts,
        'scope':'One fresh behavioral trial or saved artifact replay; does not establish reliability.'}
    if output_path:write_json(output_path,report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',required=True)
    parser.add_argument('--submission',type=Path,required=True)
    parser.add_argument('--review',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    cases=json.loads(CASES.read_text())['cases'];case=next((c for c in cases if c['id']==args.case),None)
    if case is None:parser.error('Unknown case')
    report=evaluate(case,args.submission,args.review,args.output)
    print(json.dumps({'case':args.case,'status':report['status'],'failed':[c for c in report['automaticChecks']+report['visualChecks'] if not c['pass']],'report':str(args.output)},indent=2))
    raise SystemExit({'passed':0,'failed':1,'needs-visual-review':2}[report['status']])


if __name__=='__main__':main()
