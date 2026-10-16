import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from tilekit import floor_anchor, remove_detached_markers, subtract_authored_floor, remove_floor_chroma, normalize, export_tiled


class CharacterAnchorTests(unittest.TestCase):
    def marked_character(self):
        image=Image.new('RGBA',(120,160));draw=ImageDraw.Draw(image)
        draw.rectangle((45,10,54,98),fill=(20,80,150,255))
        draw.rectangle((18,30,101,39),fill=(20,80,150,255))
        for x in (20,92):
            for y in (60,132): draw.rectangle((x,y,x+7,y+7),fill=(123,209,75,255))
        return image

    def test_solid_floor_center_does_not_follow_feet_or_color(self):
        image=Image.new('RGBA',(160,200));draw=ImageDraw.Draw(image)
        draw.rectangle((30,90,129,189),fill='blue')
        draw.rectangle((65,10,94,120),fill='blue')
        observation=floor_anchor(image)
        self.assertEqual(observation['rect'],[30,90,130,190])
        self.assertEqual(observation['anchor'],[80,140])
        self.assertNotEqual(observation['anchor'][1],120)

    def test_detached_markers_removed_even_when_bounding_boxes_overlap(self):
        image=self.marked_character();observation=floor_anchor(image,'corners')
        self.assertEqual(observation['anchor'],[60,100])
        output,info=remove_detached_markers(image,observation)
        self.assertTrue(info['exactKeptPixels'])
        for p,q in zip(image.getdata(),output.getdata()):
            if p[:3]==(20,80,150): self.assertEqual(q,p)
            else: self.assertEqual(q[3],0)
        _,meta=normalize(output,frame=(192,320),anchor_in=observation['anchor'],anchor_out=(96,248),scale=1)
        self.assertEqual(meta['anchor'],[96,248])
        self.assertEqual(meta['anchorSource'],[60,100])

    def test_hand_touching_floor_does_not_expand_measured_floor_width(self):
        image=Image.new('RGBA',(160,200));draw=ImageDraw.Draw(image)
        draw.rectangle((30,90,129,189),fill=(123,209,75,255))
        draw.rectangle((65,10,94,120),fill='blue')
        draw.rectangle((23,90,40,96),fill='brown')
        observation=floor_anchor(image)
        self.assertEqual(observation['rect'],[30,90,130,190])
        self.assertEqual(observation['anchor'],[80,140])

    def test_touching_marker_refused_instead_of_cutting_character(self):
        image=self.marked_character()
        ImageDraw.Draw(image).rectangle((27,63,45,64),fill='blue')
        with self.assertRaisesRegex(ValueError,'four detached'):
            floor_anchor(image,'corners')

    def test_known_floor_subtraction_retains_repainted_pixels_and_character(self):
        floor=Image.new('RGBA',(192,320));draw=ImageDraw.Draw(floor)
        draw.rectangle((32,184,159,311),fill=(123,209,75,255))
        image=floor.copy();image.putpixel((35,200),(124,209,75,255));image.putpixel((96,248),(20,80,150,255))
        result,info=subtract_authored_floor(image,floor)
        self.assertEqual(result.getpixel((34,200))[3],0)
        self.assertEqual(result.getpixel((35,200)),image.getpixel((35,200)))
        self.assertEqual(result.getpixel((96,248)),image.getpixel((96,248)))
        self.assertFalse(info['productionSafe'])

    def test_empty_floor_and_invalid_threshold_rejected(self):
        for threshold in (0,255):
            with self.assertRaises(ValueError):floor_anchor(Image.new('RGBA',(20,20)),threshold=threshold)
        with self.assertRaises(ValueError):floor_anchor(Image.new('RGBA',(20,20)))

    def test_explicit_floor_key_preserves_shoes_frame_anchor_and_green_outside_floor(self):
        image=Image.new('RGBA',(160,200));draw=ImageDraw.Draw(image)
        draw.rectangle((30,90,129,189),fill=(123,209,75,255))
        draw.rectangle((65,20,94,140),fill=(70,40,25,255))
        draw.rectangle((65,10,94,19),fill=(123,209,75,255))
        observation=floor_anchor(image);original=image.tobytes()
        result,info=remove_floor_chroma(image,observation,(123,209,75))
        self.assertEqual(result.size,image.size)
        self.assertEqual(info['anchor'],[80,140])
        self.assertEqual(result.getpixel((40,150))[3],0)
        self.assertEqual(result.getpixel((80,140)),image.getpixel((80,140)))
        self.assertEqual(result.getpixel((80,15)),image.getpixel((80,15)))
        self.assertEqual(image.tobytes(),original)

    def test_chroma_key_handles_shading_and_detached_pale_corner_accents(self):
        image=Image.new('RGBA',(120,160));draw=ImageDraw.Draw(image)
        draw.rectangle((20,60,99,139),fill=(60,110,35,255))
        draw.rectangle((22,65,28,66),fill=(255,255,255,255))
        draw.rectangle((50,20,69,110),fill=(30,80,160,255))
        draw.rectangle((50,2,55,6),fill=(255,255,255,255))
        observation=floor_anchor(image)
        result,info=remove_floor_chroma(image,observation,(123,209,75),remove_corner_remnants=True)
        self.assertEqual(result.getpixel((30,120))[3],0)
        self.assertEqual(result.getpixel((25,65))[3],0)
        self.assertEqual(result.getpixel((60,110)),image.getpixel((60,110)))
        self.assertEqual(result.getpixel((52,3)),image.getpixel((52,3)))
        self.assertEqual(len(info['removedCornerRemnants']),1)

    def test_soft_chroma_matte_is_explicitly_approximate_and_rejects_invalid_key(self):
        image=Image.new('RGBA',(80,80),(140,200,110,255))
        observation={'mode':'solid','rect':[0,0,80,80],'anchor':[40,40]}
        result,info=remove_floor_chroma(image,observation,(123,209,75))
        self.assertGreater(result.getpixel((40,40))[3],0)
        self.assertLess(result.getpixel((40,40))[3],255)
        self.assertEqual(result.getpixel((40,40))[:3],image.getpixel((40,40))[:3])
        self.assertFalse(info['exactCharacterMatte'])
        with self.assertRaises(ValueError):remove_floor_chroma(image,observation,(255,255,255))
        with self.assertRaises(ValueError):remove_floor_chroma(image,observation,(123,209,75),hue_feather=0)

    def test_saturated_floor_key_preserves_neutral_garments_with_matching_hue(self):
        observation={'mode':'solid','rect':[0,0,40,40],'anchor':[20,20]}
        for key,cloth in [((255,0,255),(120,108,120)),((123,209,75),(110,120,106))]:
            image=Image.new('RGBA',(40,40),(*key,255))
            ImageDraw.Draw(image).rectangle((10,5,29,30),fill=(*cloth,255))
            before=image.tobytes()
            result,info=remove_floor_chroma(image,observation,key)
            self.assertEqual(result.getpixel((20,20)),(*cloth,255))
            self.assertEqual(result.getpixel((2,2))[3],0)
            self.assertEqual(info['minSaturation'],.5)
            self.assertEqual(image.tobytes(),before)

    def test_tiled_cell_center_preserves_floating_ground_anchor(self):
        assets={'cellSize':128,'tiles':[{'id':'jump','image':'characters/jump.png','size':[192,320],'anchor':[96,248]}]}
        scene={'width':3,'height':2,'roadColumns':[],'groundAnchorAlignment':'center','objects':[{'tileId':'jump','col':1,'row':1}]}
        with tempfile.TemporaryDirectory() as directory:
            tiled=export_tiled(scene,assets,Path(directory)/'scene.tmj')
        obj=tiled['layers'][1]['objects'][0];offset=tiled['tilesets'][1]['tileoffset']
        self.assertEqual([obj['x'],obj['y']],[192,192])
        self.assertEqual(offset,{'x':0,'y':72})
        self.assertEqual(obj['y']-320+offset['y']+248,192)


if __name__=='__main__':unittest.main()
