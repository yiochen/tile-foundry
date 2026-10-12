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

    def test_references_cannot_publish_files_outside_case_bundle(self):
        self.run_record('2026-01-01',status='failed')
        p=self.root/'runs/2026-01-01/floor/generation.json'
        p.write_text(json.dumps({'prompt':'Exact prompt','references':['../../secret.png']}))
        with self.assertRaisesRegex(ValueError,'escapes'):
            self.build()


if __name__=='__main__':
    unittest.main()
