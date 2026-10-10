#!/usr/bin/env python3
"""Deterministic tile processing. Coordinates use top-left origin and pixel edges."""
from __future__ import annotations

import argparse
import json
import math
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def load_rgba(path):
    with Image.open(path) as source:
        if "A" not in source.getbands() and "transparency" not in source.info:
            raise ValueError(f"{path}: no alpha channel; use transparent generation or an explicit mask")
        return source.convert("RGBA")


def alpha_bounds(image, threshold=8):
    if not 0 <= threshold <= 254:
        raise ValueError("Alpha threshold must be 0..254")
    bounds = image.getchannel("A").point(lambda a: 255 if a > threshold else 0).getbbox()
    if bounds is None:
        raise ValueError("Image is empty at the requested alpha threshold")
    return bounds


def clean_alpha(image, min_alpha=32):
    """Remove only weak alpha noise, without guessing an RGB background color."""
    if not 1 <= min_alpha <= 254:
        raise ValueError("min-alpha must be 1..254")
    output = image.copy()
    alpha = output.getchannel("A")
    histogram = alpha.histogram()
    output.putalpha(alpha.point(lambda a: a if a >= min_alpha else 0))
    alpha_bounds(output)
    return output, {"minAlpha": min_alpha, "removedPixels": sum(histogram[1:min_alpha]),
                    "warning": "Review at final size: intentionally faint details can also be removed."}


def crop_alpha(image, anchor=None, padding=0, threshold=8):
    """Crop the whole alpha silhouette; preserve ground anchor, including outside art."""
    if padding < 0:
        raise ValueError("Padding cannot be negative")
    box = alpha_bounds(image, threshold)
    if anchor is None:
        anchor = ((box[0] + box[2]) / 2, box[3])
    cropped = image.crop(box)
    output = Image.new("RGBA", (cropped.width + 2 * padding, cropped.height + 2 * padding))
    output.paste(cropped, (padding, padding))
    return output, {
        "sourceSize": list(image.size), "sourceRect": list(box),
        "anchor": [anchor[0] - box[0] + padding, anchor[1] - box[1] + padding],
        "anchorSource": list(anchor), "size": list(output.size),
    }


def split_grid(image, cell, columns, rows, margin=0, spacing=0):
    if min(*cell, columns, rows) <= 0 or min(margin, spacing) < 0:
        raise ValueError("Grid dimensions must be positive; margins and spacing nonnegative")
    needed = (2 * margin + columns * cell[0] + (columns - 1) * spacing,
              2 * margin + rows * cell[1] + (rows - 1) * spacing)
    if needed[0] > image.width or needed[1] > image.height:
        raise ValueError(f"Grid requires {needed}, source is {image.size}; refusing truncated cuts")
    tiles = []
    for row in range(rows):
        for col in range(columns):
            x = margin + col * (cell[0] + spacing)
            y = margin + row * (cell[1] + spacing)
            rect = (x, y, x + cell[0], y + cell[1])
            tiles.append((image.crop(rect), {"row": row, "column": col, "sourceRect": list(rect)}))
    return tiles


def component_rects(image, threshold=8, min_area=32, join_radius=0):
    """Flood-fill alpha. Optional dilation groups nearby detached sprite fragments."""
    if min_area < 1 or not 0 <= join_radius <= 32:
        raise ValueError("min-area must be positive; join-radius must be 0..32")
    mask = image.getchannel("A").point(lambda a: 255 if a > threshold else 0)
    if join_radius:
        mask = mask.filter(ImageFilter.MaxFilter(2 * join_radius + 1))
    pixels = bytearray(mask.tobytes())
    w, h = image.size
    results = []
    for start in range(w * h):
        if not pixels[start]:
            continue
        pixels[start] = 0
        queue = deque([start])
        x0 = x1 = start % w
        y0 = y1 = start // w
        count = 0
        while queue:
            index = queue.popleft()
            x, y = index % w, index // w
            x0, x1 = min(x0, x), max(x1, x)
            y0, y1 = min(y0, y), max(y1, y)
            count += 1
            # Eight-connected alpha handles antialiased diagonal silhouettes.
            for ny in range(max(0, y - 1), min(h, y + 2)):
                for nx in range(max(0, x - 1), min(w, x + 2)):
                    neighbor = ny * w + nx
                    if pixels[neighbor]:
                        pixels[neighbor] = 0
                        queue.append(neighbor)
        if count >= min_area:
            # Dilation is only for grouping; restore the true silhouette bounds.
            expanded = (x0, y0, x1 + 1, y1 + 1)
            original = image.crop(expanded)
            real = alpha_bounds(original, threshold)
            results.append((x0 + real[0], y0 + real[1], x0 + real[2], y0 + real[3]))
    return sorted(results, key=lambda b: (b[1], b[0]))


