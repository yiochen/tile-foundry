"""Synthetic material processor fixtures; these do not assess generated artwork."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageChops, ImageDraw

SKILL = Path(__file__).resolve().parents[1] / "skills/build-overlap-tiles"
sys.path.insert(0, str(SKILL / "scripts"))
from assemble_result import assemble
from material_animation import BACKGROUND, compose, write_guide
from svg_tools import materialize, rasterize


class MaterialAnimationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.guide_path = self.root / "material-guide.json"
        self.guide = write_guide(self.root / "material-guide", sample_size=8, gutter=4, margin=2)
        self.template = self.root / "template"
        self.template.mkdir()
        # A plain raised surface, without studs. Decorative art deliberately
        # reaches every frame edge, beyond the logical ground footprint.
        self.opening = '<svg xmlns="http://www.w3.org/2000/svg" width="30" height="44" viewBox="0 0 30 44">'
        self.top = '<rect x="5" y="12" width="20" height="20" fill="#ee712c"/>'
        self.front = '<rect x="5" y="32" width="20" height="8" fill="#9c3619"/>'
        self.extra = ('<rect width="30" height="4" fill="#ed863a"/>'
                      '<rect y="42" width="30" height="2" fill="#ed863a" opacity=".5"/>')
        svg = self.opening + self.top + self.front + self.extra + "</svg>"
        (self.template / "shaded.svg").write_text(svg)
        rasterize(svg).save(self.template / "shaded.png")
        for name, content in (("top", self.top), ("front", self.front), ("studs", "")):
            rasterize(self.opening + content + "</svg>").getchannel("A").save(self.template / f"mask-{name}.png")
        self.geometry = {"version": 1, "primitive": "authored-raised-surface", "size": [30, 44],
                         "anchor": [15, 40], "cellSize": [20, 20], "height": 8,
                         "bodyRect": [5, 12, 25, 40], "topRect": [5, 12, 25, 32],
                         "frontRect": [5, 32, 25, 40]}
        (self.template / "geometry.json").write_text(json.dumps(self.geometry))
        self.source = self.root / "source.png"
        self.write_source(self.source)
        self.output = self.root / "processed"

    def write_source(self, path, side=96):
        image = Image.new("RGBA", (side, side), BACKGROUND)
        draw = ImageDraw.Draw(image)
        factor = side / self.guide["size"][0]
        for index, cell in enumerate(self.guide["cells"]):
            box = [round(v * factor) for v in cell["rect"]]
            for y in range(box[1], box[3]):
                for x in range(box[0], box[2]):
                    grain = (index + 1) * (1 if (x + y) % 2 else -1)
                    draw.point((x, y), fill=(120 + grain, 70 + grain, 45 + grain, 255))
        image.save(path)

    def process(self, **kwargs):
        return compose(self.template, self.source, self.guide_path, self.output, **kwargs)

    def test_guide_is_fully_opaque_square_with_twelve_exact_square_samples(self):
        default = write_guide(self.root / "default")
        self.assertEqual(default["size"], [1024, 1024])
        self.assertEqual((default["columns"], default["rows"]), (4, 3))
        self.assertEqual(default["margin"], [16, 144])
        self.assertFalse(default["generationRequirements"]["transparent_background"])
        self.assertEqual(len(default["cells"]), 12)
        with Image.open(self.root / "default.png") as opened:
            image = opened.convert("RGBA")
        self.assertEqual(image.size, (1024, 1024))
        self.assertEqual(image.getchannel("A").getextrema(), (255, 255))
        for index, cell in enumerate(default["cells"]):
            x = 16 + (index % 4) * 256
            y = 144 + (index // 4) * 256
            self.assertEqual(cell, {"index": index, "rect": [x, y, x + 224, y + 224]})
            self.assertEqual(image.crop(tuple(cell["rect"])).getextrema(), ((144, 144), (144, 144), (138, 138), (255, 255)))
        for point in ((0, 0), (1023, 1023), (240, 144), (239, 368), (512, 128)):
            self.assertEqual(image.getpixel(point), (222, 222, 219, 255))
        self.assertIn('fill="#dededb"', (self.root / "default.svg").read_text())

    def test_guide_requires_integer_centered_squares_and_preserves_prior_attempts(self):
        with self.assertRaisesRegex(ValueError, "even"):
            write_guide(self.root / "odd", sample_size=7, gutter=4)
        with self.assertRaisesRegex(ValueError, "positive"):
            write_guide(self.root / "zero", gutter=0)
        original = self.guide_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "already exists"):
            write_guide(self.root / "material-guide")
        self.assertEqual(self.guide_path.read_bytes(), original)

    def test_translucent_source_even_only_a_margin_pixel_is_refused(self):
        with Image.open(self.source) as opened:
            source = opened.convert("RGBA")
        source.putpixel((0, 0), (222, 222, 219, 254))
        source.save(self.source)
        with self.assertRaisesRegex(ValueError, "fully opaque"):
            self.process()
        self.assertFalse(self.output.exists())

    def test_rectangular_source_is_refused_without_axis_stretching(self):
        Image.new("RGB", (96, 64), "red").save(self.source)
        with self.assertRaisesRegex(ValueError, "must be square"):
            self.process()
        self.assertFalse(self.output.exists())

    def test_metadata_retains_complete_frames_timing_anchor_and_exact_provenance(self):
        source_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()
        result = self.process()
        self.assertEqual(result["fps"], 12)
        self.assertEqual(result["sourceSize"], [96, 96])
        self.assertEqual(result["guideSize"], [48, 48])
        self.assertEqual(result["uniformSourceScale"], 2)
        self.assertEqual(result["sourceRects"], [[v * 2 for v in c["rect"]] for c in self.guide["cells"]])
        self.assertEqual(len(result["frames"]), 12)
        for index, frame in enumerate(result["frames"]):
            self.assertEqual(frame["index"], index)
            self.assertEqual(frame["size"], [30, 44])
            self.assertEqual(frame["footprint"], [20, 20])
            self.assertEqual(frame["anchor"], [15, 30])
            self.assertEqual(frame["templateNearEdgeAnchor"], [15, 40])
            self.assertEqual(frame["durationMs"], 1000 / 12)
            self.assertEqual(frame["artRect"], [0, 0, 30, 44])
        self.assertEqual(result["anchorConversion"]["offset"], [0, -10])
        self.assertFalse(result["anchorConversion"]["artMoved"])
        self.assertEqual(result["provenance"]["source"]["sha256"], source_hash)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), source_hash)
        for name in ("top", "front", "studs"):
            mask = result["provenance"]["masks"][name]
            self.assertEqual(mask["size"], [30, 44])
            self.assertEqual(mask["sha256"], hashlib.sha256((self.template / f"mask-{name}.png").read_bytes()).hexdigest())
        self.assertIn("Authored SVG palette", result["materialProcessing"]["colorBehavior"])
        self.assertIn("no synthesized motion", result["materialProcessing"]["motion"])
        self.assertEqual(json.loads((self.output / "result.json").read_text()), result)

    def test_full_svg_alpha_and_all_extended_art_survive_every_frame(self):
        result = self.process()
        with Image.open(self.template / "shaded.png") as opened:
            base = opened.convert("RGBA")
        self.assertEqual(base.getchannel("A").getextrema(), (0, 255))
        self.assertEqual(base.getpixel((0, 43))[3], 128)
        with Image.open(self.output / "sheet.png") as opened:
            sheet = opened.convert("RGBA")
        self.assertEqual(sheet.size, (120, 132))
        for index, frame in enumerate(result["frames"]):
            with Image.open(self.output / frame["image"]) as opened:
                image = opened.convert("RGBA")
            self.assertEqual(image.getchannel("A").tobytes(), base.getchannel("A").tobytes())
            self.assertEqual(image.getpixel((0, 0)), base.getpixel((0, 0)))
            self.assertEqual(image.getpixel((29, 43)), base.getpixel((29, 43)))
            left, top = (index % 4) * 30, (index // 4) * 44
            self.assertEqual(sheet.crop((left, top, left + 30, top + 44)).tobytes(), image.tobytes())

    def test_each_supplied_phase_is_materialized_without_synthesized_changes(self):
        result = self.process(strength=1)
        with Image.open(self.source) as opened:
            source = opened.convert("RGBA")
        with Image.open(self.template / "shaded.png") as opened:
            base = opened.convert("RGBA")
        masks = {}
        for name in ("top", "front", "studs"):
            with Image.open(self.template / f"mask-{name}.png") as opened:
                masks[name] = opened.convert("L")
        phase_bytes = []
        for frame in result["frames"]:
            texture = source.crop(tuple(map(int, frame["sourceRect"])))
            expected = materialize(base, texture, masks, strength=1)
            with Image.open(self.output / frame["image"]) as opened:
                actual = opened.convert("RGBA")
            self.assertIsNone(ImageChops.difference(expected, actual).getbbox())
            self.assertEqual(expected.tobytes(), actual.tobytes())
            phase_bytes.append(actual.tobytes())
        self.assertEqual(len(set(phase_bytes)), 12)

    def test_noninteger_square_source_mapping_keeps_one_uniform_scale(self):
        self.write_source(self.source, side=101)
        result = self.process()
        scale = 101 / 48
        self.assertEqual(result["uniformSourceScale"], scale)
        self.assertEqual(result["sampleRasterSize"], [17, 17])
        for guide_rect, source_rect in zip(result["guideRects"], result["sourceRects"]):
            self.assertEqual(source_rect, [v * scale for v in guide_rect])
            self.assertAlmostEqual(source_rect[2] - source_rect[0], source_rect[3] - source_rect[1])
        with Image.open(self.source) as source:
            self.assertEqual(source.size, (101, 101))

    def test_invalid_template_geometry_or_masks_is_refused_instead_of_clipping(self):
        geometry = dict(self.geometry, bodyRect=[-1, 12, 25, 40])
        (self.template / "geometry.json").write_text(json.dumps(geometry))
        with self.assertRaisesRegex(ValueError, "exceeds the frame"):
            self.process()
        self.assertFalse(self.output.exists())
        (self.template / "geometry.json").write_text(json.dumps(self.geometry))
        Image.new("L", (30, 44), 255).save(self.template / "mask-top.png")
        with self.assertRaisesRegex(ValueError, "outside the SVG alpha"):
            self.process()
        self.assertFalse(self.output.exists())

    def test_object_guide_overlapping_samples_and_mismatched_raster_are_refused(self):
        bad = dict(self.guide, kind="object-sheet")
        self.guide_path.write_text(json.dumps(bad))
        with self.assertRaisesRegex(ValueError, "not object panels"):
            self.process()
        bad = json.loads(json.dumps(self.guide))
        bad["cells"][1]["rect"] = bad["cells"][0]["rect"]
        self.guide_path.write_text(json.dumps(bad))
        with self.assertRaisesRegex(ValueError, "overlap"):
            self.process()
        self.guide_path.write_text(json.dumps(self.guide))
        Image.new("RGBA", (30, 44), "red").save(self.template / "shaded.png")
        with self.assertRaisesRegex(ValueError, "exactly match"):
            self.process()

    def test_processor_result_assembles_as_animation_and_preserves_previous_output(self):
        self.process()
        registration = self.root / "registration.json"
        registration.write_text(json.dumps({"kind": "animation", "projection": "top-down-oblique-square-grid",
                                             "elevationPx": 8, "occupiedCells": [[0, 0]]}))
        result = assemble([self.output / "result.json"], registration, self.root / "result.json")
        self.assertEqual(result["fps"], 12)
        self.assertEqual(len(result["sprites"]), 12)
        self.assertTrue(all(s["anchor"] == [15, 30] and s["durationMs"] == 1000 / 12 for s in result["sprites"]))
        frame_hash = hashlib.sha256((self.output / "frames/frame-00.png").read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "empty"):
            self.process()
        self.assertEqual(hashlib.sha256((self.output / "frames/frame-00.png").read_bytes()).hexdigest(), frame_hash)

    def test_copied_skill_cli_runs_from_unrelated_directory(self):
        foreign = self.root / "unrelated-project"
        foreign.mkdir()
        bundle = foreign / "copied-skill"
        shutil.copytree(SKILL, bundle, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        helper = bundle / "scripts/material_animation.py"
        stem = foreign / "guide"
        subprocess.run([sys.executable, str(helper), "guide", str(stem), "--sample-size", "8",
                        "--gutter", "4", "--margin", "2"], cwd=foreign, check=True, capture_output=True)
        shutil.copytree(self.template, foreign / "template")
        shutil.copy2(self.source, foreign / "source.png")
        processed = foreign / "processed"
        subprocess.run([sys.executable, str(helper), "compose", str(foreign / "template"),
                        str(foreign / "source.png"), str(stem.with_suffix(".json")), str(processed)],
                       cwd=foreign, check=True, capture_output=True)
        registration = foreign / "registration.json"
        registration.write_text(json.dumps({"kind": "animation", "projection": "top-down-oblique-square-grid",
                                             "elevationPx": 8, "occupiedCells": [[0, 0]]}))
        subprocess.run([sys.executable, str(bundle / "scripts/assemble_result.py"),
                        "--input-result", str(processed / "result.json"), "--registration", str(registration),
                        "--output", str(foreign / "result.json")], cwd=foreign, check=True, capture_output=True)
        result = json.loads((foreign / "result.json").read_text())
        self.assertEqual(len(result["sprites"]), 12)
        self.assertTrue(all(s["size"] == [30, 44] and s["anchor"] == [15, 30] for s in result["sprites"]))


if __name__ == "__main__":
    unittest.main()
