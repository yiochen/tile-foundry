"""Synthetic helper/grader tests; these do not run or pass behavioral generations."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from PIL import Image, ImageDraw

SKILL = Path(__file__).resolve().parents[1] / 'skills/build-overlap-tiles'
sys.path.insert(0, str(SKILL / 'scripts'))
from evaluate import evaluate
from prepare_evals import prepare
from guide_tools import build
from assemble_result import assemble


class PortableSkillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve()
        self.cases = {c['id']: c for c in json.loads((SKILL / 'evals/cases.json').read_text())['cases']}

    def grade(self, case, path, review_path=None, output_path=None):
        return evaluate(case, path, review_path, output_path, run_root=self.run_root)

    def digest(self, name):
        return hashlib.sha256((self.artifacts/name).read_bytes()).hexdigest()

    def test_copied_bundle_runs_outside_source_project_at_12_fps(self):
        foreign = self.directory / 'unrelated-project'
        foreign.mkdir()
        bundle = foreign / 'asset-skill'
        shutil.copytree(SKILL, bundle, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        output = foreign / 'generated'
        subprocess.run([sys.executable, str(bundle/'scripts/guide_tools.py'), 'dance', str(output/'guide')],
                       cwd=foreign, check=True, capture_output=True)
        subprocess.run([sys.executable, str(bundle/'scripts/tile_tools.py'), 'process-on-floor',
                        str(output/'guide.png'), str(output/'guide.json'), str(output/'processed')],
                       cwd=foreign, check=True, capture_output=True)
        result = json.loads((output/'processed/result.json').read_text())
        self.assertEqual(len(result['frames']), 6)
        self.assertTrue(all(abs(f['durationMs']-1000/12)<1e-9 for f in result['frames']))
        self.assertTrue(all(f['anchor']==[96,248] for f in result['frames']))
        registration = output/'registration.json'
        registration.write_text(json.dumps({'kind':'animation','projection':'top-down-oblique-square-grid',
                                           'elevationPx':160,'occupiedCells':[[0,0]]}))
        subprocess.run([sys.executable, str(bundle/'scripts/assemble_result.py'),
                        '--input-result',str(output/'processed/result.json'),
                        '--registration',str(registration),'--output',str(output/'result.json')],
                       cwd=foreign, check=True, capture_output=True)
        delivered = json.loads((output/'result.json').read_text())
        self.assertEqual(delivered['version'],2)
        self.assertEqual(delivered['fps'],12)
        self.assertEqual(len(delivered['sprites']),6)
        self.assertTrue(all(s['anchor']==[96,248] for s in delivered['sprites']))
        subprocess.run([sys.executable, str(bundle/'scripts/prepare_evals.py'), '--run-root', str(foreign/'eval-run')],
                       cwd=foreign, check=True, capture_output=True)
        run = json.loads((foreign/'eval-run/run.json').read_text())
        self.assertEqual(len(run['trials']), 13)
        self.assertTrue(all(t['status']=='not-run' for t in run['trials']))
        for trial in run['trials']:
            request = (foreign/'eval-run'/trial['requestFile']).read_text()
            self.assertIn(trial['outputDirectory'], request)
            self.assertNotIn('{{OUTPUT_DIR}}', request)

    def test_preparation_preserves_previous_run_and_freezes_rubric(self):
        root = self.directory / 'run'
        record = prepare(root, selected=['lava-tile'])
        self.assertEqual(record['mode'], 'prepared-not-run')
        self.assertEqual(record['suiteSHA256'], hashlib.sha256((root/'suite.json').read_bytes()).hexdigest())
        with self.assertRaisesRegex(ValueError, 'empty'):
            prepare(root)

    def test_preparation_refuses_escaped_case_destination(self):
        case = dict(self.cases['lava-tile'], outputSubdir='../escape')
        suite = self.directory/'cases.json'
        suite.write_text(json.dumps({'version':2,'cases':[case]}))
        with self.assertRaisesRegex(ValueError, 'inside'):
            prepare(self.directory/'run', suite)
        self.assertFalse((self.directory/'escape').exists())

    def fixture(self, case_id='seamless-square-floor'):
        case = self.cases[case_id]
        self.run_root = self.directory/'frozen-run'
        prepare(self.run_root, selected=[case_id])
        base = self.run_root/case['outputSubdir']
        self.artifacts = base
        build('floor', base/'guide')
        source = Image.new('RGBA', (256,256), '#707050')
        source.save(base/'source-01.png')
        (base/'generation-01.json').write_text(json.dumps({
            'prompt':'Synthetic helper fixture, not a fresh behavioral trial.',
            'references':['guide-4x.png'], 'tool':'synthetic-unit-fixture',
            'referenceSHA256':{'guide-4x.png':self.digest('guide-4x.png')},
            'referenceRoles':{'guide-4x.png':'geometry'},
            'transparentBackground':case['kind']!='floor',
            'sourceSHA256':hashlib.sha256((base/'source-01.png').read_bytes()).hexdigest()}))
        expected = case['expected']
        if case['kind']=='floor':
            image = Image.new('RGB', (128,128), '#707050')
        else:
            image = Image.new('RGBA', tuple(expected['size']))
            ImageDraw.Draw(image).rectangle((32,184,159,311), fill='#707050')
        image.save(base/'sprite.png')
        sprite = {'id':'fixture','image':'sprite.png',
                  **{k:expected[k] for k in ('size','anchor','footprint','occupiedCells','elevationPx')}}
        result = {'version':2,'kind':case['kind'],'projection':'top-down-oblique-square-grid',
                  'cellSize':128,'sprites':[sprite]}
        (base/'result.json').write_text(json.dumps(result))
        submission = {'caseId':case_id,'outputDirectory':str(base),
                      'userPrompt':case['prompt'].replace('{{OUTPUT_DIR}}',str(base)),
                      'sources':[{'image':'source-01.png','recipe':'generation-01.json'}],
                      'guide':'guide.json','guideSHA256':self.digest('guide.json'),'result':'result.json'}
        path = base/'submission.json';path.write_text(json.dumps(submission))
        return case,path

    def test_structural_success_does_not_claim_visual_pass(self):
        case, path = self.fixture()
        report = self.grade(case,path,output_path=self.directory/'reports/floor.json')
        self.assertEqual(report['status'],'needs-visual-review')
        self.assertTrue(all(c['pass'] for c in report['automaticChecks']))
        self.assertEqual(len(report['reviewArtifacts']),2)

    def test_floor_seam_jump_is_a_failure(self):
        case,path = self.fixture()
        image = Image.new('RGB',(128,128),'black')
        ImageDraw.Draw(image).rectangle((64,0,127,127),fill='white')
        image.save(self.artifacts/'sprite.png')
        report = self.grade(case,path)
        self.assertEqual(report['status'],'failed')
        self.assertFalse(next(c for c in report['automaticChecks'] if c['check']=='opposite-edge-continuity')['pass'])

    def test_flat_lava_cannot_pass_visible_height_requirement(self):
        case,path = self.fixture('lava-tile')
        report = self.grade(case,path)
        self.assertEqual(report['status'],'failed')
        self.assertFalse(next(c for c in report['automaticChecks'] if c['check']=='fixture-visible-elevation')['pass'])

    def test_wrong_destination_and_changed_source_fail(self):
        case,path = self.fixture()
        submission = json.loads(path.read_text());submission['outputDirectory']='/elsewhere'
        path.write_text(json.dumps(submission))
        Image.new('RGBA',(256,256),'blue').save(self.artifacts/'source-01.png')
        report = self.grade(case,path)
        failed = {c['check'] for c in report['automaticChecks'] if not c['pass']}
        self.assertIn('requested-output-location',failed)
        self.assertIn('source-0-unchanged',failed)

    def test_references_outside_bundle_are_refused(self):
        case,path = self.fixture()
        recipe = json.loads((self.artifacts/'generation-01.json').read_text())
        recipe['references']=['../not-portable.png']
        (self.artifacts/'generation-01.json').write_text(json.dumps(recipe))
        self.assertEqual(self.grade(case,path)['status'],'failed')

    def test_recipe_relative_paths_can_cross_sibling_directories_inside_bundle(self):
        case,path = self.fixture()
        recipes = self.artifacts/'recipes';recipes.mkdir()
        references = self.artifacts/'references';references.mkdir()
        (self.artifacts/'guide-4x.png').rename(references/'guide.png')
        recipe_path = self.artifacts/'generation-01.json'
        recipe = json.loads(recipe_path.read_text())
        recipe.update(references=['../references/guide.png'],
                      referenceSHA256={'../references/guide.png':self.digest('references/guide.png')},
                      referenceRoles={'../references/guide.png':'geometry'})
        (recipes/'generation.json').write_text(json.dumps(recipe))
        submission = json.loads(path.read_text());submission['sources'][0]['recipe']='recipes/generation.json'
        path.write_text(json.dumps(submission))
        self.assertEqual(self.grade(case,path)['status'],'needs-visual-review')

    def test_old_frame_durations_fail_even_with_12_fps_header(self):
        case,path = self.fixture('animated-lava')
        result = json.loads((self.artifacts/'result.json').read_text())
        sprite = result['sprites'][0]
        result['fps'] = 12
        result['sprites'] = [dict(sprite,id=f'frame-{i}',index=i,durationMs=125) for i in range(12)]
        (self.artifacts/'result.json').write_text(json.dumps(result))
        report = self.grade(case,path)
        self.assertEqual(report['status'],'failed')
        self.assertFalse(next(c for c in report['automaticChecks'] if c['check']=='12-fps-schedule')['pass'])

    def test_review_for_different_output_images_is_refused(self):
        case,path = self.fixture()
        review = self.directory/'review.json'
        review.write_text(json.dumps({'independent':True,'reviewer':'Synthetic test fixture',
                                     'spriteSHA256':{'fixture':'stale'},
                                     'checks':{k:{'pass':True,'note':'Synthetic grader fixture only'}
                                               for k in case['visualChecks']}}))
        report = self.grade(case,path,review)
        self.assertEqual(report['status'],'failed')
        self.assertFalse(report['visualChecks'][0]['pass'])

    def test_reference_pixel_change_is_detected(self):
        case,path = self.fixture()
        Image.new('RGB',(128,128),'blue').save(self.artifacts/'guide-4x.png')
        report = self.grade(case,path)
        self.assertFalse(next(c for c in report['automaticChecks'] if c['check']=='source-0-reference-hashes')['pass'])

    def test_recipe_requires_tool_transparency_and_reference_roles(self):
        case,path = self.fixture()
        recipe_path = self.artifacts/'generation-01.json'
        recipe = json.loads(recipe_path.read_text())
        del recipe['tool']
        recipe['transparentBackground'] = 'false'
        recipe['referenceRoles'] = {}
        recipe_path.write_text(json.dumps(recipe))
        report = self.grade(case,path)
        self.assertFalse(next(c for c in report['automaticChecks'] if c['check']=='source-0-recipe-fields')['pass'])

    def test_authored_svg_workflow_accepts_opaque_reference_free_material(self):
        case,path = self.fixture('lava-tile')
        submission = json.loads(path.read_text());submission['sources'][0]['role']='appearance-material'
        path.write_text(json.dumps(submission))
        recipe_path = self.artifacts/'generation-01.json'
        recipe = json.loads(recipe_path.read_text())
        recipe.update(transparentBackground=False,references=[],referenceSHA256={},referenceRoles={})
        recipe_path.write_text(json.dumps(recipe))
        report = self.grade(case,path)
        recipe_checks = [c for c in report['automaticChecks'] if c['check'].startswith('source-0-')]
        self.assertTrue(all(c['pass'] for c in recipe_checks),recipe_checks)

    def test_delivery_cannot_redefine_its_requested_destination(self):
        case,path = self.fixture()
        wrong = self.directory/'different-destination'
        shutil.copytree(self.artifacts,wrong)
        submission = json.loads(path.read_text())
        submission['outputDirectory'] = str(wrong)
        submission['userPrompt'] = case['prompt'].replace('{{OUTPUT_DIR}}',str(wrong))
        relocated = wrong/'submission.json';relocated.write_text(json.dumps(submission))
        report = self.grade(case,relocated)
        failed = {c['check'] for c in report['automaticChecks'] if not c['pass']}
        self.assertIn('requested-output-location',failed)
        self.assertIn('case-and-request',failed)

    def test_duplicate_sprite_ids_cannot_hide_frames_from_review(self):
        case,path = self.fixture('animated-lava')
        result_path = self.artifacts/'result.json'
        result = json.loads(result_path.read_text())
        sprite = result['sprites'][0]
        result.update(fps=12,sprites=[dict(sprite,index=i,durationMs=1000/12) for i in range(12)])
        result_path.write_text(json.dumps(result))
        report = self.grade(case,path)
        self.assertFalse(next(c for c in report['automaticChecks'] if c['check']=='unique-sprite-ids')['pass'])

    def test_review_is_bound_to_registration_and_result_metadata(self):
        case,path = self.fixture()
        review = self.artifacts/'review.json'
        review.write_text(json.dumps({'independent':True,'reviewer':'Synthetic grader fixture',
                                     'spriteSHA256':{'fixture':self.digest('sprite.png')},
                                     'resultSHA256':self.digest('result.json'),'guideSHA256':self.digest('guide.json'),
                                     'checks':{k:{'pass':True,'note':'Synthetic helper test; no artwork quality claim'}
                                               for k in case['visualChecks']}}))
        self.assertEqual(self.grade(case,path,review)['status'],'passed')
        result_path = self.artifacts/'result.json'
        result = json.loads(result_path.read_text());result['registrationNote']='Changed after review'
        result_path.write_text(json.dumps(result))
        report = self.grade(case,path,review)
        self.assertEqual(report['status'],'failed')
        self.assertFalse(report['visualChecks'][0]['pass'])

    def test_assembler_refuses_geometry_overrides_and_silent_retiming(self):
        image = self.directory/'sprite.png';Image.new('RGBA',(128,128),'blue').save(image)
        processing_path = self.directory/'processing.json'
        processing_path.write_text(json.dumps({'frames':[{'image':'sprite.png','size':[128,128],
                                                         'anchor':[64,64],'footprint':[128,128],'durationMs':125}]}))
        registration_path = self.directory/'registration.json'
        registration = {'kind':'animation','projection':'top-down-oblique-square-grid',
                        'elevationPx':32,'occupiedCells':[[0,0]]}
        registration_path.write_text(json.dumps(registration))
        with self.assertRaisesRegex(ValueError,'12 fps'):
            assemble([processing_path],registration_path,self.directory/'result.json')
        registration.update(kind='object',sprites=[{'anchor':[64,32]}])
        registration_path.write_text(json.dumps(registration))
        with self.assertRaisesRegex(ValueError,'geometry'):
            assemble([processing_path],registration_path,self.directory/'result.json')

    def test_depth_pieces_must_be_registered_separate_images(self):
        case,path = self.fixture('disjoint-support-arch')
        result_path = self.artifacts/'result.json'
        result = json.loads(result_path.read_text())
        result['supportCells'] = case['expected']['supportCells']
        result['overheadCells'] = case['expected']['overheadCells']
        result['depthPieces'] = [{'id':f'piece-{i}','drawOrder':i,'image':'sprite.png',
                                  'size':case['expected']['size'],'anchor':case['expected']['anchor']}
                                 for i in range(2)]
        result_path.write_text(json.dumps(result))
        report = self.grade(case,path)
        self.assertFalse(next(c for c in report['automaticChecks'] if c['check']=='authored-depth-pieces')['pass'])


if __name__ == '__main__':
    unittest.main()
