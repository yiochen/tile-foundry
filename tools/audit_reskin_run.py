"""Check that every case in a reskin run has fresh AI sources and 3D provenance.

This is a provenance audit, not a visual grade or evidence of correct geometry.
It never promotes a direct render to an AI candidate or edits an eval rubric.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(base, name):
    path = (base / name).resolve()
    if base.resolve() not in path.parents:
        raise ValueError(f'Path escapes case bundle: {name}')
    return path


def audit(run_root):
    run = Path(run_root).resolve()
    record = json.loads((run / 'run.json').read_text())
    suite = json.loads((run / record['suite']).read_text())
    trials = {t['caseId']: t for t in record['trials']}
    findings = []
    for case in suite['cases']:
        case_id = case['id']
        base = inside(run, case.get('outputSubdir', case_id))
        errors = []
        sources = []
        delivered = 0
        try:
            trial = trials[case_id]
            submission = json.loads((base / 'submission.json').read_text())
            source_records = submission['sources']
            if not source_records:
                errors.append('No imagegen sources')
            for source in source_records:
                original = inside(base, source['image'])
                recipe_path = inside(base, source['recipe'])
                recipe = json.loads(recipe_path.read_text())
                tool = str(recipe.get('tool', '')).lower()
                if not any(name in tool for name in ('imagegen', 'image_gen')):
                    errors.append(f'{source["image"]}: recipe is not an imagegen call')
                if recipe.get('sourceSHA256') != digest(original):
                    errors.append(f'{source["image"]}: original hash mismatch')
                references = recipe.get('references', [])
                image_references = []
                for name in references:
                    reference = inside(base, str((recipe_path.parent / name).relative_to(base)))
                    if recipe.get('referenceSHA256', {}).get(name) != digest(reference):
                        errors.append(f'{source["image"]}: reference hash mismatch: {name}')
                    if reference.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'):
                        image_references.append(reference)
                if not image_references:
                    errors.append(f'{source["image"]}: no supplied raster geometry reference')
                if any(digest(original) == digest(ref) for ref in image_references):
                    errors.append(f'{source["image"]}: original is a reused reference')
                sources.append(original)
            calls = trial.get('generationCalls')
            if calls != len(sources) or calls == 0:
                errors.append('Recorded imagegen calls do not cover every new source')
            result_path = inside(base, submission['result'])
            result = json.loads(result_path.read_text())
            provenance = result.get('provenance', {})
            if result.get('workflow') != '3d-imagegen-reskin':
                errors.append('Final workflow is not 3D then imagegen')
            declared_sources = {inside(base, str((result_path.parent / name).relative_to(base)))
                                for name in provenance.get('reskinSources', [])}
            if declared_sources != set(sources):
                errors.append('Final/source-only result does not trace to all new AI originals')
            if provenance.get('imageGenerationCalls') != calls:
                errors.append('Result imagegen call count mismatch')
            delivered = len(result.get('sprites', [])) + len(result.get('depthPieces', []))
            for sprite in result.get('sprites', []) + result.get('depthPieces', []):
                if not inside(base, str((result_path.parent / sprite['image']).relative_to(base))).is_file():
                    errors.append(f'Missing delivered art: {sprite["id"]}')
                if sprite.get('reskinSource'):
                    traced = inside(base, str((result_path.parent / sprite['reskinSource']).relative_to(base)))
                    if traced not in sources:
                        errors.append(f'Untraced AI piece: {sprite["id"]}')
            if case['kind'] == 'layered' or case['expected'].get('depthPiecesRequired'):
                pieces = result.get('depthPieces', []) if case['expected'].get('depthPiecesRequired') else result.get('sprites', [])
                if any(not p.get('reskinSource') for p in pieces):
                    errors.append('Independent layers/depth pieces need individual AI source links')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(str(exc))
        findings.append({'caseId': case_id, 'imagegenSources': len(sources),
                         'deliveredSpritesAndPieces': delivered,
                         'freshReskinCoverage': not errors, 'errors': errors})
    total = sum(f['imagegenSources'] for f in findings)
    return {'run': run.name, 'kind': 'imagegen-coverage-audit',
            'scope': 'Source/provenance coverage only; visual quality and delivery grades are separate.',
            'cases': findings, 'actualImagegenSources': total,
            'plannedImagegenCalls': record.get('plannedGenerationCalls'),
            'ok': all(f['freshReskinCoverage'] for f in findings) and total == record.get('plannedGenerationCalls')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = audit(args.run)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['ok'] else 1)


if __name__ == '__main__':
    main()
