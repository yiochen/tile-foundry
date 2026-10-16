"""Synthetic fixtures for authored texture motion; no AI quality claims."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, PngImagePlugin

SKILL = Path(__file__).resolve().parents[1] / "skills/build-overlap-tiles"
sys.path.insert(0, str(SKILL / "scripts"))
from material_flow import _distance_mask, _shift_texture, compose
from svg_tools import materialize, rasterize


class MaterialFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.template = self.root / "template"
        self.template.mkdir()
        # Art beyond the footprint reaches all four frame edges. Bottom-edge
        # semitransparency verifies that composition cannot discard its matte.
        opening = '<svg xmlns="http://www.w3.org/2000/svg" width="60" height="84" viewBox="0 0 60 84">'
        top = '<rect x="8" y="12" width="44" height="44" fill="#df702c"/>'
        front = '<rect x="8" y="56" width="44" height="20" fill="#9c3619"/>'
        extra = '<rect width="60" height="4" fill="#ed863a"/><rect y="82" width="60" height="2" fill="#ed863a" opacity=".5"/>'
        svg = opening + top + front + extra + "</svg>"
        (self.template / "shaded.svg").write_text(svg)
        self.base = rasterize(svg)
        self.base.save(self.template / "shaded.png")
        self.masks = {}
        for name, content in (("top", top), ("front", front), ("studs", "")):
            self.masks[name] = rasterize(opening + content + "</svg>").getchannel("A")
            self.masks[name].save(self.template / f"mask-{name}.png")
        self.geometry = {"version": 1, "primitive": "authored-raised-surface", "size": [60, 84],
                         "anchor": [30, 76], "cellSize": [44, 44], "height": 20,
                         "bodyRect": [8, 12, 52, 76], "topRect": [8, 12, 52, 56],
                         "frontRect": [8, 56, 52, 76]}
        (self.template / "geometry.json").write_text(json.dumps(self.geometry))
        self.source = self.root / "source.png"
        self.write_source()
        self.output = self.root / "processed"

    def write_source(self, side=96):
        image = Image.new("RGBA", (side, side))
        image.putdata([((x * 67 + y * 23 + x * y * 17) % 161 + 40,
                        (x * 31 + y * 71 + x * y * 29) % 151 + 45,
                        (x * 47 + y * 53 + x * y * 13) % 141 + 50, 255)
                       for y in range(side) for x in range(side)])
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("prompt", "Synthetic full-square fixture; source bytes and prompt must survive.")
        image.save(self.source, pnginfo=metadata)

    def process(self, **kwargs):
        return compose(self.template, self.source, self.output, **kwargs)

    def frame(self, entry):
        with Image.open(self.output / entry["image"]) as image:
            return image.convert("RGBA")

    def test_translucent_pixel_square_and_non_png_sources_are_refused(self):
        with Image.open(self.source) as opened:
            source = opened.convert("RGBA")
        source.putpixel((95, 95), (123, 45, 67, 254))
        source.save(self.source)
        with self.assertRaisesRegex(ValueError, "fully opaque"):
            self.process()
        self.assertFalse(self.output.exists())
        Image.new("RGB", (96, 95), "red").save(self.source)
        with self.assertRaisesRegex(ValueError, "must be square"):
            self.process()
        self.assertFalse(self.output.exists())
        Image.new("RGB", (96, 96), "red").save(self.source, format="JPEG")
        with self.assertRaisesRegex(ValueError, "source PNG"):
            self.process()
        self.assertFalse(self.output.exists())

    def test_source_bytes_complete_square_and_authored_motion_provenance(self):
        original = self.source.read_bytes()
        result = self.process()
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(result["sourceRect"], [0, 0, 96, 96])
        self.assertEqual(result["sourceSize"], [96, 96])
        self.assertEqual(result["workflow"], "authored-periodic-material-flow")
        source = result["provenance"]["source"]
        self.assertEqual(source["sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(source["sourceRect"], [0, 0, 96, 96])
        self.assertEqual(source["role"], "single-appearance-material-texture")
        self.assertFalse(source["modelGeneratedAnimation"])
        self.assertFalse(result["materialProcessing"]["sourceEdited"])
        self.assertFalse(result["materialProcessing"]["sourceCropped"])
        self.assertIn("not animation phases or poses", result["materialProcessing"]["motion"])
        self.assertIn("Independent LLM", result["visualReviewRequired"])
        self.assertEqual(json.loads((self.output / "result.json").read_text()), result)
        for key, name in (("templateGeometry", "geometry.json"), ("templateSVG", "shaded.svg"),
                          ("templateRaster", "shaded.png")):
            self.assertEqual(result["provenance"][key]["sha256"],
                             hashlib.sha256((self.template / name).read_bytes()).hexdigest())
        for name, record in result["provenance"]["masks"].items():
            self.assertEqual(record["sha256"], hashlib.sha256((self.template / f"mask-{name}.png").read_bytes()).hexdigest())
        stabilization = result["materialProcessing"]["boundaryStabilization"]
        self.assertEqual(stabilization["edgeBandLogicalPx"], 16)
        for record in [stabilization["mask"], *stabilization["faceMasks"].values()]:
            self.assertEqual(record["sha256"], hashlib.sha256((self.output / record["path"]).read_bytes()).hexdigest())

    def test_exact_full_frame_alpha_root_timing_and_no_clipping(self):
        result = self.process()
        self.assertEqual((result["fps"], len(result["frames"])), (12, 12))
        self.assertEqual(result["groundAnchorAlignment"], "center")
        self.assertEqual(result["anchorConversion"]["offset"], [0, -22])
        self.assertFalse(result["anchorConversion"]["artMoved"])
        with Image.open(self.output / "sheet.png") as opened:
            sheet = opened.convert("RGBA")
        self.assertEqual(sheet.size, (240, 252))
        for index, entry in enumerate(result["frames"]):
            frame = self.frame(entry)
            self.assertEqual(entry["size"], [60, 84])
            self.assertEqual(entry["footprint"], [44, 44])
            self.assertEqual(entry["anchor"], [30, 54])
            self.assertEqual(entry["templateNearEdgeAnchor"], [30, 76])
            self.assertEqual(entry["durationMs"], 1000 / 12)
            self.assertEqual(entry["sourceRect"], [0, 0, 96, 96])
            self.assertEqual(entry["artRect"], [0, 0, 60, 84])
            self.assertTrue(entry["alphaPreserved"])
            self.assertEqual(frame.getchannel("A").tobytes(), self.base.getchannel("A").tobytes())
            self.assertEqual(frame.getpixel((0, 0)), self.base.getpixel((0, 0)))
            self.assertEqual(frame.getpixel((59, 83)), self.base.getpixel((59, 83)))
            self.assertEqual(frame.getpixel((59, 83))[3], 128)
            x, y = (index % 4) * 60, (index // 4) * 84
            self.assertEqual(sheet.crop((x, y, x + 60, y + 84)).tobytes(), frame.tobytes())

    def test_periodic_shift_retains_all_pixels_and_closes_exactly(self):
        self.write_source(side=97)
        with Image.open(self.source) as opened:
            source = opened.convert("RGBA")
        initial, _ = _shift_texture(source, 0)
        closure, offset = _shift_texture(source, 12)
        self.assertEqual(closure.tobytes(), initial.tobytes())
        self.assertEqual(offset, 0)
        self.assertEqual(materialize(self.base, closure, self.masks).tobytes(),
                         materialize(self.base, initial, self.masks).tobytes())
        for phase in range(12):
            shifted, applied = _shift_texture(source, phase)
            self.assertEqual(applied, round(97 * phase / 12))
            self.assertEqual(Counter(shifted.getdata()), Counter(source.getdata()))
            for point in ((0, 0), (96, 0), (0, 96), (53, 47)):
                self.assertEqual(shifted.getpixel(point), source.getpixel(((point[0] - applied) % 97, point[1])))
        result = self.process()
        for phase, shift in enumerate(result["uvShifts"]):
            self.assertEqual(shift["appliedXPixels"], round(97 * phase / 12))
            self.assertEqual(shift["requestedXPixels"], 97 * phase / 12)
        self.assertTrue(result["materialProcessing"]["translation"]["frame12EqualsFrame0"])
        self.assertIn("ties to even", result["materialProcessing"]["translation"]["rounding"])

    def test_every_authored_boundary_stays_static_while_interior_moves(self):
        result = self.process(strength=1)
        frames = [self.frame(entry) for entry in result["frames"]]
        with Image.open(self.source) as source:
            expected_zero = materialize(self.base, source, self.masks, 1)
        self.assertEqual(frames[0].tobytes(), expected_zero.tobytes())
        boundary = set()
        for x0, y0, x1, y1 in (self.geometry["topRect"], self.geometry["frontRect"]):
            boundary.update((x, y) for x in range(x0, x1) for y in (y0, y1 - 1))
            boundary.update((x, y) for x in (x0, x1 - 1) for y in range(y0, y1))
        for point in boundary:
            self.assertEqual({frame.getpixel(point) for frame in frames}, {frames[0].getpixel(point)}, point)
        self.assertGreater(len({frame.getpixel((30, 34)) for frame in frames}), 1)
        self.assertEqual(len({frame.tobytes() for frame in frames}), 12)
        self.assertEqual(result["diagnostics"]["distinctFrameCount"], 12)

    def test_distance_fade_is_smooth_in_logical_pixels_including_frame_edges(self):
        mask = _distance_mask(Image.new("L", (41, 41), 255), 16)
        self.assertEqual(mask.getpixel((0, 20)), 0)
        self.assertEqual(mask.getpixel((40, 20)), 0)
        self.assertEqual(mask.getpixel((20, 0)), 0)
        self.assertEqual(mask.getpixel((20, 40)), 0)
        self.assertEqual(mask.getpixel((8, 20)), 128)
        self.assertEqual(mask.getpixel((16, 20)), 255)
        self.assertEqual(mask.getpixel((20, 20)), 255)
        values = [mask.getpixel((x, 20)) for x in range(17)]
        self.assertEqual(values, sorted(values))
        self.assertLess(values[1] - values[0], values[8] - values[7])
        self.assertLess(values[16] - values[15], values[8] - values[7])

    def test_flat_source_reports_duplicate_frames_without_fabricated_motion(self):
        Image.new("RGB", (96, 96), (90, 70, 50)).save(self.source)
        result = self.process()
        self.assertEqual(len(result["frames"]), 12)
        self.assertEqual(result["diagnostics"]["distinctFrameCount"], 1)
        self.assertFalse(result["diagnostics"]["motionObserved"])
        for entry in result["frames"]:
            self.assertEqual(self.frame(entry).tobytes(), self.base.tobytes())

    def test_invalid_parameters_and_out_of_frame_geometry_are_refused(self):
        for edge_band in (0, -1, float("nan"), float("inf"), True):
            with self.subTest(edge_band=edge_band), self.assertRaisesRegex(ValueError, "Edge band"):
                self.process(edge_band=edge_band)
        for strength in (-.1, 1.1, float("nan"), True):
            with self.subTest(strength=strength), self.assertRaisesRegex(ValueError, "Strength"):
                self.process(strength=strength)
        (self.template / "geometry.json").write_text(json.dumps(dict(self.geometry, bodyRect=[-1, 12, 52, 76])))
        with self.assertRaisesRegex(ValueError, "exceeds the frame"):
            self.process()
        self.assertFalse(self.output.exists())

    def test_existing_attempt_is_preserved(self):
        self.process()
        original = (self.output / "result.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "empty"):
            self.process()
        self.assertEqual((self.output / "result.json").read_bytes(), original)

    def test_copied_bundle_cli_and_assemble_run_from_unrelated_directory(self):
        foreign = self.root / "unrelated-project"
        foreign.mkdir()
        bundle = foreign / "copied-skill"
        shutil.copytree(SKILL, bundle, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(self.template, foreign / "template")
        shutil.copy2(self.source, foreign / "source.png")
        processed = foreign / "processed"
        subprocess.run([sys.executable, str(bundle / "scripts/material_flow.py"), "compose",
                        str(foreign / "template"), str(foreign / "source.png"), str(processed),
                        "--strength", ".7", "--edge-band", "16"],
                       cwd=foreign, check=True, capture_output=True)
        registration = foreign / "registration.json"
        registration.write_text(json.dumps({"kind": "animation", "projection": "top-down-oblique-square-grid",
                                             "elevationPx": 20, "occupiedCells": [[0, 0]]}))
        subprocess.run([sys.executable, str(bundle / "scripts/assemble_result.py"),
                        "--input-result", str(processed / "result.json"), "--registration", str(registration),
                        "--output", str(foreign / "result.json")], cwd=foreign, check=True, capture_output=True)
        result = json.loads((foreign / "result.json").read_text())
        self.assertEqual(result["fps"], 12)
        self.assertEqual(len(result["sprites"]), 12)
        self.assertTrue(all(sprite["size"] == [60, 84] and sprite["anchor"] == [30, 54] and
                            sprite["durationMs"] == 1000 / 12 and
                            sprite["processing"]["sourceRect"] == [0, 0, 96, 96]
                            for sprite in result["sprites"]))
        self.assertEqual((foreign / "source.png").read_bytes(), self.source.read_bytes())


if __name__ == "__main__":
    unittest.main()
