"""Project playground Tiled adapter; shared processing lives in the portable skill."""
from tile_tools import write_json

def export_tiled(scene, assets, output):
    tiles = list(assets['tiles'])
    experiment = scene.get('blockExperiment', 'original')
    if experiment != 'original':
        variant = next((t for t in assets.get('blockVariants', []) if t['id'] == experiment), None)
        if variant is None:
            raise ValueError(f"Unknown block experiment: {experiment}")
        if not any(t['id'] == 'block' for t in tiles):
            raise ValueError("Block experiment requires a block tile in the manifest")
        tiles = [{**variant, 'id': 'block'} if t['id'] == 'block' else t for t in tiles]
    tile_by_id = {tile["id"]: (index, tile) for index, tile in enumerate(tiles)}
    w, h = scene["width"], scene["height"]
    size = assets["cellSize"]
    alignment=scene.get('groundAnchorAlignment','bottom')
    if alignment not in ('bottom','center'):
        raise ValueError("groundAnchorAlignment must be bottom or center")
    row_offset=.5 if alignment=='center' else 1
    # Image collection avoids assuming image height == logical map cell height.
    object_tiles = []
    for index, tile in enumerate(tiles):
        fw, fh = tile["size"]
        ax, ay = tile["anchor"]
        object_tiles.append({"id": index, "image": tile["image"], "imagewidth": fw, "imageheight": fh,
            "properties": [{"name": "groundAnchor", "type": "string", "value": f"{ax},{ay}"}],
            "objectgroup": {"type": "objectgroup", "objects": [{"id": 1, "x": ax - 32, "y": ay - 48, "width": 64, "height": 48}]}})
    anchors = {tuple(t["anchor"]) for t in tiles}
    sizes = {tuple(t["size"]) for t in tiles}
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
                        "x": (obj["col"] + .5) * size, "y": (obj["row"] + row_offset) * size,
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
    if experiment != 'original':
        value['properties'] = [{'name': 'blockExperiment', 'type': 'string', 'value': experiment}]
    write_json(output, value)
    return value
