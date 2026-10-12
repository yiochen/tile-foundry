#!/usr/bin/env python3
"""Replay preserved skill-eval artifacts. Fresh agent generation follows the protocol."""
import argparse
import json
from pathlib import Path
from eval_tile_skill import evaluate,CASES,ROOT
from tilekit import write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,default=ROOT/'assets/evals/2026-10-11-skill-v1')
    args=parser.parse_args();run=args.run.resolve();record=json.loads((run/'run.json').read_text())
    cases_path=run/'cases.json'
    cases={c['id']:c for c in json.loads(cases_path.read_text())['cases']}
    output=ROOT/'docs/evals'/record['id'];reports=[]
    for trial in record['trials']:
        directory=run/trial['directory']
        report=evaluate(cases[trial['caseId']],directory/'submission.json',directory/'review.json',output/trial['report'])
        reports.append({'trial':trial['directory'],'caseId':trial['caseId'],'status':report['status'],
            'expectedStatus':trial['expectedStatus'],'matchesExpected':report['status']==trial['expectedStatus']})
    summary={'run':record['id'],'mode':'saved-artifact-replay','ok':all(r['matchesExpected'] for r in reports),
        'trials':reports,'scope':'Includes an intentional failed first dance attempt; fresh behavioral reruns require image generation.'}
    write_json(output/'summary.json',summary);print(json.dumps(summary,indent=2))
    raise SystemExit(0 if summary['ok'] else 1)


if __name__=='__main__':main()
