import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from svgkit import block_svg, rasterize, write_template, materialize, compose
from tilekit import neighbor_coverage


class SvgGeometryTests(unittest.TestCase):
    def test_heights_keep_exact_footprint_anchor_and_opaque_parallel_edges(self):
        for height in (16,32,64,96):
            image = rasterize(block_svg(height=height))
            self.assertEqual(image.getbbox(), (32,312-128-height,160,312))
            alpha = image.getchannel("A")
            self.assertEqual(alpha.crop(image.getbbox()).getextrema(), (255,255))
            self.assertEqual(neighbor_coverage(image,(96,312))[0]["uncoveredPixels"],0)
            for y in range(312-128-height,312):
                self.assertEqual(alpha.crop((0,y,192,y+1)).getbbox(),(32,0,160,1))

    def test_clipping_rejected_and_nondefault_frame_supported(self):
        with self.assertRaises(ValueError):
            block_svg(height=200)
        image = rasterize(block_svg(height=200,frame=(256,512),anchor=(128,504)))
        self.assertEqual(image.getbbox(),(64,176,192,504))

    def test_unaligned_edges_rejected_instead_of_blurring_the_footprint(self):
        with self.assertRaises(ValueError):
            block_svg(width=127)

    def test_face_masks_partition_the_whole_body(self):
        with tempfile.TemporaryDirectory() as directory:
            write_template(directory)
            p = Path(directory)
            top = Image.open(p/"mask-top.png")
            front = Image.open(p/"mask-front.png")
            silhouette = Image.open(p/"mask-silhouette.png")
            self.assertIsNone(ImageChops.darker(top,front).getbbox())
            self.assertIsNone(ImageChops.difference(ImageChops.lighter(top,front),silhouette).getbbox())
            with Image.open(p/"reference-4x.png") as reference:
                self.assertEqual(reference.size,(768,1280))

    def test_extreme_generated_detail_never_changes_alpha_or_leaks(self):
        with tempfile.TemporaryDirectory() as directory:
            write_template(directory,height=64)
            p=Path(directory)
            base=Image.open(p/"shaded.png").convert("RGBA")
            texture=Image.new("RGB",(64,64))
            texture.putdata([(255,255,255) if (x+y)%2 else (0,0,0) for y in range(64) for x in range(64)])
            masks={n:Image.open(p/f"mask-{n}.png") for n in ("top","front","studs")}
            result=materialize(base,texture,masks,strength=1)
            self.assertEqual(result.getchannel("A").tobytes(),base.getchannel("A").tobytes())
            self.assertNotEqual(result.tobytes(),base.tobytes())
            empty=base.getchannel("A").point(lambda a:255 if a==0 else 0)
            self.assertIsNone(ImageChops.multiply(ImageChops.difference(result.convert("RGB"),base.convert("RGB")),Image.merge("RGB",(empty,)*3)).getbbox())

    def test_opaque_texture_and_matching_masks_required(self):
        with tempfile.TemporaryDirectory() as directory:
            write_template(directory)
            p=Path(directory)
            Image.new("RGBA",(32,32),(200,0,0,128)).save(p/"bad.png")
            with self.assertRaises(ValueError):
                compose(p,p/"bad.png",p/"out.png")
            with self.assertRaises(ValueError):
                materialize(Image.new("RGBA",(10,10)),Image.new("RGB",(10,10)),{n:Image.new("L",(2,2)) for n in ("top","front","studs")})


if __name__ == "__main__":
    unittest.main()
