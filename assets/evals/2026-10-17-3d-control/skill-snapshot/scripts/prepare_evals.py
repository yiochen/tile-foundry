#!/usr/bin/env python3
"""Freeze eval requests and the skill in a caller-selected workspace; generate no art."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

SKILL_DIR = Path(__file__).resolve().parents[1]
SUITE = SKILL_DIR / 'evals/cases.json'


def prepare(run_root, cases_path=SUITE, selected=None):
    run_root = Path(run_root).resolve()
    if run_root == SKILL_DIR or SKILL_DIR in run_root.parents:
        raise ValueError('Choose an output workspace outside the skill bundle')
    if run_root.exists() and any(run_root.iterdir()):
        raise ValueError('Run destination must be empty; never replace an earlier run')
    suite = json.loads(Path(cases_path).read_text())
    cases = [c for c in suite['cases'] if selected is None or c['id'] in selected]
    if selected and set(selected) != {c['id'] for c in cases}:
        raise ValueError('Unknown case selection')
    if not cases:
        raise ValueError('Select at least one case')
    directories = [(run_root / c['outputSubdir']).resolve() for c in cases]
    if any(run_root not in d.parents for d in directories) or len(set(directories)) != len(directories):
        raise ValueError('Case destinations must be distinct directories inside the run workspace')
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / 'suite.json').write_text(json.dumps(suite, indent=2) + '\n')
    snapshot = run_root / 'skill-snapshot'
    # Runtime packages are installed separately; freezing their binaries would
    # make a portable reference renderer's snapshot machine-specific and huge.
    shutil.copytree(SKILL_DIR, snapshot, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'node_modules'))
    trials = []
    for case in cases:
        directory = run_root / case['outputSubdir']
        directory.mkdir()
        prompt = case['prompt'].replace('{{OUTPUT_DIR}}', str(directory))
        (directory / 'request.txt').write_text(prompt + '\n')
        trials.append({'caseId': case['id'], 'status': 'not-run',
                       'outputDirectory': str(directory),
                       'requestFile': f"{case['outputSubdir']}/request.txt"})
    record = {'version': 2, 'mode': 'prepared-not-run', 'suite': 'suite.json',
              'suiteSHA256': hashlib.sha256((run_root / 'suite.json').read_bytes()).hexdigest(),
              'skillSnapshot': 'skill-snapshot/SKILL.md',
              'skillFiles': {p.relative_to(snapshot).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in sorted(snapshot.rglob('*')) if p.is_file()},
              'trials': trials}
    (run_root / 'run.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--cases', type=Path, default=SUITE)
    parser.add_argument('--case', action='append')
    args = parser.parse_args()
    record = prepare(args.run_root, args.cases, args.case)
    print(json.dumps({'mode': record['mode'], 'cases': len(record['trials']),
                      'run': str(args.run_root.resolve() / 'run.json')}, indent=2))


if __name__ == '__main__':
    main()
