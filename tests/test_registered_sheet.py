"""Synthetic fixed-layout extraction checks, not judgments of AI reskin quality."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

SCRIPT = Path(__file__).resolve().parents[1] / "skills/build-overlap-tiles/scripts/extract_registered_sheet.py"
sys.path.insert(0, str(SCRIPT.parent))
from extract_registered_sheet import extract


class RegisteredSheetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.png"
        self.guide_path = self.root / "guide.json"
        self.output = self.root / "processed"
        self.guide = {
            "version": 1, "kind": "rendered-3d-sheet", "assetKind": "animation",
            "size": [40, 44], "frame": [12, 16], "cellSize": 8, "anchor": [6, 12],
            "captureScale": 1, "gutter": 4, "columns": 2, "occupiedCells": [[0, 0]],
            "elevationPx": 10,
            "cells": [{"index": i, "rect": [6 + (i % 2) * 16, 4 + (i // 2) * 20,
                                                18 + (i % 2) * 16, 20 + (i // 2) * 20],
                       "durationMs": 1000 / 12} for i in range(4)],
        }
        self.guide_path.write_text(json.dumps(self.guide))
        self.original = Image.new("RGBA", tuple(self.guide["size"]))
        draw = ImageDraw.Draw(self.original)
        for i, cell in enumerate(self.guide["cells"]):
            x, y, _, _ = cell["rect"]
            draw.rectangle((x + 3, y + 3, x + 8, y + 12), fill=(42 + 20 * i, 89, 125, 255))
            draw.point((x + 2, y + 5), fill=(135, 57, 24, 91))
            draw.point((x + 9, y + 7), fill=(37, 201, 71, 1))
            # Fully transparent generated RGB is retained in exact extraction.
            draw.point((x + 1, y + 1), fill=(93, 51, 27, 0))
        self.original.save(self.source)

    def process(self, **kwargs):
        return extract(self.source, self.guide_path, self.output, **kwargs)

    def write_guide(self):
        self.guide_path.write_text(json.dumps(self.guide))

    def test_exact_panels_preserve_every_rgba_pixel_and_full_blank_padding(self):
        source_bytes = self.source.read_bytes()
        result = self.process()
        for cell, entry in zip(self.guide["cells"], result["sprites"]):
            expected = self.original.crop(cell["rect"])
            with Image.open(self.output / entry["image"]) as opened:
                actual = opened.convert("RGBA")
            self.assertEqual(actual.size, (12, 16))
            self.assertEqual(actual.tobytes(), expected.tobytes())
            self.assertEqual(actual.getpixel((2, 5))[3], 91)
            self.assertEqual(actual.getpixel((9, 7))[3], 1)
            self.assertEqual(actual.getpixel((1, 1)), (93, 51, 27, 0))
        self.assertEqual(self.source.read_bytes(), source_bytes)
        self.assertEqual(result["cleanup"]["removedAlphaMass"], 0)
        self.assertFalse(result["cleanup"]["rendererMaskApplied"])
        self.assertFalse(result["cleanup"]["colorKeyApplied"])
        self.assertEqual(result["panelIsolation"]["maximumOutsideAlphaBeforeThreshold"], 0)

    def test_runtime_contract_retains_authored_root_footprint_order_and_timing(self):
        result = self.process()
        self.assertEqual(result["version"], 2)
        self.assertEqual(result["kind"], "animation")
        self.assertEqual(result["fps"], 12)
        self.assertEqual(result["groundAnchorAlignment"], "center")
        self.assertEqual(result["registration"]["method"], "authored-3d-projection")
        self.assertIn("require independent visual review", result["geometryDeclaration"])
        for i, sprite in enumerate(result["sprites"]):
            self.assertEqual(sprite["index"], i)
            self.assertEqual(sprite["anchor"], [6, 12])
            self.assertEqual(sprite["footprint"], [8, 8])
            self.assertEqual(sprite["occupiedCells"], [[0, 0]])
            self.assertEqual(sprite["elevationPx"], 10)
            self.assertEqual(sprite["role"], "player")
            self.assertEqual(sprite["durationMs"], 1000 / 12)
            self.assertFalse(sprite["normalization"]["perPoseFitting"])
            self.assertEqual(sprite["normalization"]["scale"], [1, 1])
        self.assertEqual(json.loads((self.output / "result.json").read_text()), result)
        self.assertEqual(result["provenance"]["source"]["sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(result["provenance"]["guide"]["sha256"], hashlib.sha256(self.guide_path.read_bytes()).hexdigest())

    def test_static_mode_retains_one_authored_object_without_animation_metadata(self):
        self.guide.update(assetKind='object',size=[24,32],frame=[12,16],captureScale=2,
                          gutter=0,columns=1,cells=[{'index':0,'rect':[0,0,24,32]}])
        self.write_guide()
        source=Image.new('RGBA',(24,32));ImageDraw.Draw(source).rectangle((7,8,16,25),fill='orange')
        source.save(self.source)
        result=self.process()
        self.assertEqual(result['kind'],'object')
        self.assertNotIn('fps',result)
        self.assertEqual(len(result['sprites']),1)
        sprite=result['sprites'][0]
        self.assertEqual(sprite['role'],'object')
        self.assertEqual(sprite['anchor'],[6,12])
        self.assertNotIn('direction',sprite)
        self.assertNotIn('durationMs',sprite)

    def test_output_sheet_is_exact_full_frame_concatenation(self):
        result = self.process()
        with Image.open(self.output / "sheet.png") as opened:
            sheet = opened.convert("RGBA")
        self.assertEqual(sheet.size, (24, 32))
        for i, frame in enumerate(result["frames"]):
            x, y = (i % 2) * 12, (i // 2) * 16
            with Image.open(self.output / frame["image"]) as opened:
                expected = opened.convert("RGBA")
            self.assertEqual(sheet.crop((x, y, x + 12, y + 16)).tobytes(), expected.tobytes())

    def test_whole_image_scale_and_capture_scale_use_one_uniform_sampling_factor(self):
        # The reference render is 2x runtime, then the generated whole source is
        # 3x reference. No per-subject bounds or scales enter extraction.
        self.guide["captureScale"] = 2
        self.guide["size"] = [v * 2 for v in self.guide["size"]]
        self.guide["gutter"] *= 2
        for cell in self.guide["cells"]:
            cell["rect"] = [v * 2 for v in cell["rect"]]
        self.write_guide()
        self.original.resize((240, 264), Image.Resampling.NEAREST).save(self.source)
        source_bytes = self.source.read_bytes()
        result = self.process()
        self.assertEqual(result["uniformSourceScale"], 3)
        for sprite, cell in zip(result["sprites"], self.guide["cells"]):
            self.assertEqual(sprite["registration"]["sourceRect"], [v * 3 for v in cell["rect"]])
            self.assertEqual(sprite["normalization"]["scale"], [1 / 6] * 2)
            with Image.open(self.source) as opened:
                expected = opened.convert("RGBA").transform((12, 16), Image.Transform.EXTENT,
                                                            sprite["registration"]["sourceRect"], Image.Resampling.BICUBIC)
            with Image.open(self.output / sprite["image"]) as opened:
                self.assertEqual(opened.convert("RGBA").tobytes(), expected.tobytes())
        self.assertEqual(self.source.read_bytes(), source_bytes)

    def test_only_integer_rounding_tolerance_permits_nonsquare_axis_ratios(self):
        self.original.resize((81, 89), Image.Resampling.NEAREST).save(self.source)
        result = self.process()
        expected = (81 * 40 + 89 * 44) / (40 ** 2 + 44 ** 2)
        self.assertEqual(result["uniformSourceScale"], expected)
        self.assertNotEqual(81 / 40, 89 / 44)
        self.assertTrue(result["normalization"]["equalAxisScale"])
        for frame in result["frames"]:
            self.assertEqual(frame["normalization"]["scale"][0], frame["normalization"]["scale"][1])

    def test_aspect_drift_cannot_be_repaired_by_stretching(self):
        self.original.resize((80, 92), Image.Resampling.NEAREST).save(self.source)
        with self.assertRaisesRegex(ValueError, "whole-sheet aspect"):
            self.process()
        self.assertFalse(self.output.exists())

    def test_portrait_canvas_rounding_uses_common_scale_before_testing_residuals(self):
        self.guide.update(assetKind="object", size=[384, 640], frame=[192, 320],
                          anchor=[96, 248], captureScale=2, gutter=0, columns=1,
                          cells=[{"index": 0, "rect": [0, 0, 384, 640]}])
        self.write_guide()
        source = Image.new("RGBA", (971, 1620))
        ImageDraw.Draw(source).rectangle((300, 700, 670, 1200), fill="orange")
        source.save(self.source)
        original_bytes = self.source.read_bytes()
        # Extrapolating the rounded width ratio gives a misleading 1.667px
        # height error. Both dimensions are <1px from the one common scalar.
        self.assertGreater(abs(1620 - 640 * (971 / 384)), 1)
        expected_scale = (971 * 384 + 1620 * 640) / (384 ** 2 + 640 ** 2)
        result = self.process()
        self.assertEqual(result["uniformSourceScale"], expected_scale)
        self.assertEqual(result["normalization"]["sourceEdgeResidualPx"],
                         [971 - 384 * expected_scale, 1620 - 640 * expected_scale])
        self.assertTrue(all(abs(value) < 1 for value in result["normalization"]["sourceEdgeResidualPx"]))
        self.assertEqual(result["normalization"]["wholeCanvasOffset"], [0, 0])
        sprite = result["sprites"][0]
        self.assertEqual(sprite["normalization"]["scale"], [1 / (2 * expected_scale)] * 2)
        self.assertFalse(sprite["normalization"]["perPoseFitting"])
        expected = source.transform((192, 320), Image.Transform.EXTENT,
                                    sprite["registration"]["sourceRect"], Image.Resampling.BICUBIC)
        with Image.open(self.output / sprite["image"]) as opened:
            self.assertEqual(opened.convert("RGBA").tobytes(), expected.tobytes())
        self.assertEqual(self.source.read_bytes(), original_bytes)

    def test_portrait_excessive_or_asymmetric_drift_still_rejects(self):
        self.guide.update(assetKind="object", size=[384, 640], frame=[192, 320],
                          anchor=[96, 248], captureScale=2, gutter=0, columns=1,
                          cells=[{"index": 0, "rect": [0, 0, 384, 640]}])
        self.write_guide()
        for dimensions in ((970, 1620), (971, 1624), (975, 1620)):
            with self.subTest(dimensions=dimensions):
                Image.new("RGBA", dimensions).save(self.source)
                with self.assertRaisesRegex(ValueError, "whole-sheet aspect"):
                    self.process()
                self.assertFalse(self.output.exists())

    def test_fractional_outer_panel_rounding_adds_only_declared_transparent_padding(self):
        self.guide.update(size=[24,32],frame=[24,32],captureScale=1,gutter=0,columns=1,
                          cells=[{'index':0,'rect':[0,0,24,32],'durationMs':1000/12}])
        self.write_guide()
        source=Image.new('RGBA',(47,63));ImageDraw.Draw(source).rectangle((8,10,37,51),fill=(80,120,200,255))
        source.save(self.source);before=self.source.read_bytes()
        result=self.process()
        self.assertEqual(result['normalization']['transparentVirtualPaddingLTRB'],[0,0,1,0])
        self.assertEqual(result['normalization']['wholeCanvasOffset'],[0,0])
        entry=result['sprites'][0]
        self.assertEqual(entry['normalization']['scale'][0],entry['normalization']['scale'][1])
        expected=source.transform((24,32),Image.Transform.EXTENT,
            entry['registration']['sourceRect'],Image.Resampling.BICUBIC)
        self.assertEqual(Image.open(self.output/entry['image']).convert('RGBA').tobytes(),expected.tobytes())
        self.assertEqual(self.source.read_bytes(),before)

    def test_virtual_padding_cannot_hide_art_on_the_original_canvas_edge(self):
        self.guide.update(size=[24,32],frame=[24,32],captureScale=1,gutter=0,columns=1,
                          cells=[{'index':0,'rect':[0,0,24,32],'durationMs':1000/12}])
        self.write_guide()
        source=Image.new('RGBA',(47,63));ImageDraw.Draw(source).rectangle((8,10,46,51),fill='red')
        source.save(self.source)
        with self.assertRaisesRegex(ValueError,'original source canvas boundary'):
            self.process()
        self.assertFalse(self.output.exists())

    def test_opaque_or_faint_gutter_content_is_rejected_without_implicit_cleanup(self):
        for alpha in (255, 1):
            image = self.original.copy()
            image.putpixel((0, 0), (40, 50, 60, alpha))
            image.save(self.source)
            with self.assertRaisesRegex(ValueError, "sheet gutter"):
                self.process()
            self.assertFalse(self.output.exists())

    def test_explicit_global_alpha_threshold_records_removed_mass_and_keeps_source(self):
        image = self.original.copy()
        image.putpixel((0, 0), (40, 50, 60, 1))
        image.save(self.source)
        original_bytes = self.source.read_bytes()
        result = self.process(min_alpha=1)
        # Four panel edge pixels plus one gutter pixel, each at alpha 1.
        self.assertEqual(result["cleanup"]["minAlpha"], 1)
        self.assertEqual(result["cleanup"]["removedAlphaMass"], 5)
        self.assertEqual(result["panelIsolation"]["maximumOutsideAlphaBeforeThreshold"], 1)
        self.assertEqual(result["panelIsolation"]["outsideAlphaMassBeforeThreshold"], 1)
        self.assertEqual(result["panelIsolation"]["maximumOutsideAlphaAfterThreshold"], 0)
        with Image.open(self.output / result["sprites"][0]["image"]) as opened:
            self.assertEqual(opened.convert("RGBA").getpixel((9, 7)), (37, 201, 71, 0))
        self.assertEqual(self.source.read_bytes(), original_bytes)
        for value in (-1, 255, True):
            with self.assertRaises(ValueError):
                self.process(min_alpha=value)

    def test_panel_boundary_content_is_rejected_instead_of_silently_clipped(self):
        x, y, _, _ = self.guide["cells"][0]["rect"]
        image = self.original.copy()
        image.putpixel((x, y + 6), (255, 0, 0, 255))
        image.save(self.source)
        with self.assertRaisesRegex(ValueError, "touches.*boundary; clipping risk"):
            self.process()
        self.assertFalse(self.output.exists())

    def test_reflow_that_omits_a_panel_is_rejected_without_subject_search(self):
        image = self.original.copy()
        x0, y0, x1, y1 = self.guide["cells"][2]["rect"]
        ImageDraw.Draw(image).rectangle((x0, y0, x1 - 1, y1 - 1), fill=(0, 0, 0, 0))
        image.save(self.source)
        with self.assertRaisesRegex(ValueError, "empty; layout may have reflowed"):
            self.process()
        self.assertFalse(self.output.exists())

    def test_directions_keep_authored_codes_without_animation_timing(self):
        self.guide["assetKind"] = "directions"
        for cell, direction in zip(self.guide["cells"], ("N", "E", "S", "W")):
            cell["direction"] = direction
            cell.pop("durationMs")
        self.write_guide()
        result = self.process()
        self.assertEqual(result["kind"], "directions")
        self.assertNotIn("fps", result)
        self.assertEqual([s["direction"] for s in result["sprites"]], ["N", "E", "S", "W"])
        self.assertTrue(all("durationMs" not in s and s["anchor"] == [6, 12] for s in result["sprites"]))

    def test_invalid_guide_geometry_or_timing_cannot_change_registration(self):
        original = json.loads(json.dumps(self.guide))
        mutations = (
            lambda guide: guide["cells"][0].update(rect=[6, 4, 19, 20]),
            lambda guide: guide["cells"][1].update(rect=guide["cells"][0]["rect"]),
            lambda guide: guide["cells"][0].update(durationMs=100),
            lambda guide: guide.update(anchor=[6, 99]),
            lambda guide: guide.update(groundAnchorAlignment="near-edge"),
        )
        for mutate in mutations:
            self.guide = json.loads(json.dumps(original))
            mutate(self.guide)
            self.write_guide()
            with self.assertRaises(ValueError):
                self.process()
            self.assertFalse(self.output.exists())

    def test_previous_output_is_preserved_and_single_script_runs_from_foreign_cwd(self):
        foreign = self.root / "other-project"
        foreign.mkdir()
        copied = foreign / "extract_registered_sheet.py"
        shutil.copyfile(SCRIPT, copied)
        subprocess.run([sys.executable, str(copied), str(self.source), str(self.guide_path), str(self.output)],
                       cwd=foreign, capture_output=True, check=True)
        before = (self.output / "result.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "empty; preserve"):
            self.process()
        self.assertEqual((self.output / "result.json").read_bytes(), before)
        self.assertEqual(json.loads(before)["provenance"]["processor"]["sha256"], hashlib.sha256(copied.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
