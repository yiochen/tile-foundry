#!/usr/bin/env python3
"""Rebuild controlled workflow comparisons from saved AI outputs, without new AI calls."""
import json
from pathlib import Path

from PIL import Image, ImageChops
from svgkit import write_template, compose
from tilekit import clean_alpha, normalize, neighbor_coverage, parallel_edges, write_json, load_rgba

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public/assets/workflows"


def measure(image, expected, height=32):
    coverage, _ = neighbor_coverage(image, (96,312))
    parallel = parallel_edges(image)
    mask = image.getchannel("A").point(lambda a: 255 if a >= 250 else 0)
    target = expected.getchannel("A").point(lambda a: 255 if a >= 250 else 0)
    intersection = sum(a > 0 for a in ImageChops.darker(mask, target).tobytes())
    union = sum(a > 0 for a in ImageChops.lighter(mask, target).tobytes())
    box = mask.getbbox()
    return {"coverage": coverage, "parallel": parallel, "bodyHeight": box[3]-box[1],
            "targetBodyHeight": 128+height, "heightError": box[3]-box[1]-128-height,
            "silhouetteIoU": intersection/union, "alphaExact": image.getchannel("A").tobytes() == expected.getchannel("A").tobytes()}


def save_variant(tile_id, name, image, expected, method, note, height=32, **metadata):
    image.save(PUBLIC / f"{tile_id}.png")
    bbox = image.getbbox()
    metrics = measure(image, expected, height)
    return {"id": tile_id, "name": name, "image": f"workflows/{tile_id}.png", "size": list(image.size),
            "anchor": [96,312], "artRect": [bbox[0],bbox[1],bbox[2]-bbox[0],bbox[3]-bbox[1]],
            "method": method, "note": note, "metrics": metrics, **metadata}


def main():
    baseline_recipe = json.loads((ROOT / "assets/prompts/svg-guided-block.json").read_text())
    sphere_recipe = json.loads((ROOT / "assets/prompts/svg-sphere-block.json").read_text())
    if (baseline_recipe["prompt"] != sphere_recipe["prompt"] or
            baseline_recipe["transparentBackground"] != sphere_recipe["transparentBackground"] or
            baseline_recipe["references"][0] != sphere_recipe["references"][0] or
            sphere_recipe["references"] != [baseline_recipe["references"][0], "assets/source/plastic-style-sphere.png"]):
        raise SystemExit("Sphere comparison must replace only the second reference; keep prompt, SVG, and transparency unchanged")
    PUBLIC.mkdir(parents=True, exist_ok=True)
    template_dir = ROOT / "assets/templates/block-32"
    write_template(template_dir)
    target = load_rgba(template_dir / "template.png")
    cards = []
    # Same normalization policy for AI outputs: uniform scaling; no perspective
    # correction, silhouette clipping, face replacement, or axis stretching.
    config = json.loads((ROOT / "assets/experiment-config.json").read_text())
    for item in config["wholeSprites"]:
        image, cleanup = clean_alpha(load_rgba(ROOT / item["source"]), item["minAlpha"])
        image, normalization = normalize(image, art_width=item["artWidth"], anchor_in=item["anchor"])
        cards.append(save_variant(item["id"], item["name"], image, target, item["method"], item["note"],
                                  source=item["source"], processing={"cleanup":cleanup,"normalization":normalization}))
    variants = []
    for material, palette in (("plastic","coral"),("wood","amber")):
        for height in (16,32,64,96):
            directory = ROOT / f"assets/templates/{material}-{height}"
            write_template(directory, height=height, palette=palette)
            tile_id = f"locked-{material}-{height}"
            image = compose(directory, ROOT / f"assets/source/{material}-material.png", PUBLIC / f"{tile_id}.png", strength=.7)
            expected = load_rgba(directory / "template.png")
            variant = save_variant(tile_id, "SVG + AI material", image, expected, "Geometry stays in SVG",
                                   "SVG lighting + generated surface detail. Shape and face positions are authored.",
                                   height=height, material=material, elevation=height)
            if not variant["metrics"]["alphaExact"] or not variant["metrics"]["coverage"]["ok"] or not variant["metrics"]["parallel"]["ok"]:
                raise SystemExit(f"Locked geometry failed: {tile_id}")
            variants.append(variant)
    cards.append(next(v for v in variants if v["id"] == "locked-plastic-32"))
    for path in PUBLIC.glob("*.png"):
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
    results = {"version":1, "cellSize":128, "target":{"width":128,"depth":128,"height":32,"bodyHeight":160},
               "cards":cards, "lockedVariants":variants,
               "scope":"One saved output for each of three SVG-reference strategies: block style, SVG only, and sphere style. The sphere trial uses the block-style prompt unchanged, replacing only its second input image; calls were made at different times without a recorded model version or seed. Two generated materials, four deterministic heights per material. Not a statistical model benchmark. Coverage tests identical solid cells; IoU tests silhouette only."}
    write_json(ROOT / "public/assets/workflows.json", results)
    write_json(ROOT / "docs/workflow-comparison.json", results)
    print(json.dumps({"cards":[{"id":c["id"],"missing":c["metrics"]["coverage"]["uncoveredPixels"],
                              "heightError":c["metrics"]["heightError"],"parallel":c["metrics"]["parallel"]["ok"],
                              "IoU":round(c["metrics"]["silhouetteIoU"],4)} for c in cards],
                      "lockedVariants":len(variants),"exactAlphaAll":all(v["metrics"]["alphaExact"] for v in variants)}, indent=2))


if __name__ == "__main__":
    main()
