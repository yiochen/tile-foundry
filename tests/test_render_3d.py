"""Actual fixed-camera 3D captures; these assertions do not grade AI reskins."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/build-overlap-tiles/scripts'


class Render3DTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        # A copied bundle outside this repository must resolve its explicitly
        # supplied npm runtime, rather than reach back through project paths.
        cls.portable = cls.root / 'portable-skill'
        cls.portable.mkdir()
        for name in ('render_3d.mjs', 'render_3d_scene.js', 'package.json'):
            shutil.copyfile(SCRIPTS / name, cls.portable / name)
        cls.outputs = {}
        for mode in ('dance', 'directions'):
            destination = cls.root / mode
            completed = subprocess.run(['node', str(cls.portable / 'render_3d.mjs'), mode,
                str(destination), '--scale', '2', '--runtime-root', str(ROOT)],
                cwd=cls.root, check=True, text=True, capture_output=True, timeout=90)
            cls.outputs[mode] = {'path': destination,
                'receipt': json.loads(completed.stdout),
                'guide': json.loads((destination / 'guide.json').read_text()),
                'result': json.loads((destination / 'result.json').read_text()),
                'poses': json.loads((destination / 'scene/poses.json').read_text())}

    def test_projection_square_floor_and_authored_crown(self):
        for mode, data in self.outputs.items():
            with self.subTest(mode=mode):
                g = data['guide']
                self.assertEqual(g['frame'], [192, 320])
                self.assertEqual(g['anchor'], [96, 248])
                self.assertEqual(g['kind'], 'rendered-3d-sheet')
                self.assertAlmostEqual(g['neutralProjectedCrownHeight'], 160, places=4)
                for got, expected in zip(g['floorCorners'], ([32, 184], [160, 184], [160, 312], [32, 312])):
                    for a, b in zip(got['screen'], expected):
                        self.assertAlmostEqual(a, b, places=6)
                self.assertEqual(g['fitting'], {'perFrame': False, 'perDirection': False,
                    'camera': 'fixed', 'root': 'fixed', 'modelScale': 'fixed'})
                self.assertEqual(data['receipt']['browserErrors'], [])

    def test_sheet_panels_are_exact_complete_capture_frames(self):
        for mode, data in self.outputs.items():
            with self.subTest(mode=mode):
                root, g = data['path'], data['guide']
                sheet = Image.open(root / 'sheet.png').convert('RGBA')
                self.assertEqual(list(sheet.size), g['size'])
                self.assertEqual(g['captureScale'], 2)
                self.assertEqual(g['gutter'], 64)
                outside = sheet.copy()
                for cell in g['cells']:
                    rect = cell['rect']
                    self.assertEqual([rect[2]-rect[0], rect[3]-rect[1]], [384,640])
                    frame = Image.open(root / f"frames-highres/frame-{cell['index']:02}.png").convert('RGBA')
                    self.assertEqual(sheet.crop(rect).tobytes(), frame.tobytes())
                    outside.paste((0,0,0,0), rect)
                    bounds = cell['alphaBounds']
                    self.assertTrue(0 < bounds[0] < bounds[2] < 192)
                    self.assertTrue(0 < bounds[1] < bounds[3] < 320)
                self.assertIsNone(outside.getchannel('A').getbbox())

    def test_exact_alpha_masks_do_not_guess_a_key_color(self):
        for mode, data in self.outputs.items():
            for cell in data['guide']['cells']:
                i = cell['index']
                color = Image.open(data['path'] / f'frames/frame-{i:02}.png').convert('RGBA')
                mask = Image.open(data['path'] / f'masks/frame-{i:02}.png').convert('RGBA')
                self.assertIsNone(ImageChops.difference(color.getchannel('A'), mask.getchannel('R')).getbbox())
                self.assertEqual(mask.getchannel('A').getextrema(), (255,255))

    def test_skin_bones_and_camera_are_preserved_in_editable_scene(self):
        for mode, data in self.outputs.items():
            root = data['path']
            scene = json.loads((root / 'scene.json').read_text())
            rig = json.loads((root / 'scene/rig.json').read_text())
            self.assertEqual(rig['boneCount'], 18)
            self.assertGreater(rig['skinVertexCount'], 10000)
            def all_objects(obj):
                yield obj
                for child in obj.get('children', []):
                    yield from all_objects(child)
            objects = list(all_objects(scene['object']))
            self.assertEqual(sum(o['type']=='Bone' for o in objects), 18)
            self.assertEqual(sum(o['type']=='SkinnedMesh' for o in objects), 1)
            self.assertEqual(sum(o['type']=='OrthographicCamera' for o in objects), 1)
            self.assertEqual(len(scene['skeletons']), 1)
            attributes = next(g['data']['attributes'] for g in scene['geometries'] if 'skinWeight' in g.get('data',{}).get('attributes',{}))
            self.assertIn('skinIndex', attributes)
            self.assertIn('skinWeight', attributes)
            weights = attributes['skinWeight']['array']
            self.assertTrue(any(0 < w < 1 for w in weights))
            for i in range(0, len(weights), 4):
                self.assertAlmostEqual(sum(weights[i:i+4]), 1, places=6)

    def test_dance_has_fixed_root_feet_and_periodic_joint_poses(self):
        data = self.outputs['dance']
        self.assertEqual(len(data['poses']), 12)
        self.assertEqual(data['result']['fps'], 12)
        feet = data['poses'][0]['feet']
        root_matrix = data['poses'][0]['modelMatrix']
        for i, pose in enumerate(data['poses']):
            self.assertEqual(pose['rootWorld'], [0,0,0])
            self.assertEqual(pose['feet'], feet)
            self.assertEqual(pose['modelMatrix'], root_matrix)
            self.assertAlmostEqual(pose['phase'], i/12)
            for a,b in zip(pose['rootProjected'], [96,248]):
                self.assertAlmostEqual(a,b,places=6)
        self.assertEqual(len({(data['path']/s['image']).read_bytes() for s in data['result']['sprites']}), 12)
        # Test authored periodic functions at t=0 and t=2pi directly; no duplicate
        # endpoint is inserted into the 12-frame sheet.
        output = subprocess.run(['node', '--input-type=module', '-e',
            f"import {{createCharacter,setPose}} from {json.dumps((SCRIPTS/'render_3d_scene.js').as_uri())};"
            "const c=createCharacter(); setPose(c,'dance',0,12); const a=c.bones.map(b=>b.quaternion.toArray());"
            "setPose(c,'dance',12,12); console.log(JSON.stringify({a,b:c.bones.map(b=>b.quaternion.toArray())}));"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(output.returncode,0,output.stderr)
        q = json.loads(output.stdout)
        for a,b in zip(q['a'],q['b']):
            for x,y in zip(a,b):
                self.assertAlmostEqual(x,y,places=12)

    def test_authored_dance_leaves_fixed_horizontal_brushwork_margin(self):
        # A strict registered reskin must fit its declared full panels. Author
        # compact elbow curves before generation instead of fitting captures or
        # clipping image-model output after seeing it.
        for cell in self.outputs['dance']['guide']['cells']:
            with self.subTest(frame=cell['index']):
                self.assertGreaterEqual(cell['projectedBounds'][0], 24)
                self.assertLessEqual(cell['projectedBounds'][2], 192-24)
                self.assertGreaterEqual(cell['alphaBounds'][0], 24)
                self.assertLessEqual(cell['alphaBounds'][2], 192-24)

    def test_direction_order_scale_and_capture_without_fitting(self):
        data = self.outputs['directions']
        expected = ['N','NE','E','SE','S','SW','W','NW']
        self.assertEqual([c['direction'] for c in data['guide']['cells']], expected)
        self.assertEqual([s['direction'] for s in data['result']['sprites']], expected)
        self.assertNotIn('fps', data['result'])
        heights = [248-c['projectedBounds'][1] for c in data['guide']['cells']]
        self.assertLess(max(heights)-min(heights), .01)
        for s in data['result']['sprites']:
            self.assertEqual(s['anchor'], [96,248])
            self.assertEqual(s['size'], [192,320])
        capture = json.loads((data['path'] / 'capture.json').read_text())
        self.assertFalse(capture['perFrameFit'])
        self.assertFalse(capture['rootFit'])
        self.assertFalse(capture['backgroundRemoval'])
        self.assertEqual(capture['imageGenerationCalls'], 0)

    def test_refuses_to_overwrite_preserved_output(self):
        data = self.outputs['dance']
        before = (data['path']/'sheet.png').read_bytes()
        run = subprocess.run(['node',str(SCRIPTS/'render_3d.mjs'),'dance',str(data['path'])],
            capture_output=True,text=True)
        self.assertNotEqual(run.returncode,0)
        self.assertIn('already exists',run.stderr)
        self.assertEqual((data['path']/'sheet.png').read_bytes(),before)


if __name__ == '__main__':
    unittest.main()
