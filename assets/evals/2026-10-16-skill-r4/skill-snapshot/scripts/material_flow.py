#!/usr/bin/env python3
"""Author a 12 fps terrain loop from ONE opaque square material texture.

Choose this texture-mapping workflow before generation. The model supplies one
full square appearance texture; it does not generate animation phases or poses.
Motion is authored periodic X translation on pre-authored SVG faces, with static
phase-zero detail at each face boundary. The original source is never edited,
keyed, cropped, fitted, or interpreted as a whole-object render.

Boundary stabilization does not prove that the supplied material is seamless or
that the loop looks good. Independent LLM review must judge spatial seams and
temporal quality. A flat or repeating source can yield duplicate frames.
"""
import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageChops

from material_animation import COLOR_BEHAVIOR, MASK_NAMES, _record, _template
from svg_tools import materialize
from tile_tools import write_json


COLUMNS, ROWS, COUNT, FPS = 4, 3, 12, 12


def _shift_texture(source, phase):
    """Wrap every pixel of the whole square; phase 12 is exactly phase zero.

    Integer offsets use Python round (nearest integer, ties to even). Modulo is
    applied to the phase first, so loop closure is exact even for small sources.
    """
    offset = round(source.width * (phase % COUNT) / COUNT)
    return ImageChops.offset(source, offset, 0), offset


def _effective_faces(masks):
    """Follow svg_tools.materialize's face priority, including stud exclusion."""
    total = Image.new("L", masks["top"].size)
    faces = {}
    for name in MASK_NAMES:
        face = masks[name].copy()
        if name != "studs":
            face = ImageChops.subtract(face, masks["studs"])
        face = ImageChops.subtract(face, total)
        faces[name] = face
        total = ImageChops.lighter(total, face)
    return faces


def _distance_mask(face, edge_band):
    """Smoothstep of Chebyshev distance inward from the face boundary.

    Distances are logical template pixels. A padded zero exterior and two
    8-neighbor passes compute the exact Chebyshev distance to the exterior.
    Subtracting one puts the first occupied boundary pixel at distance zero,
    including diagonal boundaries. No geometry or alpha is changed.
    """
    width, height = face.size
    stride = width + 2
    distances = [[0] * stride for _ in range(height + 2)]
    pixels = face.tobytes()
    infinity = width + height + 1
    for y in range(height):
        row = distances[y + 1]
        for x in range(width):
            if pixels[y * width + x]:
                row[x + 1] = infinity
    for y in range(1, height + 1):
        row, above = distances[y], distances[y - 1]
        for x in range(1, width + 1):
            if row[x]:
                row[x] = min(row[x], row[x - 1] + 1, above[x - 1] + 1,
                             above[x] + 1, above[x + 1] + 1)
    for y in range(height, 0, -1):
        row, below = distances[y], distances[y + 1]
        for x in range(width, 0, -1):
            if row[x]:
                row[x] = min(row[x], row[x + 1] + 1, below[x - 1] + 1,
                             below[x] + 1, below[x + 1] + 1)
    weights = []
    for y in range(1, height + 1):
        for x in range(1, width + 1):
            fraction = min(1., max(0., (distances[y][x] - 1) / edge_band))
            weights.append(round(255 * fraction * fraction * (3 - 2 * fraction)))
    result = Image.new("L", face.size)
    result.putdata(weights)
    return result


def _motion_masks(masks, edge_band):
    faces = _effective_faces(masks)
    weights = {name: _distance_mask(face, edge_band) for name, face in faces.items()}
    # Partial authored mask overlaps use the most stable active face's weight.
    # Thus no other face can animate a pixel on a participating face boundary.
    face_pixels = [faces[name].tobytes() for name in MASK_NAMES]
    weight_pixels = [weights[name].tobytes() for name in MASK_NAMES]
    combined = bytes(min((weight_pixels[n][i] for n in range(len(MASK_NAMES)) if face_pixels[n][i]),
                         default=0) for i in range(masks["top"].width * masks["top"].height))
    return Image.frombytes("L", masks["top"].size, combined), weights