def normalize(image, frame=(192, 320), anchor_out=(96, 312), art_width=128,
              anchor_in=None, footprint=(128, 128), threshold=8, scale=None):
    cropped, info = crop_alpha(image, anchor_in, threshold=threshold)
    if min(*frame, *footprint, art_width) <= 0:
        raise ValueError("Frame, footprint, and art width must be positive")
    scale = scale if scale is not None else art_width / cropped.width
    if scale <= 0:
        raise ValueError("Scale must be positive")
    size = (max(1, round(cropped.width * scale)), max(1, round(cropped.height * scale)))
    # Store the actual per-axis scale introduced by rounding, preserving exact anchors.
    sx, sy = size[0] / cropped.width, size[1] / cropped.height
    scaled_anchor = (info["anchor"][0] * sx, info["anchor"][1] * sy)
    x, y = round(anchor_out[0] - scaled_anchor[0]), round(anchor_out[1] - scaled_anchor[1])
    if x < 0 or y < 0 or x + size[0] > frame[0] or y + size[1] > frame[1]:
        raise ValueError(f"Art at {(x, y, *size)} exceeds frame {frame}; enlarge the frame or choose an explicit scale")
    output = Image.new("RGBA", frame)
    output.paste(cropped.resize(size, Image.Resampling.LANCZOS), (x, y))
    # Fractional source anchors must converge to the same exact frame anchor.
    # Translate the composed frame by the residual after integer-pixel placement.
    shift = [anchor_out[0] - x - scaled_anchor[0], anchor_out[1] - y - scaled_anchor[1]]
    if any(abs(value) > 1e-9 for value in shift):
        output = output.transform(frame, Image.Transform.AFFINE,
                                  (1, 0, -shift[0], 0, 1, -shift[1]), Image.Resampling.BICUBIC)
    return output, {
        **info, "size": list(frame), "anchor": list(anchor_out), "subpixelShift": shift,
        "footprint": list(footprint), "artRect": [x, y, *size],
        "scale": [sx, sy], "sourceAnchorMode": "explicit" if anchor_in else "alpha-bottom-center",
    }


