import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from tilekit import crop_alpha, split_grid, component_rects, normalize, pack_atlas, clean_alpha, export_tiled, neighbor_coverage, parallel_edges, validate_assets


class TileGeometryTests(unittest.TestCase):
    def fixture(self):
        image = Image.new("RGBA", (100, 140))
        ImageDraw.Draw(image).rectangle((20, 15, 69, 109), fill=(100, 120, 140, 255))
        return image

    def test_crop_preserves_explicit_ground_anchor(self):
        crop, meta = crop_alpha(self.fixture(), (45, 108), padding=4)
        self.assertEqual(crop.size, (58, 103))
        self.assertEqual(meta["anchor"], [29, 97])
        # Mapping from cropped-local back to source preserves exact ground contact.
        self.assertEqual([meta["anchor"][i] + meta["sourceRect"][i] - 4 for i in (0, 1)], [45, 108])

    def test_normalize_does_not_stretch_height_to_frame(self):
        norm, meta = normalize(self.fixture(), frame=(160, 300), anchor_out=(80, 292), art_width=100,
                               anchor_in=(45, 110))
        self.assertEqual(meta["artRect"][2:], [100, 190])
        self.assertEqual(meta["anchor"], [80, 292])
        self.assertEqual(norm.getpixel((80, 291))[3], 255)

    def test_normalize_rejects_clipping_instead_of_hiding_it(self):
        with self.assertRaisesRegex(ValueError, "exceeds frame"):
            normalize(self.fixture(), frame=(100, 100), anchor_out=(50, 100), art_width=100)

    def test_fractional_source_anchors_share_exact_frame_anchor(self):
        _, meta=normalize(self.fixture(),frame=(192,320),anchor_out=(96,312),art_width=128,
                          anchor_in=(45.4,109.7))
        self.assertEqual(meta["anchor"],[96,312])
        self.assertTrue(any(abs(v)>0.01 for v in meta["subpixelShift"]))

    def test_empty_image_fails(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            crop_alpha(Image.new("RGBA", (20, 20)))

    def test_anchor_can_be_outside_tightly_cropped_art(self):
        _, meta = crop_alpha(self.fixture(), (45, 120))
        self.assertGreater(meta["anchor"][1], meta["size"][1])

    def test_grid_spacing_and_margin_preserve_pixels(self):
        sheet = Image.new("RGBA", (25, 12))
        ImageDraw.Draw(sheet).rectangle((2,2,9,9), fill="red")
        ImageDraw.Draw(sheet).rectangle((13,2,20,9), fill="green")
        parts = split_grid(sheet, (8,8),2,1,margin=2,spacing=3)
        self.assertEqual(parts[0][0].getpixel((0,0)), (255,0,0,255))
        self.assertEqual(parts[1][0].getpixel((7,7)), (0,128,0,255))

    def test_grid_rejects_partial_last_frame(self):
        with self.assertRaisesRegex(ValueError, "refusing truncated"):
            split_grid(Image.new("RGBA", (20,20)), (12,12),2,2)

    def test_component_cuts_find_full_silhouettes(self):
        sheet = Image.new("RGBA", (80,80))
        draw = ImageDraw.Draw(sheet)
        draw.rectangle((5,5,14,24), fill="red")
        draw.rectangle((40,35,59,64), fill="green")
        self.assertEqual(component_rects(sheet), [(5,5,15,25),(40,35,60,65)])

    def test_component_grouping_rejoins_detached_parts(self):
        sheet = Image.new("RGBA", (40,40))
        draw = ImageDraw.Draw(sheet)
        draw.rectangle((5,5,14,14), fill="red")
        draw.rectangle((5,18,14,27), fill="red")
        self.assertEqual(len(component_rects(sheet,join_radius=2)),1)

    def test_alpha_cleanup_keeps_rgb_and_strong_alpha(self):
        image=Image.new("RGBA",(3,1));image.putdata([(1,2,3,10),(4,5,6,100),(7,8,9,255)])
        result, meta=clean_alpha(image,64)
        self.assertEqual([result.getpixel((x,0)) for x in range(3)],[(1,2,3,0),(4,5,6,100),(7,8,9,255)])
        self.assertEqual(meta["removedPixels"],1)

    def test_trimmed_atlas_reconstructs_every_source_pixel(self):
        image=self.fixture()
        image.putpixel((18,12),(40,50,60,2)) # Retain even faint antialias texels in atlas trim.
        atlas, info=pack_atlas([("tile",image,{"anchor":[45,108]})])
        f=info["frames"]["tile"];r=f["frame"];trim=f["spriteSourceSize"]
        restored=Image.new("RGBA",image.size)
        restored.paste(atlas.crop((r["x"],r["y"],r["x"]+r["w"],r["y"]+r["h"])),(trim["x"],trim["y"]))
        self.assertIsNone(ImageChops.difference(restored,image).getbbox())
        self.assertEqual([f["anchor"][0]+trim["x"],f["anchor"][1]+trim["y"]],[45,108])

    def test_extrusion_copies_edge_colors_into_gutter(self):
        image=Image.new("RGBA",(8,8),(32,64,128,255))
        atlas, info=pack_atlas([("tile",image,{"anchor":[4,8]})],padding=4,extrusion=2)
        r=info["frames"]["tile"]["frame"]
        self.assertEqual(atlas.getpixel((r["x"]-2,r["y"]-2)),(32,64,128,255))
        self.assertEqual(atlas.getpixel((r["x"]-3,r["y"]-3))[3],0)

    def test_tiled_bottom_alignment_preserves_ground_anchor(self):
        assets={"cellSize":128,"tiles":[{"id":"tree","image":"sprites/tree.png","size":[192,320],"anchor":[96,312]}]}
        scene={"width":2,"height":2,"roadColumns":[],"objects":[{"tileId":"tree","col":1,"row":1}]}
        with tempfile.TemporaryDirectory() as directory:
            tiled=export_tiled(scene,assets,Path(directory)/"scene.tmj")
        obj=tiled["layers"][1]["objects"][0]
        offset=tiled["tilesets"][1]["tileoffset"]
        self.assertEqual(obj["y"]+offset["y"]-320+312,256)
        self.assertEqual(obj["x"]+offset["x"]-192/2+96,192)
        self.assertEqual(tiled["layers"][1]["draworder"],"topdown")

    def test_solid_cell_check_catches_short_body_despite_correct_width(self):
        image=Image.new("RGBA",(128,112),"red")
        report,_=neighbor_coverage(image,(64,112))
        self.assertFalse(report["ok"])
        self.assertEqual(report["uncoveredPixels"],128*16)
        self.assertEqual(len(report["emptyRows"]),16)

    def test_solid_cell_check_accepts_full_width_overlapping_body(self):
        image=Image.new("RGBA",(128,160),"red")
        report,_=neighbor_coverage(image,(64,160))
        self.assertTrue(report["ok"])
        self.assertEqual(report["uncoveredPixels"],0)
        self.assertTrue(parallel_edges(image)["ok"])

    def test_parallel_check_rejects_perspective_taper(self):
        image=Image.new("RGBA",(128,160))
        ImageDraw.Draw(image).polygon([(16,0),(111,0),(127,159),(0,159)],fill="red")
        report=parallel_edges(image)
        self.assertFalse(report["ok"])
        self.assertGreater(report["widthDelta"],10)

    def test_manifest_alpha_threshold_applies_to_both_solid_checks(self):
        image=Image.new("RGBA",(192,320))
        ImageDraw.Draw(image).rectangle((32,152,159,311),fill=(255,0,0,220))
        assets={"tiles":[{"id":"solid","image":"solid.png","anchor":[96,312],"footprint":[128,128],
                          "solidCell":{"minAlpha":200}}]}
        with tempfile.TemporaryDirectory() as directory:
            image.save(Path(directory)/"solid.png")
            report=validate_assets(assets,directory)
        self.assertTrue(report["ok"])
        self.assertEqual(report["solidChecks"]["solid"]["parallel"]["alphaThreshold"],200)


if __name__ == "__main__":
    unittest.main()
