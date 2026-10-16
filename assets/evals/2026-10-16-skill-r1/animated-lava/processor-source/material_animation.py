#!/usr/bin/env python3
"""Compose 12 supplied opaque material phases onto authored SVG faces at 12 fps.

The square guide is an appearance-material atlas, never a sheet of object
cutouts. Generate its source with transparent_background:false and preserve the
original PNG and prompt. All phases must be supplied by that source; this tool
does not invent terrain motion, interpolate phases, or repair object geometry.

svg_tools.materialize retains the authored SVG palette/lighting and transfers
generated RGB detail after removing broad lighting. It does not transfer the
material's mean/base color. Its face-detail placement may change detail aspect
ratios; the source atlas itself is only mapped by one uniform square scale.
The complete template frame and its alpha are retained without cropping.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

from PIL import Image, ImageChops

from svg_tools import materialize, rasterize
from tile_tools import write_json


COLUMNS, ROWS, COUNT, FPS = 4, 3, 12, 12
BACKGROUND = "#dededb"
SAMPLE_COLOR = "#90908a"
MASK_NAMES = ("top", "front", "studs")
COLOR_BEHAVIOR = "Authored SVG palette and lighting; generated high-frequency RGB detail only"


def _positive_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _record(path, root):
    path = Path(path).resolve()
    return {"path": Path(os.path.relpath(path, root)).as_posix(), "sha256": _sha256(path)}


def write_guide(stem, sample_size=224, gutter=32, margin=16):
    """Write an opaque square SVG/PNG and exact row-major sample rectangles.

    Four columns determine the square canvas width. Three rows are centered
    vertically; the extra vertical margin remains opaque neutral material.
    No labels, calibration keys or transparent separators enter the samples.
    """
    for value, label in ((sample_size, "Sample size"), (gutter, "Gutter"), (margin, "Margin")):
        _positive_int(value, label)
    if (sample_size + gutter) % 2:
        raise ValueError("Sample size plus gutter must be even for centered integer rectangles")
    side = COLUMNS * sample_size + (COLUMNS - 1) * gutter + 2 * margin
    margin_y = (side - (ROWS * sample_size + (ROWS - 1) * gutter)) // 2
    parts = [f'<rect width="{side}" height="{side}" fill="{BACKGROUND}"/>']
    cells = []
    for index in range(COUNT):
        x = margin + (index % COLUMNS) * (sample_size + gutter)
        y = margin_y + (index // COLUMNS) * (sample_size + gutter)
        parts.append(f'<rect x="{x}" y="{y}" width="{sample_size}" height="{sample_size}" fill="{SAMPLE_COLOR}"/>')
        cells.append({"index": index, "rect": [x, y, x + sample_size, y + sample_size]})
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{side}" height="{side}" '
           f'viewBox="0 0 {side} {side}">' + "".join(parts) + "</svg>\n")
    metadata = {
        "version": 1, "kind": "opaque-material-atlas", "size": [side, side],
        "columns": COLUMNS, "rows": ROWS, "count": COUNT, "order": "row-major",
        "sampleSize": [sample_size, sample_size], "gutter": gutter,
        "margin": [margin, margin_y], "background": BACKGROUND, "cells": cells,
        "rectConvention": "left-top-right-bottom pixel edges",
        "generationRequirements": {
            "transparent_background": False, "sourceShape": "square",
            "content": "12 supplied appearance-material phases; no objects, bevels, scenery or perspective",
            "separators": "opaque neutral gutters and margins",
        },
    }
    stem = Path(stem)
    targets = [stem.with_suffix(ext) for ext in (".svg", ".png", ".json")]
    if any(path.exists() for path in targets):
        raise ValueError("Guide output already exists; preserve the earlier attempt and choose a new stem")
    stem.parent.mkdir(parents=True, exist_ok=True)
    targets[0].write_text(svg)
    rasterize(svg).save(targets[1])
    write_json(targets[2], metadata)
    return metadata


def _guide_rects(guide):
    if guide.get("kind") != "opaque-material-atlas":
        raise ValueError("Use an authored opaque-material-atlas guide, not object panels")
    size = guide.get("size", [])
    if len(size) != 2 or size[0] != size[1]:
        raise ValueError("Material guide must be square")
    _positive_int(size[0], "Guide size")
    if (guide.get("columns"), guide.get("rows"), guide.get("order")) != (COLUMNS, ROWS, "row-major"):
        raise ValueError("Material atlas must contain 4 columns by 3 rows in row-major order")
    cells = guide.get("cells", [])
    if len(cells) != COUNT:
        raise ValueError("Material atlas must contain exactly 12 supplied phases")
    rects = []
    for index, cell in enumerate(cells):
        rect = cell.get("rect", [])
        if cell.get("index") != index or len(rect) != 4 or any(type(v) is not int for v in rect):
            raise ValueError("Guide rectangles must be indexed integer pixel-edge coordinates")
        x0, y0, x1, y1 = rect
        if not (0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]) or x1 - x0 != y1 - y0:
            raise ValueError("Each guide material sample must be a complete square inside the guide")
        if any(max(x0, r[0]) < min(x1, r[2]) and max(y0, r[1]) < min(y1, r[3]) for r in rects):
            raise ValueError("Material sample rectangles may not overlap")
        rects.append(rect)
    if len({r[2] - r[0] for r in rects}) != 1:
        raise ValueError("All material sample squares must have the same size")
    for index, rect in enumerate(rects):
        if rect[0] != rects[index % COLUMNS][0] or rect[1] != rects[(index // COLUMNS) * COLUMNS][1]:
            raise ValueError("Material rectangles must follow their authored row-major grid")
    return size, rects


def _template(directory):
    geometry_path = directory / "geometry.json"
    geometry = json.loads(geometry_path.read_text())
    size, footprint, near_anchor = (geometry.get(k, []) for k in ("size", "cellSize", "anchor"))
    for values, label in ((size, "Template size"), (footprint, "Template cellSize")):
        if len(values) != 2:
            raise ValueError(f"{label} must have two dimensions")
        for value in values:
            _positive_int(value, label)
    if (len(near_anchor) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                                     for v in near_anchor)):
        raise ValueError("Template anchor must contain two finite coordinates")
    if geometry.get("groundAnchorAlignment", "near-edge") != "near-edge":
        raise ValueError("Template anchor must explicitly use the near-edge convention")
    center_anchor = [near_anchor[0], near_anchor[1] - footprint[1] / 2]
    if any(not 0 <= v <= edge for anchor in (near_anchor, center_anchor) for v, edge in zip(anchor, size)):
        raise ValueError("Template anchors must fit the unchanged full frame")
    for name in ("bodyRect", "topRect", "frontRect"):
        rect = geometry.get(name)
        if rect is not None and (len(rect) != 4 or not (0 <= rect[0] < rect[2] <= size[0] and
                                                       0 <= rect[1] < rect[3] <= size[1])):
            raise ValueError(f"Template {name} exceeds the frame; enlarge the authored frame instead of clipping")
    with Image.open(directory / "shaded.png") as opened:
        base = opened.convert("RGBA")
    if list(base.size) != size or not base.getchannel("A").getbbox():
        raise ValueError("Template raster must be nonempty and match its declared full frame")
    svg_base = rasterize((directory / "shaded.svg").read_text())
    if svg_base.size != base.size or svg_base.tobytes() != base.tobytes():
        raise ValueError("shaded.png must exactly match its authored shaded.svg raster")
    masks = {}
    union = Image.new("L", base.size)
    outside = base.getchannel("A").point(lambda v: 255 if v == 0 else 0)
    for name in MASK_NAMES:
        with Image.open(directory / f"mask-{name}.png") as opened:
            mask = opened.convert("L")
        if mask.size != base.size:
            raise ValueError("Every face mask must match the full template frame")
        if ImageChops.multiply(mask, outside).getbbox():
            raise ValueError("A face mask extends outside the SVG alpha; correct the authored mask")
        masks[name] = mask
        union = ImageChops.lighter(union, mask)
    if not union.getbbox():
        raise ValueError("Template needs at least one nonempty material face mask")
    return geometry, base, masks, center_anchor


def compose(template_directory, source_path, guide_path, output_directory, strength=.7):
    """Sample known square material regions, then copy full SVG alpha per phase.

    Fractional source rectangles are sampled with an equal X/Y EXTENT scale.
    There is no atlas fitting, floor detection, per-axis registration, object
    extraction or silhouette clipping. A square source is required even if a
    rectangular source could be made to fit the layout by stretching it.
    """
    if not 0 <= strength <= 1:
        raise ValueError("Strength must be between 0 and 1")
    directory, source_path, guide_path, output = map(Path, (template_directory, source_path, guide_path, output_directory))
    guide = json.loads(guide_path.read_text())
    guide_size, guide_rects = _guide_rects(guide)
    with Image.open(source_path) as opened:
        if opened.format != "PNG":
            raise ValueError("Preserve and provide the original material source PNG")
        source = opened.convert("RGBA")
    if source.width != source.height:
        raise ValueError("Material source must be square; never stretch or fit atlas axes independently")
    if source.getchannel("A").getextrema() != (255, 255):
        raise ValueError("Material source must be fully opaque, including gutters and margins; use transparent_background:false")
    geometry, base, masks, anchor = _template(directory)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Output directory must be empty; preserve earlier material-animation attempts")
    root = output.resolve()
    scale = source.width / guide_size[0]
    source_rects = [[coordinate * scale for coordinate in rect] for rect in guide_rects]
    sample_side = max(1, round((guide_rects[0][2] - guide_rects[0][0]) * scale))
    # One square rectangle and one square sample imply equal axis scales. The
    # generated atlas is never resized to make it resemble the guide.
    frames = []
    output.mkdir(parents=True, exist_ok=True)
    (output / "frames").mkdir()
    sheet = Image.new("RGBA", (COLUMNS * base.width, ROWS * base.height))
    for index, (source_rect, guide_rect) in enumerate(zip(source_rects, guide_rects)):
        texture = source.transform((sample_side, sample_side), Image.Transform.EXTENT,
                                   source_rect, Image.Resampling.BICUBIC)
        image = materialize(base, texture, masks, strength)
        if image.size != base.size or image.getchannel("A").tobytes() != base.getchannel("A").tobytes():
            raise ValueError("Material compositor altered the complete template frame or alpha")
        image_name = f"frames/frame-{index:02}.png"
        image.save(output / image_name)
        sheet.paste(image, ((index % COLUMNS) * base.width, (index // COLUMNS) * base.height))
        box = image.getchannel("A").getbbox()
        frames.append({
            "id": f"frame-{index:02}", "index": index, "image": image_name,
            "size": list(image.size), "anchor": anchor, "footprint": geometry["cellSize"],
            "durationMs": 1000 / FPS, "guideRect": guide_rect, "sourceRect": source_rect,
            "artRect": [box[0], box[1], box[2] - box[0], box[3] - box[1]],
            "templateNearEdgeAnchor": geometry["anchor"], "alphaPreserved": True,
        })
    sheet.save(output / "sheet.png")
    result = {
        "version": 1, "kind": "animation", "fps": FPS, "groundAnchorAlignment": "center",
        "frames": frames, "sourceSize": list(source.size), "guideSize": guide_size,
        "sourceRects": source_rects, "guideRects": guide_rects,
        "uniformSourceScale": scale, "order": "row-major",
        "sampleRasterSize": [sample_side, sample_side], "sampling": "uniform square EXTENT, BICUBIC",
        "sheet": {"image": "sheet.png", "columns": COLUMNS, "rows": ROWS,
                  "frame": list(base.size), "spacing": 0},
        "anchorConversion": {"from": "near-edge", "to": "center", "offset": [0, -geometry["cellSize"][1] / 2],
                             "templateNearEdgeAnchor": geometry["anchor"], "centerAnchor": anchor,
                             "artMoved": False},
        "materialProcessing": {"method": "svg_tools.materialize", "strength": strength,
                               "colorBehavior": COLOR_BEHAVIOR,
                               "motion": "Only the 12 supplied atlas phases; no synthesized motion or interpolation",
                               "geometry": "Authored SVG full frame and alpha; source is appearance material only"},
        "provenance": {
            "source": {**_record(source_path, root), "size": list(source.size), "fullyOpaque": True,
                       "role": "appearance-material-phases"},
            "guide": {**_record(guide_path, root), "size": guide_size},
            "templateGeometry": _record(directory / "geometry.json", root),
            "templateSVG": _record(directory / "shaded.svg", root),
            "templateRaster": {**_record(directory / "shaded.png", root), "size": list(base.size)},
            "masks": {name: {**_record(directory / f"mask-{name}.png", root), "size": list(masks[name].size)}
                      for name in MASK_NAMES},
        },
    }
    write_json(output / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    guide = commands.add_parser("guide", help="Opaque square SVG, PNG and exact 4×3 material-sample rectangles")
    guide.add_argument("output", type=Path, help="Output stem for .svg, .png and .json")
    guide.add_argument("--sample-size", type=int, default=224)
    guide.add_argument("--gutter", type=int, default=32)
    guide.add_argument("--margin", type=int, default=16, help="Horizontal margin; vertical margin centers the three rows")
    render = commands.add_parser("compose", help="12 supplied material phases on complete SVG frames; fixed 12 fps")
    render.add_argument("template", type=Path, help="shaded.svg/.png, geometry.json and mask-top/front/studs.png")
    render.add_argument("source", type=Path, help="Unchanged opaque square generated material-atlas PNG")
    render.add_argument("guide", type=Path, help="Exact material guide JSON")
    render.add_argument("output", type=Path, help="New/empty directory for full frames, sheet and processor result")
    render.add_argument("--strength", type=float, default=.7)
    args = parser.parse_args()
    try:
        if args.command == "guide":
            result = write_guide(args.output, args.sample_size, args.gutter, args.margin)
            print(json.dumps({"guide": str(args.output.with_suffix('.json')), "size": result["size"],
                              "samples": COUNT, "transparent_background": False}, indent=2))
        else:
            result = compose(args.template, args.source, args.guide, args.output, args.strength)
            print(json.dumps({"result": str(args.output / 'result.json'), "frames": len(result["frames"]),
                              "fps": FPS, "anchor": result["frames"][0]["anchor"],
                              "colorBehavior": COLOR_BEHAVIOR}, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
