"""Source playback preserves originals and refuses cuts through visible art."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image, ImageDraw

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from eval_preview_sequences import partition_is_complete, source_sequence


class EvalPreviewSequencesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.submission={'sources':[{'image':'source.png'}]}
        self.guide={'kind':'authored-material-animation-sheet','size':[64,32],
                    'columns':2,'rows':1,'cells':[{'index':0,'rect':[0,0,24,32]},
                                                {'index':1,'rect':[40,0,64,32]}]}
        image=Image.new('RGBA',(64,32));draw=ImageDraw.Draw(image)
        draw.rectangle((4,4,23,27),fill='red');draw.rectangle((40,4,59,27),fill='blue')
        image.save(self.root/'source.png')

    def publish(self,path):
        self.assertIn(self.root.resolve(),path.resolve().parents)
        return path.relative_to(self.root).as_posix()

    def test_material_preview_preserves_every_source_pixel_and_retains_grade_separation(self):
        path=self.root/'source.png';before=path.read_bytes()
        sequence=source_sequence(self.root,self.submission,self.guide,self.publish)
        self.assertFalse(sequence['isProcessedSprite'])
        self.assertEqual(sequence['fps'],12)
        frames=sequence['frames']
        self.assertEqual(len(frames),2)
        self.assertTrue(partition_is_complete([f['sourceRect'] for f in frames],(64,32)))
        source=Image.open(path).convert('RGBA');reconstructed=Image.new('RGBA',source.size)
        for frame in frames:
            rect=frame['sourceRect'];reconstructed.paste(source.crop(rect),rect[:2])
        self.assertEqual(source.tobytes(),reconstructed.tobytes())
        self.assertEqual(path.read_bytes(),before)
        self.assertEqual(sequence['sourceSHA256']['source.png'],hashlib.sha256(before).hexdigest())

    def test_faint_gutter_noise_is_retained_instead_of_cleaned(self):
        path=self.root/'source.png';image=Image.open(path).convert('RGBA')
        ImageDraw.Draw(image).rectangle((24,0,39,31),fill=(120,100,70,1));image.save(path)
        before=path.read_bytes()
        sequence=source_sequence(self.root,self.submission,self.guide,self.publish)
        self.assertEqual(sequence['separatorAlphaMax'],1)
        self.assertEqual(path.read_bytes(),before)

    def test_object_sheet_can_preview_without_claiming_floor_normalization(self):
        guide={**self.guide,'kind':'object-sheet'}
        sequence=source_sequence(self.root,self.submission,guide,self.publish)
        self.assertEqual(len(sequence['frames']),2)
        self.assertEqual(sequence['alignment'],'panel-origin')
        self.assertFalse(sequence['isProcessedSprite'])
        self.assertTrue(partition_is_complete([f['sourceRect'] for f in sequence['frames']],(64,32)))
        self.assertEqual([f['anchor'] for f in sequence['frames']],[[0,0],[0,0]])

    def test_connected_visible_art_cannot_be_sliced_into_preview_frames(self):
        path=self.root/'source.png';image=Image.open(path).convert('RGBA')
        ImageDraw.Draw(image).line((20,16,44,16),fill='red',width=2);image.save(path)
        with self.assertRaisesRegex(ValueError,'No transparent gutter'):
            source_sequence(self.root,self.submission,self.guide,self.publish)

    def test_saved_panels_are_verified_against_the_complete_original(self):
        source=Image.open(self.root/'source.png').convert('RGBA')
        (self.root/'previews').mkdir();frames=[]
        for index in range(2):
            rect=[index*32,0,(index+1)*32,32]
            path=f'previews/frame-{index}.png';source.crop(rect).save(self.root/path)
            frames.append({'index':index,'sourceRect':rect,'sourcePreview':path,'actualSize':[32,32],
                           'floorObservation':{'anchor':[16,24]}})
        (self.root/'previews/source-panels.json').write_text(json.dumps({'kind':'unprocessed-source-panels','frames':frames}))
        sequence=source_sequence(self.root,self.submission,{},self.publish)
        self.assertEqual(sequence['alignment'],'recorded-floor-center')
        self.assertEqual(sequence['frames'][0]['anchor'],[16,24])
        Image.new('RGBA',(32,32),'green').save(self.root/'previews/frame-0.png')
        with self.assertRaisesRegex(ValueError,'differs from its original'):
            source_sequence(self.root,self.submission,{},self.publish)

    def test_partition_rejects_gaps_overlaps_and_out_of_bounds(self):
        for rects in [[[0,0,30,32],[32,0,64,32]],[[0,0,34,32],[32,0,64,32]],
                      [[-1,0,32,32],[32,0,64,32]]]:
            self.assertFalse(partition_is_complete(rects,(64,32)))


if __name__=='__main__':unittest.main()
