#!/usr/bin/env python3
"""Replay preserved skill-eval artifacts. Fresh agent generation follows the protocol."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,default=ROOT/'assets/evals/2026-10-11-skill-v2')
    parser.add_argument('--assessment',default='latest',help='latest, original, or a recorded assessment ID')
    args=parser.parse_args();run=args.run.resolve();record=json.loads((run/'run.json').read_text())
    portable=record.get('version')==2
    assessment = None
    if portable:
        import sys
        if args.assessment != 'original' and record.get('assessments'):
            assessments = sorted(record['assessments'],key=lambda a:(a['createdAt'],a['id']))
            assessment = assessments[-1] if args.assessment == 'latest' else next((a for a in assessments if a['id']==args.assessment),None)
            if assessment is None:
                parser.error('Unknown assessment ID')
        elif args.assessment not in ('original','latest'):
            parser.error('Unknown assessment ID')
        snapshot = run/'skill-snapshot'
        if assessment:
            assessment_root = (run/assessment['directory']).resolve()
            if run not in assessment_root.parents:
                parser.error('Assessment escapes run directory')
            policy = json.loads((assessment_root/'policy.json').read_text())
            snapshot = assessment_root/'grader-snapshot'
            for name,digest in policy['graderFiles'].items():
                path = (snapshot/name).resolve()
                if snapshot.resolve() not in path.parents or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                    parser.error('Assessment grader snapshot was modified')
        sys.path.insert(0,str(snapshot/'scripts'))
        spec = importlib.util.spec_from_file_location('recorded_grader',snapshot/'scripts/evaluate.py')
        module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        evaluate_portable = module.evaluate
    else:
        from eval_tile_skill import evaluate
    cases_path=run/record.get('suite','cases.json')
    cases={c['id']:c for c in json.loads(cases_path.read_text())['cases']}
    output=run/'reports' if portable else ROOT/'docs/evals'/record['id'];reports=[]
    if assessment:
        output = assessment_root/'reports'
    for trial in record['trials']:
        directory=run/trial.get('directory',cases[trial['caseId']].get('outputSubdir',trial['caseId']))
        if portable:
            grading = assessment['cases'][trial['caseId']] if assessment else trial
            review = assessment_root/grading['review'] if assessment else directory/'review.json'
            report_path = assessment_root/grading['report'] if assessment else output/trial['report']
            report=evaluate_portable(cases[trial['caseId']],directory/'submission.json',review,report_path,run)
        else:
            report=evaluate(cases[trial['caseId']],directory/'submission.json',directory/'review.json',output/trial['report'])
        expected = assessment['cases'][trial['caseId']]['expectedStatus'] if assessment else trial['expectedStatus']
        reports.append({'trial':directory.name,'caseId':trial['caseId'],'status':report['status'],
            'expectedStatus':expected,'matchesExpected':report['status']==expected})
    summary={'run':record['id'],'mode':'saved-artifact-replay','ok':all(r['matchesExpected'] for r in reports),
        'trials':reports,'scope':'Replays preserved originals and independent reviews, including failures; no new image generation or corrected attempts.'}
    if assessment:
        summary['assessment'] = assessment['id']
    output.mkdir(parents=True,exist_ok=True)
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    raise SystemExit(0 if summary['ok'] else 1)


if __name__=='__main__':main()
