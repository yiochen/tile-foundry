#!/usr/bin/env python3
"""Replay preserved skill-eval artifacts. Fresh agent generation follows the protocol."""
import argparse
import json
from pathlib import Path
from eval_tile_skill import evaluate,ROOT
from tilekit import write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,default=ROOT/'assets/evals/2026-10-11-skill-v2')
    args=parser.parse_args();run=args.run.resolve();record=json.loads((run/'run.json').read_text())
    portable=record.get('version')==2
    if portable:
        import sys
        sys.path.insert(0,str(run/'skill-snapshot/scripts'))
        from evaluate import evaluate as evaluate_portable
    cases_path=run/record.get('suite','cases.json')
    cases={c['id']:c for c in json.loads(cases_path.read_text())['cases']}
    output=run/'reports' if portable else ROOT/'docs/evals'/record['id'];reports=[]
    for trial in record['trials']:
        directory=run/trial.get('directory',cases[trial['caseId']].get('outputSubdir',trial['caseId']))
        if portable:
            report=evaluate_portable(cases[trial['caseId']],directory/'submission.json',directory/'review.json',output/trial['report'],run)
        else:
            report=evaluate(cases[trial['caseId']],directory/'submission.json',directory/'review.json',output/trial['report'])
        reports.append({'trial':directory.name,'caseId':trial['caseId'],'status':report['status'],
            'expectedStatus':trial['expectedStatus'],'matchesExpected':report['status']==trial['expectedStatus']})
    summary={'run':record['id'],'mode':'saved-artifact-replay','ok':all(r['matchesExpected'] for r in reports),
        'trials':reports,'scope':'Replays preserved originals and independent reviews, including failures; no new image generation or corrected attempts.'}
    write_json(output/'summary.json',summary);print(json.dumps(summary,indent=2))
    raise SystemExit(0 if summary['ok'] else 1)


if __name__=='__main__':main()
