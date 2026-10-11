"""Pipeline/grader regression fixtures are synthetic; behavioral runs use fresh AI art."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image,ImageDraw

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from calibration_guides import build
from tilekit import load_rgba,prepare_floor_material,process_object_sheet,write_json
from eval_tile_skill import evaluate,reserved_hue_residual,CASES


class SkillEvalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)
        self.cases={c['id']:c for c in json.loads(CASES.read_text())['cases']}

    def floor_submission(self):
        d=self.directory;build('floor',d/'guide')
        image=Image.new('RGBA',(256,256),(240,80,15,255));image.save(d/'source.png')
        result,info=prepare_floor_material(image);result.save(d/'tile.png')
        write_json(d/'tile.json',{**info,'image':'tile.png'})
        write_json(d/'generation.json',{'prompt':'Synthetic unit fixture; not a behavioral image-generation run.',
            'references':['guide-4x.png'],'transparentBackground':False,
            'sourceSHA256':hashlib.sha256((d/'source.png').read_bytes()).hexdigest()})
        path=d/'submission.json'
        write_json(path,{'caseId':'lava-tile','userPrompt':self.cases['lava-tile']['prompt'],
            'source':'source.png','generationRecipe':'generation.json','guide':'guide.json','result':'tile.json'})
        return path

    def test_valid_artifacts_require_independent_visual_review(self):
        report=evaluate(self.cases['lava-tile'],self.floor_submission())
        self.assertEqual(report['status'],'needs-visual-review')
        self.assertTrue(all(c['pass'] for c in report['automaticChecks']))

    def test_wrong_anchor_fails_even_when_pixels_look_valid(self):
        path=self.floor_submission();result=json.loads((self.directory/'tile.json').read_text())
        result['anchor']=[64,128];write_json(self.directory/'tile.json',result)
        report=evaluate(self.cases['lava-tile'],path)
        self.assertEqual(report['status'],'failed')
        self.assertFalse(next(c for c in report['automaticChecks'] if c['check']=='runtime-ground-geometry')['pass'])

    def test_modified_source_or_missing_generation_record_cannot_pass(self):
        path=self.floor_submission()
        Image.new('RGBA',(256,256),'blue').save(self.directory/'source.png')
        report=evaluate(self.cases['lava-tile'],path)
        self.assertEqual(report['status'],'failed')
        self.assertFalse(next(c for c in report['automaticChecks'] if c['check']=='unchanged-generated-source')['pass'])
        (self.directory/'generation.json').unlink()
        self.assertEqual(evaluate(self.cases['lava-tile'],path)['status'],'failed')

    def test_ground_material_refuses_transparent_or_non_square_sources(self):
        for image in (Image.new('RGBA',(128,128)),Image.new('RGBA',(127,128),'red')):
            with self.assertRaises(ValueError):prepare_floor_material(image)

    def test_sheet_uses_floor_center_for_all_poses_and_refuses_gutter_art(self):
        guide=build('dance',self.directory/'guide')
        image=load_rgba(self.directory/'guide-4x.png')
        frames=process_object_sheet(image,guide)
        self.assertEqual(len(frames),6)
        for frame,info in frames:
            self.assertEqual(frame.size,(192,320))
            self.assertEqual(info['anchor'],[96,248])
            self.assertEqual(info['normalization']['anchorSource'],info['floor']['anchor'])
            self.assertEqual(frame.getpixel((40,295))[3],0)
        image.putpixel((210*4,100*4),(200,40,60,255))
        with self.assertRaisesRegex(ValueError,'gutter'):process_object_sheet(image,guide)

    def test_missing_visual_check_cannot_be_replaced_by_a_summary(self):
        path=self.floor_submission();review=self.directory/'review.json'
        write_json(review,{'checks':{},'summary':'Looks good'})
        self.assertEqual(evaluate(self.cases['lava-tile'],path,review)['status'],'failed')

    def test_floor_residue_check_preserves_non_green_hand_at_corner(self):
        image=Image.new('RGBA',(192,320))
        chroma={'keyRGB':[123,209,75],'region':[29,181,163,315]}
        image.putpixel((35,188),(139,74,43,255))
        self.assertEqual(reserved_hue_residual(image,chroma),0)
        image.putpixel((40,200),(123,209,75,255))
        self.assertEqual(reserved_hue_residual(image,chroma),1)

    def test_transparent_separator_recovery_keeps_protruding_finger_and_refuses_touching_panels(self):
        guide=build('dance',self.directory/'guide');image=load_rgba(self.directory/'guide.png')
        draw=ImageDraw.Draw(image)
        draw.rectangle((224,352,415,671),fill=(0,0,0,0))
        draw.rectangle((256,524,383,651),fill=(123,209,75,255))
        draw.rectangle((314,348,325,600),fill=(30,80,160,255))
        with self.assertRaisesRegex(ValueError,'gutter'):process_object_sheet(image,guide)
        frames=process_object_sheet(image,guide,allow_gutter_drift=True)
        cutout,info=frames[4]
        self.assertEqual(info['anchor'],[96,248])
        self.assertEqual(info['panelIsolation'],'transparent-separators')
        self.assertEqual(cutout.getpixel((96,8)),(30,80,160,255))
        draw.rectangle((0,320,639,351),fill=(30,80,160,255))
        with self.assertRaisesRegex(ValueError,'transparent separator'):
            process_object_sheet(image,guide,allow_gutter_drift=True)


if __name__=='__main__':unittest.main()
