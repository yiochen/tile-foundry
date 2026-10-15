#!/usr/bin/env python3
"""Publish recorded evals, keeping frozen rubrics and unrun cases distinct."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
from eval_preview_sequences import source_sequence

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(Path(path).read_text())


def within(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    if root not in path.parents:
        raise ValueError(f'Eval artifact escapes its bundle: {path}')
    return path


def case_key(case):
    return hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest()


def build_gallery(runs_root, suite_path, public, reports_root, include_archived=False):
    runs_root, public, reports_root = map(Path, (runs_root, public, reports_root))
    suite = read_json(suite_path)
    current, archived = {}, {}
    def entry(case, version, current_case):
        return {**case, 'key':('current:' if current_case else 'archive:')+case_key(case)[:12],
                'title':case['id'].replace('-', ' ').capitalize(),
                'suiteVersion':version, 'current':current_case, 'latest':None, 'trials':[]}
    for case in suite['cases']:
        current[case_key(case)] = entry(case, suite['version'], True)
    runs = []
    for path in runs_root.glob('*/run.json'):
        record = read_json(path)
        runs.append((str(record.get('createdAt') or record.get('id') or path.parent.name), path, record))
    for _, run_path, record in sorted(runs, key=lambda r:(r[0],r[1].parent.name)):
        run = run_path.parent.resolve()
        run_id = run.name
        if not re.fullmatch(r'[\w.-]+', run_id):
            raise ValueError('Run directory name must be suitable for a static URL')
        frozen = read_json(within(run/record.get('suite','cases.json'),run))
        cases = {c['id']:c for c in frozen['cases']}
        for order, trial in enumerate(record['trials']):
            case = cases[trial['caseId']]
            fingerprint = case_key(case)
            target = current.get(fingerprint)
            if target is None:
                if not include_archived:
                    continue
                target = archived.setdefault(fingerprint, entry(case,frozen['version'],False))
            relative = trial.get('directory') or case.get('outputSubdir',case['id'])
            directory = within(run/relative,run)
            prefix = f'evals/{run_id}/{relative}'
            def publish(path, boundary=directory, suffix=None):
                path = within(path, boundary)
                if not path.is_file():
                    raise ValueError(f'Missing declared eval artifact: {path}')
                name = suffix or path.relative_to(boundary.resolve()).as_posix()
                url = f'{prefix}/{name}'
                destination = within(public/url,public)
                destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,destination)
                return url
            submission_path = directory/'submission.json'
            submission = read_json(submission_path) if submission_path.exists() else None
            report_name = trial.get('report',case['id']+'.json')
            report_candidates = [within(run/report_name,run), within(run/'reports'/report_name,run)]
            if frozen['version'] == 1:
                report_candidates.append(within(reports_root/run_id/report_name,reports_root/run_id))
            report_path = next((p for p in report_candidates if p.is_file()),None)
            report = read_json(report_path) if report_path else None
            status = report['status'] if report else trial.get('status')
            if submission and status in (None,'not-run'):
                status = 'ungraded'
            status = status or 'not-run'
            item = {'id':f'{run_id}:{relative}', 'runId':run_id, 'attempt':order+1,
                    'assessmentLabel':'Original grading',
                    'status':status, 'prompt':case['prompt'], 'sources':[], 'sprites':[],
                    'depthPieces':[], 'previews':[], 'automaticChecks':[], 'visualChecks':[]}
            if submission:
                if submission['caseId'] != case['id']:
                    raise ValueError('Submission is registered to a different eval case')
                item['prompt'] = submission['userPrompt']
                item['submission'] = publish(submission_path)
                sources = submission.get('sources') or [{'image':submission['source'],
                                                         'recipe':submission['generationRecipe']}]
                for source in sources:
                    recipe_path = within(directory/source['recipe'],directory)
                    recipe = read_json(recipe_path)
                    item['sources'].append({'image':publish(directory/source['image']),
                        'recipe':publish(recipe_path),'prompt':recipe['prompt'],
                        'role':source.get('role','whole-asset'),
                        'references':[{'image':publish(recipe_path.parent/name),
                                       'role':recipe.get('referenceRoles',{}).get(name,'reference')}
                                      for name in recipe.get('references',[])]})
                guide = within(directory/submission['guide'],directory)
                item['guide'] = publish(guide)
                guide_image = next((p for p in [guide.with_suffix('.png'), directory/'guide.png'] if p.is_file()),None)
                if guide_image:
                    item['guideImage'] = publish(guide_image)
                layout = read_json(guide)
                svg = guide.with_suffix('.svg')
                size, anchor = layout.get('size'), layout.get('anchor')
                cells = layout.get('cells',[])
                # Only a complete single-frame guide has an unambiguous 1:1
                # overlay. Never fit a source sheet or infer a transform from art.
                if (svg.is_file() and layout.get('kind') == 'object-sheet' and
                    layout.get('cellSize') == 128 and size == layout.get('frame') and
                    isinstance(size,list) and len(size)==2 and
                    isinstance(anchor,list) and len(anchor)==2 and len(cells)==1 and
                    cells[0].get('rect') == [0,0,*size]):
                    subject = layout.get('subjectRegistration',{})
                    item['guideOverlay'] = {'image':publish(svg),'size':size,'anchor':anchor,
                        'heightPx':subject.get('height'),'baseSize':subject.get('baseSize')}
                for name in submission.get('previews',[]):
                    if Path(name).suffix.lower() not in ('.png','.jpg','.jpeg','.webp','.gif','.svg'):
                        continue
                    item['previews'].append({'label':Path(name).stem.replace('-',' '),
                                             'image':publish(directory/name)})
                result_path = within(directory/submission.get('result','result.json'),directory)
                result = read_json(result_path) if result_path.is_file() else {}
                if result:
                    item['result'] = publish(result_path)
                diagnostic = submission.get('diagnostic') or (result.get('processing') if isinstance(result.get('processing'),str) else None)
                if diagnostic and (directory/diagnostic).is_file():
                    item['processing'] = publish(directory/diagnostic)
                elif (directory/'processing-diagnostic.json').is_file():
                    item['processing'] = publish(directory/'processing-diagnostic.json')
                item['kind'] = result.get('kind',case['kind'])
                item['anchorAlignment'] = result.get('groundAnchorAlignment','center')
                for index,sprite in enumerate(result.get('sprites') or result.get('frames') or ([result] if result.get('image') else [])):
                    item['sprites'].append({**{k:v for k,v in sprite.items() if k in
                        ('id','index','size','anchor','footprint','occupiedCells','elevationPx','durationMs','direction','role')},
                        'id':sprite.get('id',f'sprite-{index}'), 'image':publish(result_path.parent/sprite['image'])})
                sheet = result.get('sheet')
                if sheet:
                    item['sheet'] = publish(result_path.parent/(sheet['image'] if isinstance(sheet,dict) else sheet))
                for piece in result.get('depthPieces',[]):
                    item['depthPieces'].append({**piece,'image':publish(result_path.parent/piece['image'])})
                if not item['sprites'] and (case['kind']=='animation' or len(sources)>1):
                    try:
                        item['previewSequence'] = source_sequence(directory,submission,layout,publish)
                    except ValueError as exc:
                        item['previewUnavailable'] = str(exc)
            if report:
                item['report'] = publish(report_path,report_path.parent,'report.json')
                item['automaticChecks'] = report.get('automaticChecks',[])
                item['visualChecks'] = report.get('visualChecks',[])
                item['diagnostics'] = report.get('diagnostics',[])
                item['policy'] = report.get('policy')
                item['reviewer'] = report.get('reviewer')
                item['scope'] = report.get('scope','')
                for label,name in report.get('reviewArtifacts',{}).items():
                    if not isinstance(name,str):
                        continue  # Hash maps are evidence, not image paths.
                    path = Path(name)
                    if not path.is_absolute():
                        path = report_path.parent/path
                    if not path.is_file() or report_path.parent.resolve() not in path.resolve().parents:
                        # Old reports retain the original checkout's absolute paths.
                        path = report_path.parent/Path(*Path(name).parts[-2:])
                    if path.is_file():
                        item['previews'].append({'label':label,'image':publish(path,report_path.parent,
                                                'review/'+path.name)})
            if trial.get('reason'):
                item['reason'] = trial['reason']
            item['previews'] = list({p['image']:p for p in item['previews']}.values())
            target['trials'].append(item)
            # A prepared-but-unrun later run does not hide the last actual result.
            if status != 'not-run':
                target['latest'] = item
            # A re-assessment uses the same art but preserves separate policy/review/report records.
            for assessment in sorted(record.get('assessments',[]),key=lambda a:(a['createdAt'],a['id'])):
                assessment_trial = assessment.get('cases',{}).get(case['id'])
                if not assessment_trial:
                    continue
                assessment_root = within(run/assessment['directory'],run)
                new_report_path = within(assessment_root/assessment_trial['report'],assessment_root)
                new_report = read_json(new_report_path)
                revised = copy.deepcopy(item)
                revised.update(id=item['id']+'@'+assessment['id'],
                    assessmentId=assessment['id'],assessmentLabel=assessment['label'],
                    assessedAt=assessment['createdAt'],status=new_report['status'],
                    policy=new_report['policy'],reviewer=new_report.get('reviewer'),
                    reason=assessment_trial.get('reason',''),
                    automaticChecks=new_report.get('automaticChecks',[]),
                    visualChecks=new_report.get('visualChecks',[]),
                    diagnostics=new_report.get('diagnostics',[]),scope=new_report.get('scope',''))
                suffix = 'assessments/'+assessment['id']+'/'
                revised['report'] = publish(new_report_path,assessment_root,suffix+'report.json')
                revised['review'] = publish(assessment_root/assessment_trial['review'],assessment_root,suffix+'review.json')
                revised['policyRecord'] = publish(assessment_root/'policy.json',assessment_root,suffix+'policy.json')
                if assessment_trial.get('packet'):
                    packet = read_json(within(assessment_root/assessment_trial['packet'],assessment_root))
                    revised['previews'] = []
                    for asset in packet['assets']:
                        if asset['role'] not in ('placement-preview','neighbor-preview','repeat-3','repeat-5'):
                            continue
                        path = within(asset['path'],assessment_root)
                        revised['previews'].append({'label':Path(path).stem.replace('-',' '),
                            'image':publish(path,assessment_root,suffix+path.name)})
                target['trials'].append(revised)
                target['latest'] = revised
    gallery = {'version':1,'suiteVersion':suite['version'], 'cases':list(current.values()),
               'archivedCases':list(archived.values()),
               'ordering':'Runs ordered by createdAt; each generation retains original grading and separately dated assessments.'}
    public.mkdir(parents=True,exist_ok=True)
    (public/'eval-gallery.json').write_text(json.dumps(gallery,indent=2)+'\n')
    return gallery


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs-root',type=Path,default=ROOT/'assets/evals')
    parser.add_argument('--suite',type=Path,default=ROOT/'skills/build-overlap-tiles/evals/cases.json')
    parser.add_argument('--public',type=Path,default=ROOT/'public/assets')
    parser.add_argument('--reports-root',type=Path,default=ROOT/'docs/evals')
    parser.add_argument('--include-archived',action='store_true')
    args = parser.parse_args()
    result = build_gallery(args.runs_root,args.suite,args.public,args.reports_root,args.include_archived)
    print(json.dumps({'cases':len(result['cases']),'recordedCurrentCases':sum(c['latest'] is not None for c in result['cases']),
                      'archivedCases':len(result['archivedCases'])}))


if __name__ == '__main__':
    main()
