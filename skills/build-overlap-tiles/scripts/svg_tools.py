#!/usr/bin/env python3
"""Exact SVG block geometry, raster references, face masks, and material compositing.

AI generates appearance. This tool owns geometry. All coordinates are logical pixels.
"""
import argparse
from io import BytesIO
import json
from pathlib import Path

import cairosvg
from PIL import Image, ImageChops, ImageFilter

PALETTES = {
    "coral": ("#f4593e", "#d63223", "#ff9270"),
    "amber": ("#e5a633", "#aa661e", "#ffe091"),
    "mint": ("#51ba93", "#238766", "#a6efc5"),
    "ocean": ("#3c9ed1", "#23699e", "#85d7f1"),
    "lava": ("#eb5b24", "#a42b18", "#ffb344"),
}


def block_svg(height=32, width=128, depth=128, frame=(192, 320), anchor=(96, 312),
              palette="coral", shaded=False, layer=None, plain=False, terrain=False):
    """Front-on parallel projection: horizontal top face and vertical front face.

    Side edges cannot converge. The top face is exactly width × depth; height is
    a screen-space elevation, not a change in camera angle. Only this block
    primitive is implemented; other objects need their own face geometry.
    """
    if any(not isinstance(v, int) or v < 1 for v in (height, width, depth, *frame)):
        raise ValueError("Dimensions must be positive integers")
    x, top, front, bottom = anchor[0] - width / 2, anchor[1] - depth - height, anchor[1] - height, anchor[1]
    if not all(float(v).is_integer() for v in (x, top, front, bottom)):
        raise ValueError("Body edges must align to pixels; use an even width with an integer anchor")
    if x < 0 or x + width > frame[0] or top < 0 or bottom > frame[1]:
        raise ValueError("Geometry exceeds the frame; enlarge the frame explicitly")
    if palette not in PALETTES:
        raise ValueError("Unknown palette")
    color, dark, light = PALETTES[palette]
    opening = f'<svg xmlns="http://www.w3.org/2000/svg" width="{frame[0]}" height="{frame[1]}" viewBox="0 0 {frame[0]} {frame[1]}">'
    defs = f'''<defs>
      <linearGradient id="top" x2="0" y2="1"><stop stop-color="{light}"/><stop offset=".18" stop-color="{color}"/><stop offset="1" stop-color="{color}"/></linearGradient>
      <linearGradient id="front" x2="0" y2="1"><stop stop-color="{color}"/><stop offset=".13" stop-color="{dark}"/><stop offset="1" stop-color="{dark}"/></linearGradient>
      <radialGradient id="cap" cx=".32" cy=".25" r=".8"><stop stop-color="{light}"/><stop offset=".55" stop-color="{color}"/><stop offset="1" stop-color="{dark}"/></radialGradient>
    </defs>'''
    top_rect = f'<rect x="{x}" y="{top}" width="{width}" height="{depth}" fill="{("url(#top)" if shaded and not terrain else color) if not layer else "white"}"/>'
    front_rect = f'<rect x="{x}" y="{front}" width="{width}" height="{height}" fill="{("url(#front)" if shaded and not terrain else dark) if not layer else "white"}"/>'
    studs = []
    for fx in (() if plain else (.25, .75)):
        for fy in (.25, .75):
            cx, cy, rx, ry, rise = x + fx * width, top + fy * depth, width * .16, depth * .095, depth * .055
            if shaded and not layer:
                studs.append(f'<ellipse cx="{cx}" cy="{cy+4}" rx="{rx+2}" ry="{ry+2}" fill="{dark}" opacity=".25"/>')
            studs.append(f'<path d="M {cx-rx},{cy-rise} a {rx},{ry} 0 0 1 {2*rx},0 v {rise} a {rx},{ry} 0 0 1 {-2*rx},0 z" fill="{dark if not layer else "white"}"/>')
            studs.append(f'<ellipse cx="{cx}" cy="{cy-rise}" rx="{rx}" ry="{ry}" fill="{("url(#cap)" if shaded else light) if not layer else "white"}"/>')
    content = {"silhouette": top_rect + front_rect, "top": top_rect, "front": front_rect,
               "studs": "".join(studs)}.get(layer, top_rect + front_rect + "".join(studs))
    # Decorations never determine body coverage. Everything stays within its faces.
    if shaded and not layer and not terrain:
        content += f'<path d="M {x+1},{front-1} H {x+width-1}" stroke="{light}" stroke-width="2" opacity=".55"/>'
        content += f'<path d="M {x+1},{bottom-1} H {x+width-1}" stroke="{dark}" stroke-width="2"/>'
    return opening + defs + content + "</svg>"


def rasterize(svg, scale=1):
    if scale <= 0:
        raise ValueError("Scale must be positive")
    return Image.open(BytesIO(cairosvg.svg2png(bytestring=svg.encode(), scale=scale))).convert("RGBA")


