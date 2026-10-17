"""Gallery fixtures exercise run selection and publication, without generating art."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build_eval_gallery import build_gallery


class EvalGalleryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.case={'id':'floor','prompt':'Generate a floor in {{OUTPUT_DIR}}.','kind':'floor',
                   'expected':{'size':[128,128]},'visualChecks':{'seams':'Connected edges'}}
        self.suite=self.root/'suite.json'
        self.suite.write_text(json.dumps({'version':2,'cases':[self.case]}))

    def run_record(self,name,status=None,case=None,prepared=False,no_result=False):
        case=case or self.case
        run=self.root/'runs'/name;directory=run/'floor';directory.mkdir(parents=True)
        (run/'suite.json').write_text(json.dumps({'version':2,'cases':[case]}))
        (run/'run.json').write_text(json.dumps({'suite':'suite.json','createdAt':name,
            'trials':[{'caseId':'floor','directory':'floor','status':'not-run'}]}))
        if prepared:return
        Image.new('RGB',(128,128),'gray').save(directory/'source.png')
        Image.new('RGB',(128,128),'gray').save(directory/'guide.png')
        (directory/'guide.json').write_text('{}')
        (directory/'generation.json').write_text(json.dumps({'prompt':'Exact model prompt',
                                                             'references':['guide.png']}))
        (directory/'submission.json').write_text(json.dumps({'caseId':'floor',
            'userPrompt':f'Generate a floor in {directory}.','guide':'guide.json',
            'sources':[{'image':'source.png','recipe':'generation.json'}],'result':'result.json'}))
        if not no_result:
            (directory/'result.json').write_text(json.dumps({'kind':'floor',
                'sprites':[{'id':'floor','image':'source.png','size':[128,128],'anchor':[64,64]}]}))
        if status:
            (run/'reports').mkdir()
            (run/'reports/floor.json').write_text(json.dumps({'status':status,'automaticChecks':[],
                                                             'visualChecks':[],'reviewArtifacts':{}}))

    def build(self):
        return build_gallery(self.root/'runs',self.suite,self.root/'public',self.root/'reports')

    def test_newest_failure_is_selected_and_unrun_does_not_hide_it(self):
        self.run_record('2026-01-01',status='passed')
        self.run_record('2026-02-01',status='failed')
        self.run_record('2026-03-01',prepared=True)
        case=self.build()['cases'][0]
        self.assertEqual(case['latest']['runId'],'2026-02-01')
        self.assertEqual(case['latest']['status'],'failed')
        self.assertEqual(len(case['trials']),3)
        self.assertEqual(case['latest']['sources'][0]['prompt'],'Exact model prompt')
        self.assertTrue((self.root/'public'/case['latest']['result']).is_file())

    def test_changed_rubric_is_not_presented_as_current_result(self):
        self.run_record('2026-01-01',status='passed',case=dict(self.case,prompt='Old flat-lava request'))
        gallery=self.build()
        self.assertIsNone(gallery['cases'][0]['latest'])
        self.assertEqual(gallery['archivedCases'],[])
        self.assertFalse((self.root/'public/evals').exists())

    def test_failed_processing_still_publishes_original_source_and_prompt(self):
        self.run_record('2026-01-01',status='failed',no_result=True)
        trial=self.build()['cases'][0]['latest']
        self.assertEqual(trial['status'],'failed')
        self.assertEqual(trial['sprites'],[])
        self.assertTrue((self.root/'public'/trial['sources'][0]['image']).is_file())

    def test_failed_directions_expose_raw_player_without_creating_runtime_sprites(self):
        case=dict(self.case,kind='directions')
        self.suite.write_text(json.dumps({'version':2,'cases':[case]}))
        self.run_record('2026-01-01',status='failed',case=case,no_result=True)
        directory=self.root/'runs/2026-01-01/floor'
        from PIL import ImageDraw
        source=Image.new('RGBA',(128,128),(0,0,0,0))
        draw=ImageDraw.Draw(source)
        cells=[]
        for index in range(8):
            x,y=(index%4)*32,(index//4)*64
            draw.rectangle((x+12,y+12,x+20,y+52),fill=(20,100,200,255))
            cells.append({'index':index,'rect':[x+3,y+3,x+29,y+61]})
        source.save(directory/'source.png')
        original=(directory/'source.png').read_bytes()
        (directory/'guide.json').write_text(json.dumps({'kind':'rendered-3d-sheet',
            'size':[128,128],'columns':4,'rows':2,'cells':cells}))
        trial=self.build()['cases'][0]['latest']
        self.assertEqual(trial['sprites'],[])
        self.assertFalse(trial['previewSequence']['isProcessedSprite'])
        self.assertEqual(len(trial['previewSequence']['frames']),8)
        self.assertEqual((directory/'source.png').read_bytes(),original)

    def test_direct_render_inputs_publish_as_files_instead_of_broken_images(self):
        self.run_record('2026-01-01',status='passed')
        run=self.root/'runs/2026-01-01';directory=run/'floor'
        record=json.loads((run/'run.json').read_text());record['mode']='3d-render-control'
        (run/'run.json').write_text(json.dumps(record))
        (directory/'camera.json').write_text('{"projection":"orthographic"}')
        (directory/'generation.json').write_text(json.dumps({'prompt':'Direct render, zero AI calls',
            'references':['camera.json','guide.png']}))
        trial=self.build()['cases'][0]['latest']
        self.assertEqual(trial['runMode'],'3d-render-control')
        files,images=trial['sources'][0]['references']
        self.assertEqual(files['mediaType'],'file')
        self.assertEqual(images['mediaType'],'image')
        self.assertEqual((self.root/'public'/files['image']).read_text(),(directory/'camera.json').read_text())

    def test_references_cannot_publish_files_outside_case_bundle(self):
        self.run_record('2026-01-01',status='failed')
        p=self.root/'runs/2026-01-01/floor/generation.json'
        p.write_text(json.dumps({'prompt':'Exact prompt','references':['../../secret.png']}))
        with self.assertRaisesRegex(ValueError,'escapes'):
            self.build()

    def test_svg_overlay_preserves_original_and_explicit_registration(self):
        self.run_record('2026-01-01',status='failed')
        directory = self.root/'runs/2026-01-01/floor'
        layout = {'kind':'object-sheet','cellSize':128,'size':[128,128],
                  'frame':[128,128],'anchor':[64,64],
                  'cells':[{'rect':[0,0,128,128]}],
                  'subjectRegistration':{'height':80,'baseSize':[32,32]}}
        (directory/'guide.json').write_text(json.dumps(layout))
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128"><path d="M64 64V8" stroke="blue"/></svg>'
        (directory/'guide.svg').write_text(svg)
        overlay = self.build()['cases'][0]['latest']['guideOverlay']
        self.assertEqual(overlay['anchor'],[64,64])
        self.assertEqual(overlay['size'],[128,128])
        self.assertEqual(overlay['heightPx'],80)
        self.assertEqual((self.root/'public'/overlay['image']).read_text(),svg)
        # A multi-panel SVG needs its own declared per-panel mapping.
        layout['cells'].append({'rect':[0,0,128,128]})
        (directory/'guide.json').write_text(json.dumps(layout))
        self.assertNotIn('guideOverlay',self.build()['cases'][0]['latest'])

    def test_new_assessment_keeps_original_grade_and_art_separate(self):
        self.run_record('2026-01-01',status='failed')
        run = self.root/'runs/2026-01-01'
        record = json.loads((run/'run.json').read_text())
        record['assessments'] = [{'id':'llm-v1','createdAt':'2026-02-01','label':'LLM visual review',
            'directory':'assessments/llm-v1','cases':{'floor':{'report':'reports/floor.json',
                'review':'reviews/floor.json','packet':'packets/floor.json',
                'expectedStatus':'passed','reason':'No visible seam.'}}}]
        (run/'run.json').write_text(json.dumps(record))
        assessment = run/'assessments/llm-v1'
        (assessment/'reports').mkdir(parents=True);(assessment/'reviews').mkdir()
        (assessment/'packets').mkdir()
        preview = assessment/'packets/placement-light.png'
        Image.new('RGB',(128,128),'gray').save(preview)
        (assessment/'packets/floor.json').write_text(json.dumps({'assets':[
            {'role':'placement-preview','path':str(preview)},
            {'role':'source','path':str(run/'floor/source.png')}]}))
        (assessment/'policy.json').write_text('{}')
        (assessment/'reviews/floor.json').write_text('{}')
        (assessment/'reports/floor.json').write_text(json.dumps({'status':'passed','policy':'llm-visual-v1',
            'reviewer':'Fixture LLM','visualChecks':[{'check':'seams','pass':True,'detail':'No visible seam.'}],
            'diagnostics':[{'check':'opposite-edge-continuity','gating':False,'detail':12}]}))
        case = self.build()['cases'][0]
        original, latest = case['trials']
        self.assertEqual(latest,case['latest'])
        self.assertEqual((original['status'],latest['status']),('failed','passed'))
        self.assertEqual(original['sources'],latest['sources'])
        self.assertNotEqual(original['id'],latest['id'])
        self.assertNotEqual(original['report'],latest['report'])
        for trial in [original,latest]:
            saved = json.loads((self.root/'public'/trial['report']).read_text())
            self.assertEqual(saved['status'],trial['status'])
        self.assertEqual(latest['diagnostics'][0]['gating'],False)
        self.assertEqual(len(latest['previews']),1)
        self.assertTrue((self.root/'public'/latest['previews'][0]['image']).is_file())


if __name__=='__main__':
    unittest.main()
