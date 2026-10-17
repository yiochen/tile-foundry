#!/usr/bin/env python3
"""Extract authored 3D-render panels without fitting or correcting generated art.

Only the known layout is transferred: a single uniform scale maps the entire
generated PNG to the reference canvas. Transparent gutters and an empty boundary
inside every panel are required. No subject detection, panel recovery, color key,
renderer silhouette mask, per-pose scale, root fitting, or clipping is performed.
Fixed output metadata does not certify that the reskin obeyed the 3D geometry.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


FPS = 12
DIRECTIONS = {"N", "NE", "E", "SE", "S", "SW", "W", "NW"}
REGISTRATION_SCOPE = (
    "Authored frame layout, projection and root only; generated silhouette, "
    "height, contact and pose adherence require independent visual review"
)


def _integer(value, label, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")
    return value


def _dimensions(values, label):
    if not isinstance(values, list) or len(values) != 2:
        raise ValueError(f"{label} must contain two positive integer dimensions")
    return [_integer(value, label) for value in values]


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _record(path, root):
    return {"path": Path(os.path.relpath(Path(path).resolve(), root)).as_posix(), "sha256": _sha256(path)}


def _validate_guide(guide, kind):
    if guide.get("version") != 1 or guide.get("kind") != "rendered-3d-sheet":
        raise ValueError("Expected version 1 rendered-3d-sheet guide JSON")
    size = _dimensions(guide.get("size"), "Guide size")
    frame = _dimensions(guide.get("frame"), "Frame")
    cell_size = _integer(guide.get("cellSize"), "cellSize")
    anchor = guide.get("anchor")
    if (not isinstance(anchor, list) or len(anchor) != 2 or
            any(not _finite(v) or not 0 <= v <= edge for v, edge in zip(anchor, frame))):
        raise ValueError("Authored anchor must contain two finite coordinates inside the unchanged frame")
    capture_scale = guide.get("captureScale")
    if not _finite(capture_scale) or capture_scale <= 0:
        raise ValueError("captureScale must be a positive finite uniform scale")
    gutter = _integer(guide.get("gutter"), "Guide gutter", 0)
    kind = kind or guide.get("assetKind", "animation")
    if kind not in ("animation", "directions"):
        raise ValueError("Asset kind must be animation or directions")
    cells = guide.get("cells")
    if not isinstance(cells, list) or not cells:
        raise ValueError("Guide must declare at least one complete panel")
    rects, directions = [], []
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict) or cell.get("index") != index:
            raise ValueError("Guide panels must use consecutive indices in supplied playback order")
        rect = cell.get("rect")
        if not isinstance(rect, list) or len(rect) != 4 or any(type(v) is not int for v in rect):
            raise ValueError("Guide panels must use integer left-top-right-bottom pixel edges")
        x0, y0, x1, y1 = rect
        if not (0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]):
            raise ValueError("Guide panel exceeds its complete reference canvas")
        if (abs(x1 - x0 - frame[0] * capture_scale) > 1e-8 or
                abs(y1 - y0 - frame[1] * capture_scale) > 1e-8):
            raise ValueError("Every panel must equal the full runtime frame times uniform captureScale")
        for previous in rects:
            gap_x = max(x0 - previous[2], previous[0] - x1)
            gap_y = max(y0 - previous[3], previous[1] - y1)
            if max(gap_x, gap_y) < gutter or (gap_x < 0 and gap_y < 0):
                raise ValueError("Guide panels overlap or violate the declared transparent gutter")
        rects.append(rect)
        if kind == "directions":
            direction = cell.get("direction")
            if direction not in DIRECTIONS or direction in directions:
                raise ValueError("Directions require unique canonical N/NE/E/SE/S/SW/W/NW codes")
            directions.append(direction)
        elif "durationMs" in cell and (not _finite(cell["durationMs"]) or
                                        abs(cell["durationMs"] - 1000 / FPS) >= .001):
            raise ValueError("Authored animation timing must already be 12 fps; no silent retiming")
    occupied = guide.get("occupiedCells", [[0, 0]])
    if (not isinstance(occupied, list) or not occupied or
            any(not isinstance(c, list) or len(c) != 2 or any(type(v) is not int for v in c) for c in occupied)):
        raise ValueError("occupiedCells must contain authored integer grid coordinates")
    elevation = guide.get("elevationPx", 0)
    if not _finite(elevation) or elevation < 0:
        raise ValueError("elevationPx must be an authored nonnegative height")
    if guide.get("projection", "top-down-oblique-square-grid") != "top-down-oblique-square-grid":
        raise ValueError("Unknown projection profile")
    if guide.get("groundAnchorAlignment", "center") != "center":
        raise ValueError("The authored 3D guide must use a center ground anchor")
    return size, frame, cell_size, anchor, capture_scale, kind, rects, occupied, elevation


def _alpha_mass(alpha):
    return sum(index * count for index, count in enumerate(alpha.histogram()))


def _border_max(alpha):
    width, height = alpha.size
    borders = ((0, 0, width, 1), (0, height - 1, width, height),
               (0, 0, 1, height), (width - 1, 0, width, height))
    return max(alpha.crop(rect).getextrema()[1] for rect in borders)


def extract(source_path, guide_path, output_directory, kind=None, min_alpha=0):
    """Write complete registered frames using exact authored panel rectangles.

    A <=1 source-pixel rounding discrepancy between whole-canvas X/Y dimensions
    is tolerated. A least-squares scalar is used on both axes, with zero offset;
    no independent axis resize or inferred crop is permitted. The scalar and
    residuals are recorded. Threshold zero leaves every generated alpha intact.
    An explicit positive threshold zeros alpha <=threshold globally and records
    its total removed alpha mass, including any faint foreground edge pixels.
    """
    _integer(min_alpha, "min_alpha", 0)
    if min_alpha > 254:
        raise ValueError("min_alpha must be <=254; opaque content may never be deleted")
    source_path, guide_path, output = map(Path, (source_path, guide_path, output_directory))
    guide = json.loads(guide_path.read_text())
    size, frame, cell_size, anchor, capture_scale, kind, rects, occupied, elevation = _validate_guide(guide, kind)
    with Image.open(source_path) as opened:
        if opened.format != "PNG":
            raise ValueError("Preserve and supply the original generated PNG")
        source = opened.convert("RGBA")
    sx, sy = source.width / size[0], source.height / size[1]
    if abs(source.height - size[1] * sx) > 1 + 1e-9 or abs(source.width - size[0] * sy) > 1 + 1e-9:
        raise ValueError("Generated whole-sheet aspect differs from guide beyond one source pixel; no axis stretching")
    scale = (source.width * size[0] + source.height * size[1]) / (size[0] ** 2 + size[1] ** 2)
    residual = [source.width - size[0] * scale, source.height - size[1] * scale]
    mapped = [[v * scale for v in rect] for rect in rects]
    # Integer envelopes include every source pixel intersecting each known panel.
    # Transparent borders below ensure fractional edges contain no clipped art.
    integer_rects = [(math.floor(r[0] + 1e-9), math.floor(r[1] + 1e-9),
                      math.ceil(r[2] - 1e-9), math.ceil(r[3] - 1e-9)) for r in mapped]
    coverage = Image.new("L", source.size)
    draw = ImageDraw.Draw(coverage)
    for index, rect in enumerate(integer_rects):
        x0, y0, x1, y1 = rect
        if not (0 <= x0 < x1 <= source.width and 0 <= y0 < y1 <= source.height):
            raise ValueError("Uniformly mapped guide panel exceeds source; no crop or offset recovery")
        if coverage.crop(rect).getbbox():
            raise ValueError("Source resolution merges authored panel envelopes; preserve larger transparent gutters")
        draw.rectangle((x0, y0, x1 - 1, y1 - 1), fill=255)
    original_alpha = source.getchannel("A")
    original_mass = _alpha_mass(original_alpha)
    alpha = original_alpha.point(lambda value: 0 if value <= min_alpha else value) if min_alpha else original_alpha.copy()
    cleaned = source.copy()
    cleaned.putalpha(alpha)
    removed = original_mass - _alpha_mass(alpha)
    outside_original = ImageChops.multiply(original_alpha, ImageChops.invert(coverage))
    outside = ImageChops.multiply(alpha, ImageChops.invert(coverage))
    if outside.getbbox():
        raise ValueError(f"Art crosses a sheet gutter/outside declared panels (alpha {outside.getextrema()[1]}); "
                         "regenerate isolated fixed-layout panels instead of clipping")
    images, frames, sprites = [], [], []
    root = output.resolve()
    source_record, guide_record = _record(source_path, root), _record(guide_path, root)
    for index, (cell, rect, source_rect, envelope) in enumerate(zip(guide["cells"], rects, mapped, integer_rects)):
        panel_alpha = alpha.crop(envelope)
        if not panel_alpha.getbbox():
            raise ValueError(f"Panel {index} is empty; layout may have reflowed or omitted a pose")
        if _border_max(panel_alpha):
            raise ValueError(f"Panel {index} art touches its authored boundary; clipping risk, enlarge the guide and regenerate")
        # Exact integer 1:1 extraction is byte-preserving; every other case uses
        # one equal X/Y sampling factor from known source pixel edges.
        if all(abs(v - round(v)) < 1e-8 for v in source_rect) and tuple(frame) == (envelope[2] - envelope[0], envelope[3] - envelope[1]):
            image = cleaned.crop(envelope)
            sampling = "Exact known integer panel; no resampling"
        else:
            image = cleaned.transform(tuple(frame), Image.Transform.EXTENT, source_rect, Image.Resampling.BICUBIC)
            sampling = "Uniform known-panel EXTENT resampling, BICUBIC; equal X/Y factor"
        image_alpha = image.getchannel("A")
        box = image_alpha.getbbox()
        if not box:
            raise ValueError(f"Panel {index} becomes empty at runtime resolution; increase the authored art scale")
        if _border_max(image_alpha):
            raise ValueError(f"Panel {index} resampled art reaches the runtime frame boundary; clipping risk")
        name = f"frames/frame-{index:02}.png"
        registration = {"method": "authored-3d-projection", "guide": guide_record["path"],
                        "guideSHA256": guide_record["sha256"], "scope": REGISTRATION_SCOPE,
                        "guideRect": rect, "sourceRect": source_rect, "sourceEnvelope": list(envelope)}
        normalization = {"scale": [1 / (scale * capture_scale)] * 2, "offset": [0, 0],
                         "sourceOrigin": source_rect[:2], "anchorIn": [v * scale * capture_scale for v in anchor],
                         "anchorOut": anchor, "perPoseFitting": False, "sampling": sampling}
        entry = {"id": f"frame-{index:02}", "index": index, "image": name,
                 "size": frame, "anchor": anchor, "footprint": [cell_size, cell_size],
                 "artRect": [box[0], box[1], box[2] - box[0], box[3] - box[1]],
                 "registration": registration, "normalization": normalization}
        if kind == "animation":
            entry["durationMs"] = 1000 / FPS
        else:
            entry["direction"] = cell["direction"]
        sprite = {**entry, "role": "player", "occupiedCells": occupied, "elevationPx": elevation}
        frames.append(entry)
        sprites.append(sprite)
        images.append(image)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Output directory must be empty; preserve previous generated/processed attempts")
    columns = guide.get("columns", min(4, len(images)))
    _integer(columns, "Sheet columns")
    rows = math.ceil(len(images) / columns)
    sheet = Image.new("RGBA", (columns * frame[0], rows * frame[1]))
    for index, image in enumerate(images):
        sheet.paste(image, ((index % columns) * frame[0], (index // columns) * frame[1]))
    cleanup = {"minAlpha": min_alpha, "scope": "Single global source-alpha threshold before panel extraction",
               "removedAlphaMass": removed, "sourceAlphaMass": original_mass,
               "sourceRGBChanged": False, "rendererMaskApplied": False, "colorKeyApplied": False}
    result = {"version": 2, "kind": kind, "projection": "top-down-oblique-square-grid", "cellSize": cell_size,
              "groundAnchorAlignment": "center", "sprites": sprites, "frames": frames,
              "sourceSize": list(source.size), "guideSize": size,
              "uniformSourceScale": scale, "captureScale": capture_scale,
              "sourceRects": mapped, "guideRects": rects,
              "normalization": {"wholeCanvasUniformScale": scale, "wholeCanvasOffset": [0, 0],
                                "integerRoundingTolerancePx": 1, "sourceEdgeResidualPx": residual,
                                "equalAxisScale": True, "perPoseFitting": False},
              "cleanup": cleanup,
              "panelIsolation": {"method": "strict-authored-3d-panels", "gutterGuidePx": guide["gutter"],
                                 "maximumOutsideAlphaBeforeThreshold": outside_original.getextrema()[1],
                                 "outsideAlphaMassBeforeThreshold": _alpha_mass(outside_original),
                                 "maximumOutsideAlphaAfterThreshold": 0,
                                 "panelBoundaryAlphaAfterThreshold": 0},
              "registration": {"method": "authored-3d-projection", "scope": REGISTRATION_SCOPE},
              "geometryDeclaration": REGISTRATION_SCOPE,
              "sheet": {"image": "sheet.png", "columns": columns, "rows": rows, "frame": frame, "spacing": 0},
              "provenance": {"source": source_record, "guide": guide_record,
                             "processor": {"path": Path(__file__).name, "sha256": _sha256(__file__)}}}
    if kind == "animation":
        result["fps"] = FPS
    output.mkdir(parents=True, exist_ok=True)
    (output / "frames").mkdir()
    for entry, image in zip(frames, images):
        image.save(output / entry["image"])
    sheet.save(output / "sheet.png")
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("guide", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--kind", choices=("animation", "directions"))
    parser.add_argument("--min-alpha", type=int, default=0,
                        help="Explicit global alpha deletion threshold, default 0 removes nothing")
    args = parser.parse_args()
    result = extract(args.source, args.guide, args.output, args.kind, args.min_alpha)
    print(json.dumps({"kind": result["kind"], "sprites": len(result["sprites"]),
                      "sourceSHA256": result["provenance"]["source"]["sha256"],
                      "removedAlphaMass": result["cleanup"]["removedAlphaMass"],
                      "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
