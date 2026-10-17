"""A direct 3D control must never satisfy an all-AI-reskin experiment."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from audit_reskin_run import audit


class ReskinCoverageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.run = Path(temp.name)
        self.case = self.run / 'object'
        self.case.mkdir()
        self.write(self.run/'suite.json', {'cases': [{'id':'object','kind':'object','expected':{}}]})
        self.write(self.run/'run.json', {'suite':'suite.json','plannedGenerationCalls':1,
            'trials':[{'caseId':'object','generationCalls':1}]})
        Image.new('RGBA', (32,32), (200,80,30,255)).save(self.case/'source-01.png')
        Image.new('RGBA', (32,32), (80,80,80,255)).save(self.case/'geometry.png')
        self.recipe = {'tool':'image_gen.imagegen','prompt':'Reskin this 3D blockout',
            'references':['geometry.png'],
            'referenceSHA256':{'geometry.png':self.sha(self.case/'geometry.png')},
            'sourceSHA256':self.sha(self.case/'source-01.png')}
        self.write(self.case/'generation-01.json',self.recipe)
        self.write(self.case/'submission.json', {'sources':[
            {'image':'source-01.png','recipe':'generation-01.json'}], 'result':'result.json'})
        self.result={'workflow':'3d-imagegen-reskin', 'provenance':{
            'imageGenerationCalls':1,'reskinSources':['source-01.png']},
            'sprites':[{'id':'object','image':'source-01.png'}]}
        self.write(self.case/'result.json',self.result)

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def write(path,value):
        path.write_text(json.dumps(value))

    def test_new_ai_original_is_covered_even_if_visual_quality_later_fails(self):
        self.assertTrue(audit(self.run)['ok'])

    def test_direct_render_cannot_be_relabelled_as_an_ai_candidate(self):
        self.recipe['tool']='THREE.WebGLRenderer'
        self.write(self.case/'generation-01.json',self.recipe)
        report=audit(self.run)
        self.assertFalse(report['ok'])
        self.assertIn('recipe is not an imagegen call',report['cases'][0]['errors'][0])

    def test_copying_the_reference_is_not_a_new_reskin(self):
        (self.case/'source-01.png').write_bytes((self.case/'geometry.png').read_bytes())
        self.recipe['sourceSHA256']=self.sha(self.case/'source-01.png')
        self.write(self.case/'generation-01.json',self.recipe)
        self.assertFalse(audit(self.run)['ok'])

    def test_missing_ai_pass_for_a_second_layer_fails_coverage(self):
        self.write(self.run/'suite.json',{'cases':[{'id':'object','kind':'layered','expected':{}}]})
        self.result['sprites']=[{'id':'stool','image':'source-01.png','reskinSource':'source-01.png'},
                               {'id':'character','image':'geometry.png'}]
        self.write(self.case/'result.json',self.result)
        self.assertFalse(audit(self.run)['ok'])
