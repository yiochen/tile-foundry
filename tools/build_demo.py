#!/usr/bin/env python3
"""Build all demo artifacts from checked-in generated source images."""
from pathlib import Path
import json
import random

from PIL import Image, ImageDraw
from tilekit import crop_alpha, normalize, pack_atlas, write_json, export_tiled, generate_guides, load_rgba, validate_assets, clean_alpha

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public/assets"
TILE_NAMES = {"crate": ("Golden crate", "Low", "Wood"), "block": ("Coral block", "Low", "Toy brick"),
              "tree": ("Orchard tree", "Tall", "Foliage"), "house": ("Little cottage", "Medium", "Roof & plaster")}


def ground_tiles(directory):
    directory.mkdir(parents=True, exist_ok=True)
    for variant in range(3):
        im = Image.new("RGBA", (128, 128), "#91d844")
        draw = ImageDraw.Draw(im)
        randomizer = random.Random(100 + variant)
        # An 8px shared edge band keeps every variant compatible on all four sides.
        for i in range(14):
            x, y = randomizer.randrange(20, 108), randomizer.randrange(20, 108)
            r = randomizer.randrange(5, 12)
            draw.ellipse((x - r, y - r / 2, x + r, y + r / 2), fill=randomizer.choice(["#9cdf4e", "#85ce3b", "#a7e653"]))
        for i in range(7):
            x, y = randomizer.randrange(15, 112), randomizer.randrange(15, 112)
            draw.line([(x - 2, y), (x, y - 4), (x + 2, y)], fill="#72bc34", width=2)
        im.save(directory / f"grass-{variant}.png")
    road = Image.new("RGBA", (128, 128), "#a9b2b2")
    draw = ImageDraw.Draw(road)
    randomizer = random.Random(90)
    for i in range(40):
        x, y = randomizer.randrange(8, 120), randomizer.randrange(8, 120)
        draw.ellipse((x, y, x + 1, y + 1), fill="#9ba6a5")
    road.save(directory / "road.png")
    # Share lane paint between the browser and Tiled instead of drawing it only in UI.
    draw.rectangle((60, 31, 67, 94), fill="#f0f1e9")
    road.save(directory / "road-center.png")


def village_scene():
    objects = []
    def place(tile, positions):
        for col, row in positions:
            objects.append({"tileId": tile, "col": col, "row": row})
    place("tree", [(0,0),(4,0),(8,0),(10,0),(4,2),(8,2),(0,3),(10,3),
                   (4,4),(8,4),(0,6),(10,6),(4,7),(8,7),(0,9),(4,9),(8,9),(10,9)])
    # Consecutive rows visibly demonstrate foreground foliage covering back sprites.
    place("tree", [(4,1),(4,3),(4,5),(8,1),(8,3),(8,5)])
    place("house", [(1,1),(9,1),(1,5),(9,5),(2,8),(9,8)])
    place("block", [(1,2),(2,2),(3,2),(9,2),(1,3),(3,3),(9,3),
                    (1,6),(2,6),(3,6),(9,6),(2,9),(3,9)])
    place("crate", [(2,0),(3,1),(7,1),(6,3),(5,5),(6,5),(3,5),(7,6),(6,8),(5,10),(9,10)])
    return {"version": 1, "name": "Village lane", "width": 11, "height": 12, "roadColumns": [5,6,7], "objects": objects}


def stress_scene():
    randomizer = random.Random(20261010)
    return {"version": 1, "name": "Overlap stress test", "width": 11, "height": 12, "roadColumns": [],
            "objects": [{"tileId": randomizer.choice(list(TILE_NAMES)), "col": col, "row": row}
                        for row in range(12) for col in range(11) if randomizer.random() < .75]}


def main():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "sprites").mkdir(exist_ok=True)
    (ROOT / "assets/crops").mkdir(parents=True, exist_ok=True)
    config_path = ROOT / "assets/source-config.json"
    config = json.loads(config_path.read_text()) if config_path.exists() else {}
    tiles = []
    for tile_id, (label, height, material) in TILE_NAMES.items():
        source = ROOT / "assets/source" / f"{tile_id}.png"
        if not source.exists():
            raise SystemExit(f"Missing {source}; add transparent generated assets first")
        source_image = load_rgba(source)
        options = config.get(tile_id, {})
        cleaned, cleanup_meta = clean_alpha(source_image, options.get("minAlpha", 64))
        cropped, crop_meta = crop_alpha(cleaned, options.get("anchor"), padding=4)
        crop_meta["cleanup"] = cleanup_meta
        cropped.save(ROOT / "assets/crops" / f"{tile_id}.png")
        write_json(ROOT / "assets/crops" / f"{tile_id}.json", crop_meta)
        normalized, meta = normalize(cropped, anchor_in=crop_meta["anchor"],
                                     art_width=options.get("artWidth", 128))
        normalized.save(PUBLIC / "sprites" / f"{tile_id}.png")
        tiles.append({"id": tile_id, "name": label, "heightClass": height, "material": material,
                      "image": f"sprites/{tile_id}.png", "source": f"assets/source/{tile_id}.png",
                      **meta, "sourceAnchorMode": "explicit" if options.get("anchor") else "alpha-bottom-center",
                      "anchorReviewed": options.get("anchorReviewed", False),
                      "collision": {"x": -32, "y": -48, "width": 64, "height": 48}})
    assets = {"version": 1, "cellSize": 128, "frameSize": [192,320], "tiles": tiles,
              "ground": [f"ground/grass-{i}.png" for i in range(3)], "road": "ground/road.png",
              "roadCenter": "ground/road-center.png"}
    write_json(PUBLIC / "tiles.json", assets)
    items = [(t["id"], load_rgba(PUBLIC / t["image"]), t) for t in tiles]
    atlas, atlas_meta = pack_atlas(items)
    atlas.save(PUBLIC / "atlas.png")
    atlas_meta["meta"]["image"] = "atlas.png"
    write_json(PUBLIC / "atlas.json", atlas_meta)
    # A deterministic sheet fixture exercises grid and alpha-component cuts.
    sheet = Image.new("RGBA", (2*192+24, 2*320+24))
    for index, (_, image, _) in enumerate(items):
        sheet.paste(image, ((index%2)*216, (index//2)*344))
    sheet.save(PUBLIC / "sheet.png")
    ground_tiles(PUBLIC / "ground")
    generate_guides(ROOT / "assets/guides")
    scene, stress = village_scene(), stress_scene()
    write_json(PUBLIC / "village.json", scene)
    write_json(PUBLIC / "stress.json", stress)
    export_tiled(scene, assets, PUBLIC / "village.tmj")
    export_tiled(stress, assets, PUBLIC / "stress.tmj")
    report = validate_assets(assets, PUBLIC)
    boundary = [(x,y) for y in range(128) for x in range(128)
                if x < 8 or x >= 120 or y < 8 or y >= 120]
    ground_images = [Image.open(PUBLIC / f"ground/grass-{i}.png") for i in range(3)]
    report["groundEdgesMatch"] = all(im.getpixel(point) == (145,216,68,255)
                                    for im in ground_images for point in boundary)
    write_json(PUBLIC / "validation.json", report)
    print(json.dumps({"assets": len(tiles), "placedObjects": len(scene["objects"]), "atlasSize": atlas.size,
                      "validation": report}, indent=2))


if __name__ == "__main__":
    main()