def write_template(directory, **options):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    height, width, depth = (options.get(k, d) for k, d in (("height", 32), ("width", 128), ("depth", 128)))
    frame, anchor = options.get("frame", (192, 320)), options.get("anchor", (96, 312))
    for shaded, name in ((False, "template"), (True, "shaded")):
        svg = block_svg(**options, shaded=shaded)
        (directory / f"{name}.svg").write_text(svg + "\n")
        rasterize(svg).save(directory / f"{name}.png")
    rasterize(block_svg(**options), scale=4).save(directory / "reference-4x.png")
    for name in ("silhouette", "top", "front", "studs"):
        rasterize(block_svg(**options, layer=name)).getchannel("A").save(directory / f"mask-{name}.png")
    meta = {"version": 1, "primitive": "parallel-block", "size": list(frame), "anchor": list(anchor),
            "cellSize": [width, depth], "height": height, "palette": options.get("palette", "coral"),
            "bodyRect": [anchor[0]-width/2, anchor[1]-depth-height, anchor[0]+width/2, anchor[1]],
            "topRect": [anchor[0]-width/2, anchor[1]-depth-height, anchor[0]+width/2, anchor[1]-height],
            "frontRect": [anchor[0]-width/2, anchor[1]-height, anchor[0]+width/2, anchor[1]]}
    (directory / "geometry.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def materialize(base, texture, masks, strength=.45):
    """Modulate SVG appearance inside nonoverlapping faces; copy its alpha exactly.

    Remove broad lighting from the generated material so it doesn't compete with
    the SVG's face lighting. This is a material-detail pass, not AI object editing.
    """
    if not 0 <= strength <= 1:
        raise ValueError("Strength must be between 0 and 1")
    base, texture = base.convert("RGBA"), texture.convert("RGB")
    rgb = base.convert("RGB")
    # Blur in source units: retain grain and medium-scale material marks.
    blur = texture.filter(ImageFilter.GaussianBlur(max(texture.size) / 24))
    detail = ImageChops.subtract(texture, blur, scale=1, offset=128)
    total_mask = Image.new("L", base.size)
    for name in ("top", "front", "studs"):
        mask = masks[name].convert("L")
        if mask.size != base.size:
            raise ValueError("Mask and base sizes differ")
        if name != "studs":
            mask = ImageChops.subtract(mask, masks["studs"].convert("L"))
        mask = ImageChops.subtract(mask, total_mask)
        bbox = mask.getbbox()
        if not bbox:
            continue
        placed = Image.new("RGB", base.size, (128,128,128))
        placed.paste(detail.resize((bbox[2]-bbox[0], bbox[3]-bbox[1]), Image.Resampling.LANCZOS), bbox[:2])
        # Signed channel deltas preserve both highlights and darker grain.
        varied = Image.merge("RGB", [ImageChops.add(c, d, scale=1, offset=-128)
                                      for c, d in zip(rgb.split(), placed.split())])
        blend = Image.blend(rgb, varied, strength)
        rgb = Image.composite(blend, rgb, mask)
        total_mask = ImageChops.lighter(total_mask, mask)
    rgb.putalpha(base.getchannel("A"))
    return rgb


def compose(directory, texture_path, output, strength=.45):
    directory = Path(directory)
    with Image.open(directory / "shaded.png") as base, Image.open(texture_path) as texture:
        if texture.convert("RGBA").getchannel("A").getextrema()[0] != 255:
            raise ValueError("Material texture must be opaque; generate a flat material, not an object cutout")
        masks = {name: Image.open(directory / f"mask-{name}.png").convert("L") for name in ("top", "front", "studs")}
        image = materialize(base, texture, masks, strength)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    template = sub.add_parser("template", help="SVG, flat/shaded rasters, 4x AI reference, face masks and geometry JSON")
    template.add_argument("directory", type=Path)
    template.add_argument("--height", type=int, default=32)
    template.add_argument("--width", type=int, default=128)
    template.add_argument("--depth", type=int, default=128)
    template.add_argument("--frame", type=int, nargs=2, default=(192,320))
    template.add_argument("--anchor", type=int, nargs=2, default=(96,312))
    template.add_argument("--palette", choices=PALETTES, default="coral")
    template.add_argument("--plain", action="store_true", help="Undecorated raised surface; empty studs mask")
    template.add_argument("--terrain", action="store_true", help="Continuous terrain: uniform face lighting, no tile-edge highlights")
    texture = sub.add_parser("material", help="Generated flat material details inside SVG faces; exact SVG alpha")
    texture.add_argument("directory", type=Path)
    texture.add_argument("texture", type=Path)
    texture.add_argument("output", type=Path)
    texture.add_argument("--strength", type=float, default=.45)
    args = vars(parser.parse_args())
    command = args.pop("command")
    if command == "template":
        directory = args.pop("directory")
        print(json.dumps(write_template(directory, **args), indent=2))
    else:
        image = compose(args["directory"], args["texture"], args["output"], args["strength"])
        print(json.dumps({"output": str(args["output"]), "size": image.size, "alpha": "copied exactly from SVG"}))


if __name__ == "__main__":
    main()