def compose(template_directory, source_path, output_directory, strength=.7, edge_band=16):
    """Map the complete source square with deterministic authored texture motion."""
    if not isinstance(strength, (int, float)) or isinstance(strength, bool) or not 0 <= strength <= 1:
        raise ValueError("Strength must be between 0 and 1")
    if (not isinstance(edge_band, (int, float)) or isinstance(edge_band, bool) or
            not math.isfinite(edge_band) or edge_band <= 0):
        raise ValueError("Edge band must be a positive finite number of logical pixels")
    directory, source_path, output = map(Path, (template_directory, source_path, output_directory))
    with Image.open(source_path) as opened:
        if opened.format != "PNG":
            raise ValueError("Preserve and provide the original full square material source PNG")
        source = opened.convert("RGBA")
    if source.width != source.height:
        raise ValueError("Material source must be square; never stretch or fit its axes")
    if source.getchannel("A").getextrema() != (255, 255):
        raise ValueError("Material source must be fully opaque; use transparent_background:false")
    geometry, base, masks, anchor = _template(directory)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Output directory must be empty; preserve earlier material-flow attempts")
    motion_mask, face_weights = _motion_masks(masks, edge_band)
    static = materialize(base, source, masks, strength)
    root = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "frames").mkdir()
    motion_mask.save(output / "motion-mask.png")
    for name, mask in face_weights.items():
        mask.save(output / f"motion-mask-{name}.png")
    source_rect = [0, 0, source.width, source.height]
    frames, frame_pixels, uv_shifts = [], set(), []
    sheet = Image.new("RGBA", (COLUMNS * base.width, ROWS * base.height))
    for phase in range(COUNT):
        texture, shift_x = _shift_texture(source, phase)
        moving = materialize(base, texture, masks, strength)
        image = Image.composite(moving.convert("RGB"), static.convert("RGB"), motion_mask)
        image.putalpha(base.getchannel("A"))
        if image.size != base.size or image.getchannel("A").tobytes() != base.getchannel("A").tobytes():
            raise ValueError("Material flow altered the complete template frame or alpha")
        frame_pixels.add(image.tobytes())
        uv_shift = {"phase": phase, "requestedXPixels": source.width * phase / COUNT,
                    "appliedXPixels": shift_x, "appliedYPixels": 0,
                    "appliedNormalized": [shift_x / source.width, 0]}
        uv_shifts.append(uv_shift)
        image_name = f"frames/frame-{phase:02}.png"
        image.save(output / image_name)
        sheet.paste(image, ((phase % COLUMNS) * base.width, (phase // COLUMNS) * base.height))
        box = image.getchannel("A").getbbox()
        frames.append({
            "id": f"frame-{phase:02}", "index": phase, "image": image_name,
            "size": list(image.size), "anchor": anchor, "footprint": geometry["cellSize"],
            "durationMs": 1000 / FPS, "sourceRect": source_rect, "uvShift": uv_shift,
            "artRect": [box[0], box[1], box[2] - box[0], box[3] - box[1]],
            "templateNearEdgeAnchor": geometry["anchor"], "alphaPreserved": True,
        })
    sheet.save(output / "sheet.png")
    result = {
        "version": 1, "kind": "animation", "workflow": "authored-periodic-material-flow",
        "fps": FPS, "groundAnchorAlignment": "center", "frames": frames,
        "sourceSize": list(source.size), "sourceRect": source_rect, "uvShifts": uv_shifts,
        "order": "row-major", "sampling": "Whole square, integer periodic X wrap, then svg_tools.materialize face mapping",
        "sheet": {"image": "sheet.png", "columns": COLUMNS, "rows": ROWS,
                  "frame": list(base.size), "spacing": 0},
        "anchorConversion": {"from": "near-edge", "to": "center", "offset": [0, -geometry["cellSize"][1] / 2],
                             "templateNearEdgeAnchor": geometry["anchor"], "centerAnchor": anchor, "artMoved": False},
        "materialProcessing": {
            "method": "svg_tools.materialize", "strength": strength, "colorBehavior": COLOR_BEHAVIOR,
            "motion": "Authored periodic texture translation; model supplies one material, not animation phases or poses",
            "geometry": "Authored SVG full frame and alpha; source is appearance material only",
            "sourceEdited": False, "sourceCropped": False,
            "translation": {"axis": "x", "formula": "round(source.width * (phase % 12) / 12)",
                            "rounding": "nearest integer, ties to even", "wrap": "periodic, all source pixels retained",
                            "periodFrames": COUNT, "frame12EqualsFrame0": True},
            "boundaryStabilization": {
                "edgeBandLogicalPx": edge_band, "staticReferencePhase": 0,
                "distance": "Chebyshev distance inward from the effective authored face's 8-neighbor boundary",
                "weight": "smoothstep(clamp(distance / edgeBand, 0, 1)), quantized to 8-bit nearest integer",
                "blend": "phase0 RGB + weight * (moving RGB - phase0 RGB); unchanged authored alpha",
                "overlaps": "minimum weight among participating effective faces",
                "mask": {**_record(output / "motion-mask.png", root), "size": list(base.size)},
                "faceMasks": {name: {**_record(output / f"motion-mask-{name}.png", root), "size": list(base.size)}
                              for name in MASK_NAMES},
            },
        },
        "diagnostics": {"distinctFrameCount": len(frame_pixels), "motionObserved": len(frame_pixels) > 1,
                        "meaning": "Pixel differences only; duplicate frames are retained, never fabricated"},
        "visualReviewRequired": "Independent LLM review of spatial seams and temporal quality; source seamlessness is not guaranteed",
        "provenance": {
            "source": {**_record(source_path, root), "size": list(source.size), "sourceRect": source_rect,
                       "fullyOpaque": True, "role": "single-appearance-material-texture", "modelGeneratedAnimation": False},
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
    render = commands.add_parser("compose", help="Author a periodic 12 fps loop from one full material square")
    render.add_argument("template", type=Path, help="Authored shaded.svg/.png, geometry.json and face masks")
    render.add_argument("source", type=Path, help="Unchanged opaque square material PNG; no object or animation atlas")
    render.add_argument("output", type=Path, help="New/empty directory for complete frames and processor result")
    render.add_argument("--strength", type=float, default=.7)
    render.add_argument("--edge-band", type=float, default=16, help="Static-boundary fade distance in logical template pixels")
    args = parser.parse_args()
    try:
        result = compose(args.template, args.source, args.output, args.strength, args.edge_band)
        print(json.dumps({"result": str(args.output / "result.json"), "frames": COUNT, "fps": FPS,
                          "anchor": result["frames"][0]["anchor"],
                          "distinctFrames": result["diagnostics"]["distinctFrameCount"],
                          "motion": result["materialProcessing"]["motion"]}, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
