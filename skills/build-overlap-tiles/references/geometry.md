# Geometry and acceptance

Coordinates are pixel-edge coordinates with a top-left origin. A canvas bottom can
be `y == height`; a ground anchor can also fall outside a tight alpha crop.

The demo uses a 128px square logical cell, a 192 × 320 art frame, and a (96,312)
ground anchor. The visible-art width is 128px by default; foliage or roof overhang
can differ from the actual collision footprint. Demo collision boxes are authored
64 × 48 rectangles relative to ground contact, not auto-derived from alpha.

For a cell `(column,row)`, ground anchor is at
`((column + .5) * 128, (row + 1) * 128)`. Draw back-to-front by that ground Y.
Trimmed atlas anchors are relative to the trimmed frame. PNG anchors are relative
to the original fixed frame. Do not mix the two coordinate systems.

For generic `pack`, write a manifest beside the sprite images. Each `image` path
is relative to the manifest, and the anchor uses that image's local coordinates:

```json
{
  "cellSize": 128,
  "tiles": [
    {"id": "tree", "image": "tree.png", "size": [192, 320],
     "anchor": [96, 312], "footprint": [128, 128]}
  ]
}
```

Copy `size`, `anchor`, and `footprint` from each `normalize` JSON sidecar rather than
assuming them. `pack` minimally needs `tiles[].id`, `image`, and `anchor`; `validate`
also needs an alpha image and anchor. `export-tiled` requires `cellSize`, sprite
`size`, shared frames/anchors, and scene `width`, `height`, and `objects` containing
`tileId`, `col`, and `row`. Keep the `.tmj` output beside the manifest so its relative
image paths stay valid. Demo ground files live under `ground/` next to that map.

The Tiled exporter uses an image-collection tileset, bottom-centered objects,
a top-down draw-order object layer, and a tileset offset of `(0,8)` to compensate
for the 8px space below the frame's ground anchor. Its stored GIDs point at complete
sprites, not chopped art fragments. Ground is a separate tile layer.

Acceptance:

- Alpha silhouette is complete; no unexpected glow, solid backdrop, or edge clipping.
- Crop metadata maps the local anchor back to the correct original ground contact.
- Normalizing preserves proportions and never silently crops overflowing art.
- Heights vary, cell pitch stays constant, and near/far instances stay the same size.
- Dense front rows cover the appropriate back rows, independent of insertion order.
- Atlas trimming reconstructs every nonzero source alpha pixel and keeps the anchor.
- Atlas gutters do not become visible at preview scale.
- All floor variants retain the shared boundary band; no cracks at tile joins.
- UI fits a 390px mobile viewport; imports, cell edits, undo, and downloads work.

Limitations:

- Disconnected alpha components can belong to one sprite. Use an explicit grouping
  radius, a regular sheet layout, or individual generation. Touching objects cannot
  be separated by flood fill without an authored mask.
- Automatic alpha-bottom-center is a starting estimate, not a geometry measurement.
- Simple ground-Y sorting assumes one-cell objects without bridges or interlocking
  multi-cell occlusion. Split complex structures into authored depth pieces.
- Continuous elevated terrain needs neighbor-height edge/face rules and dedicated
  art; this demo demonstrates independent objects with visual overlap.
