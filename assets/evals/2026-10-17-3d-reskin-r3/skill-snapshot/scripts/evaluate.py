#!/usr/bin/env python3
"""Grade portable eval deliveries; visual quality requires an independent review."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image
from tile_tools import load_rgba, neighbor_coverage, parallel_edges, render_floor_repeat, write_json

SUITE = Path(__file__).resolve().parents[1] / 'evals/cases.json'
POLICY = 'llm-visual-v1'


def contained(base, name, bundle_root=None):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError('Artifact paths must be relative to their bundle file')
    path = (base / name).resolve()
    boundary = (bundle_root or base).resolve()
    if boundary not in path.parents or not path.is_file():
        raise ValueError(f'Missing or escaped artifact: {name}')
    return path


def seam_delta(image):
    image = image.convert('RGB')
    w, h = image.size
    horizontal = sum(abs(image.getpixel((0,y))[c]-image.getpixel((w-1,y))[c])
                     for y in range(h) for c in range(3)) / (h*3)
    vertical = sum(abs(image.getpixel((x,0))[c]-image.getpixel((x,h-1))[c])
                   for x in range(w) for c in range(3)) / (w*3)
    return {'horizontal': horizontal, 'vertical': vertical}


def evaluate(case, submission_path, review_path=None, output_path=None, run_root=None):
    submission_path = Path(submission_path).resolve()
    base = submission_path.parent
    checks, visual, diagnostics, artifacts = [], [], [], {}
    def check(name, passed, detail):
        checks.append({'check': name, 'pass': bool(passed), 'detail': detail})
    def diagnostic(name, detail):
        diagnostics.append({'check':name, 'detail':detail, 'gating':False})
    source_hashes = {}
    try:
        submission = json.loads(submission_path.read_text())
        if run_root is None:
            raise ValueError('Provide the independently selected prepared run root')
        run_root = Path(run_root).resolve()
        run = json.loads((run_root/'run.json').read_text())
        suite_path = contained(run_root, run['suite'])
        if hashlib.sha256(suite_path.read_bytes()).hexdigest() != run['suiteSHA256']:
            raise ValueError('Frozen eval suite was modified')
        frozen = next(c for c in json.loads(suite_path.read_text())['cases'] if c['id']==case['id'])
        if frozen != case:
            raise ValueError('Grading case differs from frozen run contract')
        trial = next(t for t in run['trials'] if t['caseId']==case['id'])
        requested_directory = (run_root/case['outputSubdir']).resolve()
        expected_prompt = case['prompt'].replace('{{OUTPUT_DIR}}', str(requested_directory))
        request = contained(run_root, trial['requestFile']).read_text().rstrip('\n')
        if request != expected_prompt or trial['outputDirectory'] != str(requested_directory):
            raise ValueError('Prepared request/destination was modified')
        check('requested-output-location', base == requested_directory and
              submission.get('outputDirectory') == str(requested_directory), str(requested_directory))
        check('case-and-request', submission.get('caseId') == case['id'] and
              submission.get('userPrompt') == expected_prompt, submission.get('userPrompt'))
        records = submission.get('sources', [])
        check('generation-sources', len(records) >= (2 if case['kind'] == 'layered' else 1), len(records))
        for i, record in enumerate(records):
            role = record.get('role', 'whole-asset')
            material = role == 'appearance-material'
            check(f'source-{i}-role', role in ('whole-asset','appearance-material'), role)
            source = contained(base, record['image'])
            recipe_path = contained(base, record['recipe'])
            recipe = json.loads(recipe_path.read_text())
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            source_hashes[record['image']] = digest
            check(f'source-{i}-unchanged', recipe.get('sourceSHA256') == digest, digest)
            check(f'source-{i}-actual-prompt', bool(recipe.get('prompt', '').strip()), 'Expanded submitted prompt')
            refs = recipe.get('references', [])
            hashes = recipe.get('referenceSHA256', {})
            roles = recipe.get('referenceRoles', {})
            reference_hashes_match = set(hashes) == set(refs)
            for reference in refs:
                path = contained(recipe_path.parent, reference, base)
                if base not in path.parents:
                    raise ValueError('References must travel with the output bundle')
                reference_hashes_match &= hashes.get(reference) == hashlib.sha256(path.read_bytes()).hexdigest()
            check(f'source-{i}-references', bool(refs) or material, refs)
            check(f'source-{i}-reference-hashes', (bool(refs) or material) and reference_hashes_match, 'Every generation input raster is hashed')
            check(f'source-{i}-recipe-fields', isinstance(recipe.get('tool'),str) and bool(recipe['tool'].strip()) and
                  type(recipe.get('transparentBackground')) is bool and
                  recipe['transparentBackground'] == (case['kind'] != 'floor' and not material) and
                  set(roles) == set(refs) and all(isinstance(r,str) and r for r in roles.values()),
                  'Tool, transparency mode, and input roles recorded')
            with Image.open(source) as image:
                check(f'source-{i}-png', image.format == 'PNG', image.format)
                image.verify()
            if material:
                with Image.open(source) as image:
                    alpha = image.convert('RGBA').getchannel('A')
                    check(f'source-{i}-opaque-material', image.width == image.height and alpha.getextrema()[0] >= 250,
                          'Complete opaque square appearance material; registration comes from authored geometry')
        guide_path = contained(base, submission['guide'])
        guide = json.loads(guide_path.read_text())
        guide_digest = hashlib.sha256(guide_path.read_bytes()).hexdigest()
        check('unchanged-guide-layout', submission.get('guideSHA256') == guide_digest, guide_digest)
        check('registered-guide', guide.get('cellSize') == 128 and isinstance(guide.get('anchor'), list),
              'Declared registration exists; placement still needs independent visual review')
        result_path = contained(base, submission['result'])
        result = json.loads(result_path.read_text())
        expected = case['expected']
        check('kind-and-projection', result.get('kind') == case['kind'] and
              result.get('projection') == 'top-down-oblique-square-grid' and result.get('cellSize') == 128,
              {'kind': result.get('kind'), 'projection': result.get('projection')})
        sprites = result.get('sprites', [])
        count = expected.get('frames', len(expected.get('layers', [])) or 1)
        check('sprite-count', len(sprites) == count, len(sprites))
        ids = [s.get('id') for s in sprites]
        check('unique-sprite-ids', all(isinstance(i,str) and i for i in ids) and len(set(ids)) == len(ids), ids)
        images = []
        geometry = bool(sprites)
        for sprite in sprites:
            image_path = contained(result_path.parent, sprite['image'], base)
            if case['kind'] == 'floor':
                with Image.open(image_path) as opened:
                    image = opened.convert('RGBA')
            else:
                image = load_rgba(image_path)
            images.append(image)
            geometry &= list(image.size) == expected['size'] and sprite.get('size') == expected['size']
            geometry &= sprite.get('anchor') == expected['anchor'] and sprite.get('footprint') == expected['footprint']
            geometry &= sprite.get('occupiedCells') == expected['occupiedCells']
            tolerance = expected.get('elevationTolerancePx', 0)
            elevation = expected.get('layerElevationPx', {}).get(sprite.get('role'), expected['elevationPx'])
            geometry &= abs(sprite.get('elevationPx', -10000) - elevation) <= tolerance
            if case['kind'] != 'floor':
                alpha = image.getchannel('A')
                border = [alpha.crop(rect).getextrema()[1] for rect in
                          [(0,0,image.width,1),(0,image.height-1,image.width,image.height),
                           (0,0,1,image.height),(image.width-1,0,image.width,image.height)]]
                diagnostic(f"{sprite['id']}-frame-margin", {'edgeAlphaMax':max(border),
                           'note':'Inspect complete art visually; edge alpha alone does not establish clipping.'})
            if expected.get('fullBase'):
                try:
                    anchor = expected['anchor']
                    coverage, _ = neighbor_coverage(image, (anchor[0], anchor[1]+expected['footprint'][1]/2),
                                                    pitch=tuple(expected['footprint']), min_alpha=expected['minimumAlpha'])
                    sides = parallel_edges(image)
                    diagnostic(f"{sprite['id']}-solid-coverage", {'coverage': coverage, 'sideSpans': sides})
                    if case['kind'] == 'object':
                        body = sides['bodyRect']
                        observed = body[3]-body[1]-expected['footprint'][1]
                        diagnostic(f"{sprite['id']}-visible-elevation", {'observedPx':observed,
                                   'requestedPx':expected['elevationPx']})
                except (ValueError, TypeError, KeyError) as exc:
                    diagnostic(f"{sprite['id']}-solid-coverage", {'unavailable':str(exc)})
            if 'groundClearancePx' in expected:
                box = image.getchannel('A').point(lambda a: 255 if a >= 64 else 0).getbbox()
                observed = expected['anchor'][1]-box[3] if box else -10000
                diagnostic('floating-clearance', {'observedPx':observed,'requestedPx':expected['groundClearancePx']})
        check('declared-geometry', geometry, 'Size, center anchor, occupancy and declared elevation; metadata does not prove visual geometry')
        if case['kind'] == 'floor' and images:
            image = images[0]
            check('opaque-floor', image.getchannel('A').getextrema()[0] >= expected['minimumAlpha'], 'Complete opaque square')
            delta = seam_delta(image)
            diagnostic('opposite-edge-continuity', {**delta,
                       'note':'RGB deltas do not determine visible seams; inspect repeated neighbors.'})
            if output_path:
                previews = Path(output_path).parent / (Path(output_path).stem+'-previews')
                previews.mkdir(parents=True, exist_ok=True)
                for columns in case.get('repeat', [3]):
                    path = previews/f'repeat-{columns}.png'
                    render_floor_repeat(image, repeats=columns).save(path)
                    artifacts[f'repeat-{columns}'] = str(path)
        if case['kind'] in ('animation', 'directions'):
            check('frame-order', [s.get('index') for s in sprites] == list(range(count)), 'Explicit frame order')
        if case['kind'] == 'animation':
            check('12-fps-schedule', result.get('fps') == 12 and
                  all(abs(s.get('durationMs',0)-1000/12) < .001 for s in sprites), '12 fps / 83.333333 ms')
        if case['kind'] == 'directions':
            check('eight-directions', [s.get('direction') for s in sprites] == expected['directions'], expected['directions'])
            heights = [i.getchannel('A').point(lambda a: 255 if a >= 64 else 0).getbbox() for i in images]
            if heights and all(heights):
                heights = [b[3]-b[1] for b in heights]
                diagnostic('upright-bounds', {'alphaHeights':heights,
                           'note':'Pose and toe length change bounds; judge anatomy scale and support visually.'})
        if 'supportCells' in expected:
            check('ground-support-cells', result.get('supportCells') == expected['supportCells'], result.get('supportCells'))
        if expected.get('depthPiecesRequired'):
            pieces = result.get('depthPieces', [])
            piece_hashes = {}
            piece_ids = [p.get('id') for p in pieces]
            orders = [p.get('drawOrder') for p in pieces]
            registered = len(pieces)>=2 and all(isinstance(i,str) and i for i in piece_ids) and len(set(piece_ids))==len(piece_ids)
            registered &= not set(piece_ids).intersection(ids) and all(type(o) is int for o in orders) and len(set(orders))==len(orders)
            for piece in pieces:
                path = contained(result_path.parent, piece['image'], base)
                image = load_rgba(path)
                registered &= list(image.size)==piece.get('size')==expected['size'] and piece.get('anchor')==expected['anchor']
                piece_hashes[piece['id']] = hashlib.sha256(path.read_bytes()).hexdigest()
            registered &= len(set(piece_hashes.values()))==len(pieces)
            check('authored-depth-pieces', registered and result.get('overheadCells') == expected['overheadCells'],
                  'Registered independent depth pieces; passage correctness needs visual review')
            artifacts['depthPieceSHA256'] = piece_hashes
        if case['kind'] == 'layered':
            check('separate-layer-roles', [s.get('role') for s in sprites] == expected['layers'], expected['layers'])
            character = next((s for s in sprites if s.get('role') == 'character'), {})
            check('support-elevation-once', character.get('supportElevationPx') == expected['supportElevationPx'] and
                  character.get('supportElevationBakedIntoArt') is True, character.get('supportElevationPx'))
        # A review is tied to these actual processed images, not a self-declared result.
        image_hashes = {s['id']: hashlib.sha256(contained(result_path.parent,s['image'],base).read_bytes()).hexdigest()
                        for s in sprites}
        image_hashes.update(artifacts.get('depthPieceSHA256',{}))
        result_digest = hashlib.sha256(result_path.read_bytes()).hexdigest()
    except (OSError, ValueError, TypeError, KeyError, ZeroDivisionError, StopIteration) as exc:
        check('artifact-integrity', False, str(exc))
        image_hashes = {}
        result_digest = guide_digest = None
    if review_path:
        try:
            review = json.loads(Path(review_path).read_text())
            visual.append({'check':'independent-current-artifacts','pass':review.get('independent') is True and
                           review.get('policy') == POLICY and review.get('reviewerType') == 'llm' and
                           bool(review.get('reviewer')) and review.get('spriteSHA256') == image_hashes and
                           review.get('sourceSHA256') == source_hashes and
                           review.get('resultSHA256') == result_digest and review.get('guideSHA256') == guide_digest,
                           'detail':'Independent LLM identity, grading policy and hashes of originals, sprites, registration and result metadata'})
            for key, description in case['visualChecks'].items():
                entry = review.get('checks',{}).get(key,{})
                evidence = entry.get('evidence')
                supported = bool(entry.get('note')) and isinstance(evidence,list) and bool(evidence) and all(isinstance(p,str) and p for p in evidence)
                verdict = entry.get('pass') if type(entry.get('pass')) is bool and supported else None
                visual.append({'check':key,'pass':verdict,'detail':entry.get('note') or description,
                               'evidence':evidence or []})
            for key, values in review.get('measurements',{}).items():
                diagnostic(key, values)
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            visual.append({'check':'independent-review','pass':None,'detail':str(exc)})
    automatic_pass = bool(checks) and all(c['pass'] for c in checks)
    status = ('failed' if not automatic_pass or any(c['pass'] is False for c in visual)
              else 'passed' if visual and all(c['pass'] is True for c in visual) else 'needs-visual-review')
    report = {'version':3,'policy':POLICY,'caseId':case['id'],'status':status,'automaticChecks':checks,
              'visualChecks':visual,'diagnostics':diagnostics,'reviewArtifacts':artifacts,
              'reviewer':review.get('reviewer') if review_path and 'review' in locals() else None,
              'scope':'Delivery integrity plus qualitative LLM visual review. Image metrics are non-gating diagnostics; no new artwork is generated.'}
    if output_path:
        write_json(output_path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, default=SUITE)
    parser.add_argument('--case', required=True)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--submission', type=Path, required=True)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    case = next((c for c in json.loads(args.cases.read_text())['cases'] if c['id'] == args.case), None)
    if case is None:
        parser.error('Unknown case')
    report = evaluate(case, args.submission, args.review, args.output, args.run_root)
    print(json.dumps({'case':args.case,'status':report['status'],'report':str(args.output)},indent=2))
    raise SystemExit({'passed':0,'failed':1,'needs-visual-review':2}[report['status']])


if __name__ == '__main__':
    main()
