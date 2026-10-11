# Geometry and acceptance

Coordinates are pixel-edge coordinates with a top-left origin. A canvas bottom can
be `y == height`; a ground anchor can also fall outside a tight alpha crop.

The demo uses a 128px square logical cell, a 192 × 320 art frame, and a (96,312)
ground anchor. The visible-art width is 128px by default; foliage or roof overhang
can differ from the actual collision footprint. Demo collision boxes are authored
64 × 48 rectangles relative to ground contact, not auto-derived from alpha.
The corrected solid block uses 130px full art, including its antialiased fringe,
to give a measured 128px opaque body. Its logical cell remains 128×128.

Character calibration experiments retain that grid/frame but use floor center
`(96,248)` as the ground anchor. The authored floor is `(32,184)`–`(160,312)`.
Airborne feet are not the anchor. Detect the floor center with `floor-anchor`;
use `isolate-marked` only when four guide corners are detached alpha components.
`subtract-floor` is an exact-reference diagnostic, not a general matte remover.
An explicitly supplied reserved floor color can be removed with `key-floor`;
measure and normalize from the intact floor first. The cutout keeps that scale,
full frame, and anchor. This is approximate chroma matting, not a guarantee of
unchanged boot edges. Do not treat the visible shoe bottom as anchor error: toe
length can extend below the cell center. The key operates only in measured floor
bounds, with a 3px fringe allowance. Green artwork there would also be removed.
See `docs/character-anchor-experiments.md` for tested limitations and commands.

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

The playground manifest also contains `blockVariants` (normalized tile entries)
and `blockVariantsAtlas` (the separate trimmed-atlas JSON filename), rebuilt by
`python tools/build_experiments.py` after `python tools/build_demo.py`. The editor's
four logical tile IDs remain unchanged. A scene may set `blockExperiment` to a
variant ID such as `svg-only-block` or `locked-wood-96`; absent or `original`
keeps the original coral block. The browser and `export-tiled` resolve every
`tileId: "block"` through that selection, using the variant's stored image,
frame, and anchor. Heights change visible art, never ground pitch. Unknown
experiment IDs fail import/export. Keep the extended `tiles.json` with scene JSON
when exporting experiment scenes to Tiled.

The Tiled exporter uses an image-collection tileset, bottom-centered objects,
a top-down draw-order object layer, and a tileset offset of `(0,8)` to compensate
for the 8px space below the frame's ground anchor. Its stored GIDs point at complete
sprites, not chopped art fragments. Ground is a separate tile layer.

Scenes may set `"groundAnchorAlignment":"center"` for characters; the default
remains `"bottom"` for prior block/village scenes. Center placement is
`((column+.5)*cellSize,(row+.5)*cellSize)`. The normalized character local anchor
`(96,248)` produces Tiled offset `(0,72)` in a `192×320` frame. Browser previews
must use the same center placement, without snapping airborne soles to the floor.

For a joinable opaque block, run:

```sh
python tools/tilekit.py check-solid public/assets/sprites/block.png tmp/block-check.json --anchor 96 312 --pitch 128 128 --preview
```

This writes the report and optional repeated-neighborhood proof on magenta. A
failure exits nonzero. The central cell must have no alpha below 250 after all
neighbors are drawn; near/far opaque side spans may differ by at most one pixel.
Use `--body-rect left top right bottom` to exclude intentional protrusions from
the side-span check. Review corner shapes, stud sizes, and camera tilt visually.
Declare `"solidCell": {"minAlpha": 250, "minCoverage": 1.0, "edgeTolerance": 1.0}`
on a manifest tile to include these checks in `validate`. Keep trees, roofs, and
other intentionally open silhouettes out of this test. Color/texture continuity
and mixed-height terrain remain separate requirements.

Acceptance:

- Alpha silhouette is complete; no unexpected glow, solid backdrop, or edge clipping.
- Crop metadata maps the local anchor back to the correct original ground contact.
- Normalizing preserves proportions and never silently crops overflowing art.
- Heights vary, cell pitch stays constant, and near/far instances stay the same size.
- Opaque solid-cell body covers adjacent cell joins, with parallel near/far edges.
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