def pack_atlas(items, columns=4, padding=4, extrusion=2, trim=True):
    """Pack shelf cells; trimmed frame anchors are expressed in frame-local pixels."""
    if not items or columns < 1 or extrusion < 0 or padding < extrusion:
        raise ValueError("Require tiles, columns > 0, and padding >= extrusion >= 0")
    prepared = []
    for name, image, meta in items:
        box = alpha_bounds(image, 0) if trim else (0, 0, image.width, image.height)
        prepared.append((name, image.crop(box), meta, box))
    columns = min(columns, len(items))
    cell_w = max(i.width for _, i, _, _ in prepared) + 2 * padding
    cell_h = max(i.height for _, i, _, _ in prepared) + 2 * padding
    atlas = Image.new("RGBA", (columns * cell_w, math.ceil(len(items) / columns) * cell_h))
    frames = {}
    for index, (name, tile, meta, box) in enumerate(prepared):
        x, y = (index % columns) * cell_w + padding, (index // columns) * cell_h + padding
        if extrusion:
            e = extrusion
            # Clamp edge texels into the surrounding gutter, including four corners.
            expanded = Image.new("RGBA", (tile.width + 2 * e, tile.height + 2 * e))
            expanded.paste(tile, (e, e))
            expanded.paste(tile.crop((0, 0, 1, tile.height)).resize((e, tile.height)), (0, e))
            expanded.paste(tile.crop((tile.width - 1, 0, tile.width, tile.height)).resize((e, tile.height)), (e + tile.width, e))
            expanded.paste(tile.crop((0, 0, tile.width, 1)).resize((tile.width, e)), (e, 0))
            expanded.paste(tile.crop((0, tile.height - 1, tile.width, tile.height)).resize((tile.width, e)), (e, e + tile.height))
            for xx, yy, tx, ty in [(0, 0, 0, 0), (e + tile.width, 0, tile.width - 1, 0),
                                   (0, e + tile.height, 0, tile.height - 1),
                                   (e + tile.width, e + tile.height, tile.width - 1, tile.height - 1)]:
                expanded.paste(Image.new("RGBA", (e, e), tile.getpixel((tx, ty))), (xx, yy))
            atlas.paste(expanded, (x - e, y - e))
        else:
            atlas.paste(tile, (x, y))
        frames[name] = {
            "frame": {"x": x, "y": y, "w": tile.width, "h": tile.height},
            "sourceSize": {"w": image.width, "h": image.height},
            "spriteSourceSize": {"x": box[0], "y": box[1], "w": tile.width, "h": tile.height},
            "anchor": [meta["anchor"][0] - box[0], meta["anchor"][1] - box[1]],
            "footprint": meta.get("footprint", [128, 128]),
        }
    return atlas, {"frames": frames, "meta": {"size": {"w": atlas.width, "h": atlas.height},
                  "padding": padding, "extrusion": extrusion, "trimmed": trim}}


def generate_guides(directory, frame=(192, 320), footprint=(128, 128), heights=(32, 64, 96)):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    ax, ay = frame[0] / 2, frame[1] - 8
    x0, x1 = ax - footprint[0] / 2, ax + footprint[0] / 2
    for height in heights:
        if ay - footprint[1] - height < 0:
            raise ValueError("Guide exceeds frame")
        guide = Image.new("RGBA", frame)
        draw = ImageDraw.Draw(guide)
        draw.rectangle((x0, ay - footprint[1] - height, x1 - 1, ay - height - 1), fill="#f1c879", outline="#9e7337", width=2)
        draw.rectangle((x0, ay - height, x1 - 1, ay - 1), fill="#b1803b", outline="#79562c", width=2)
        # Guides deliberately include lines; final art must not include these marks.
        draw.rectangle((x0, ay - footprint[1], x1 - 1, ay - 1), outline="#2b70da", width=1)
        draw.line((ax - 5, ay, ax + 5, ay), fill="#da4055", width=2)
        draw.line((ax, ay - 5, ax, ay + 5), fill="#da4055", width=2)
        guide.save(directory / f"height-{height}.png")
    write_json(directory / "guides.json", {"frame": frame, "footprint": footprint,
               "anchor": [ax, ay], "heights": list(heights), "projection": "orthogonal top and front; height extends upward"})


def validate_assets(assets, root):
    errors, warnings = [], []
    for asset in assets["tiles"]:
        image = load_rgba(Path(root) / asset["image"])
        ax, ay = asset["anchor"]
        if not 0 <= ax <= image.width or not 0 <= ay <= image.height:
            errors.append(f"{asset['id']}: anchor outside canvas")
        bbox = alpha_bounds(image)
        if bbox[0] == 0 or bbox[1] == 0 or bbox[2] == image.width or bbox[3] == image.height:
            warnings.append(f"{asset['id']}: silhouette touches frame edge; inspect for clipping")
        if asset.get("sourceAnchorMode") == "alpha-bottom-center" and not asset.get("anchorReviewed"):
            warnings.append(f"{asset['id']}: automatic anchor; visually verify ground contact")
    return {"ok": not errors, "errors": errors, "warnings": warnings}


def export_tiled(scene, assets, output):
    tile_by_id = {tile["id"]: (index, tile) for index, tile in enumerate(assets["tiles"])}
    w, h = scene["width"], scene["height"]
    size = assets["cellSize"]
    # Image collection avoids assuming image height == logical map cell height.
    object_tiles = []
    for index, tile in enumerate(assets["tiles"]):
        fw, fh = tile["size"]
        ax, ay = tile["anchor"]
        object_tiles.append({"id": index, "image": tile["image"], "imagewidth": fw, "imageheight": fh,
            "properties": [{"name": "groundAnchor", "type": "string", "value": f"{ax},{ay}"}],
            "objectgroup": {"type": "objectgroup", "objects": [{"id": 1, "x": ax - 32, "y": ay - 48, "width": 64, "height": 48}]}})
    anchors = {tuple(t["anchor"]) for t in assets["tiles"]}
    sizes = {tuple(t["size"]) for t in assets["tiles"]}
    if len(anchors) != 1 or len(sizes) != 1:
        raise ValueError("Tiled demo exporter expects normalized common frames and anchors")
    ax, ay = next(iter(anchors))
    fw, fh = next(iter(sizes))
    objects = []
    for i, obj in enumerate(sorted(scene["objects"], key=lambda o: (o["row"], o["col"]))):
        if obj["tileId"] not in tile_by_id:
            raise ValueError(f"Unknown tile ID: {obj['tileId']}")
        index, _ = tile_by_id[obj["tileId"]]
        objects.append({"id": i + 1, "name": obj["tileId"], "gid": 100 + index,
                        "x": (obj["col"] + .5) * size, "y": (obj["row"] + 1) * size,
                        "width": fw, "height": fh, "rotation": 0, "visible": True})
    ground_tiles = [{"id": i, "image": f"ground/{name}.png", "imagewidth": size, "imageheight": size}
                    for i, name in enumerate(["grass-0", "grass-1", "grass-2", "road", "road-center"])]
    ground_data = []
    road = scene.get("roadColumns", [5, 6])
    center_col = road[len(road) // 2] if road else None
    for row in range(h):
        for col in range(w):
            ground_data.append((5 if col == center_col else 4) if col in road else 1 + (col * 7 + row * 11) % 3)
    value = {"type": "map", "version": "1.10", "tiledversion": "1.11.2", "orientation": "orthogonal",
        "renderorder": "right-down", "infinite": False, "width": w, "height": h,
        "tilewidth": size, "tileheight": size, "nextlayerid": 3, "nextobjectid": len(objects) + 1,
        "layers": [{"id": 1, "type": "tilelayer", "name": "Ground", "x": 0, "y": 0,
                    "width": w, "height": h, "opacity": 1, "visible": True, "data": ground_data},
                   {"id": 2, "type": "objectgroup", "name": "Y-sorted objects", "draworder": "topdown",
                    "opacity": 1, "visible": True, "objects": objects}],
        "tilesets": [{"firstgid": 1, "name": "Ground", "tilewidth": size, "tileheight": size,
                      "columns": 0, "tilecount": len(ground_tiles), "tiles": ground_tiles},
                     {"firstgid": 100, "name": "Overlapping sprites", "tilewidth": fw, "tileheight": fh,
                      "columns": 0, "tilecount": len(object_tiles), "objectalignment": "bottom",
                      "tileoffset": {"x": fw / 2 - ax, "y": fh - ay}, "tiles": object_tiles}]}
    write_json(output, value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    def image_args(name):
        command = sub.add_parser(name)
        command.add_argument("input", type=Path)
        command.add_argument("output", type=Path)
        return command
    crop = image_args("crop-alpha")
    crop.add_argument("--padding", type=int, default=4)
    crop.add_argument("--anchor", type=float, nargs=2)
    crop.add_argument("--threshold", type=int, default=8)
    clean = image_args("clean-alpha")
    clean.add_argument("--min-alpha", type=int, default=32)
    grid = image_args("split-grid")
    grid.add_argument("--cell", type=int, nargs=2, required=True)
    grid.add_argument("--columns", type=int, required=True)
    grid.add_argument("--rows", type=int, required=True)
    grid.add_argument("--margin", type=int, default=0)
    grid.add_argument("--spacing", type=int, default=0)
    components = image_args("split-components")
    components.add_argument("--min-area", type=int, default=32)
    components.add_argument("--join-radius", type=int, default=0)
    components.add_argument("--threshold", type=int, default=8)
    norm = image_args("normalize")
    norm.add_argument("--frame", type=int, nargs=2, default=[192, 320])
    norm.add_argument("--anchor-out", type=float, nargs=2, default=[96, 312])
    norm.add_argument("--anchor-in", type=float, nargs=2)
    norm.add_argument("--art-width", type=int, default=128)
    norm.add_argument("--footprint", type=int, nargs=2, default=[128, 128])
    norm.add_argument("--scale", type=float)
    norm.add_argument("--threshold", type=int, default=8)
    guides = sub.add_parser("guides")
    guides.add_argument("output", type=Path)
    atlas = sub.add_parser("pack")
    atlas.add_argument("manifest", type=Path)
    atlas.add_argument("output", type=Path)
    atlas.add_argument("--columns", type=int, default=4)
    atlas.add_argument("--padding", type=int, default=4)
    atlas.add_argument("--extrusion", type=int, default=2)
    atlas.add_argument("--no-trim", action="store_true")
    check = sub.add_parser("validate")
    check.add_argument("manifest", type=Path)
    tiled = sub.add_parser("export-tiled")
    tiled.add_argument("scene", type=Path)
    tiled.add_argument("manifest", type=Path)
    tiled.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "guides":
            generate_guides(args.output)
        elif args.command in {"crop-alpha", "normalize", "clean-alpha"}:
            image = load_rgba(args.input)
            if args.command == "clean-alpha":
                result, info = clean_alpha(image, args.min_alpha)
            elif args.command == "crop-alpha":
                result, info = crop_alpha(image, args.anchor, args.padding, args.threshold)
            else:
                result, info = normalize(image, tuple(args.frame), tuple(args.anchor_out), args.art_width,
                                         args.anchor_in, tuple(args.footprint), threshold=args.threshold, scale=args.scale)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            result.save(args.output)
            write_json(args.output.with_suffix(".json"), info)
        elif args.command in {"split-grid", "split-components"}:
            image = load_rgba(args.input)
            args.output.mkdir(parents=True, exist_ok=True)
            if args.command == "split-grid":
                parts = split_grid(image, tuple(args.cell), args.columns, args.rows, args.margin, args.spacing)
            else:
                parts = [(image.crop(box), {"sourceRect": list(box)}) for box in
                         component_rects(image, args.threshold, args.min_area, args.join_radius)]
                if not parts:
                    raise ValueError("No nonempty components; review min-area/threshold")
            cuts = []
            for index, (part, meta) in enumerate(parts):
                filename = f"tile-{index:03}.png"
                part.save(args.output / filename)
                cuts.append({"image": filename, **meta})
            write_json(args.output / "cuts.json", {"source": str(args.input), "tiles": cuts})
        elif args.command == "pack":
            assets = json.loads(args.manifest.read_text())
            items = [(t["id"], load_rgba(args.manifest.parent / t["image"]), t) for t in assets["tiles"]]
            result, info = pack_atlas(items, args.columns, args.padding, args.extrusion, not args.no_trim)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            result.save(args.output)
            info["meta"]["image"] = args.output.name
            write_json(args.output.with_suffix(".json"), info)
        elif args.command == "validate":
            report = validate_assets(json.loads(args.manifest.read_text()), args.manifest.parent)
            print(json.dumps(report, indent=2))
            if not report["ok"]:
                raise SystemExit(1)
        else:
            export_tiled(json.loads(args.scene.read_text()), json.loads(args.manifest.read_text()), args.output)
        print(f"{args.command}: complete")
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
