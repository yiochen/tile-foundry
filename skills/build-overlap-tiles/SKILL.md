---
name: build-overlap-tiles
description: Generate square-grid game floors, raised objects, characters, and animation sheets in top-down oblique projection, with reusable ground anchors, independent footprints, removable calibration guides, and 12 fps animation.
---

# Build overlap tiles

Use this skill in any target project. Resolve `SKILL_DIR` to the directory
containing this file and `OUTPUT_DIR` to the user-requested asset destination.
Keep outputs there; do not assume a repository layout, engine, playground, or API
credentials. Bundled commands work from any current directory:

```sh
python -m pip install -r "$SKILL_DIR/scripts/requirements.txt"
python "$SKILL_DIR/scripts/guide_tools.py" object "$OUTPUT_DIR/guide"
```

Generate new artwork with the available image-generation tool. Use bundled scripts
for deterministic processing. Retain original generated images, exact expanded
prompts, references, SVGs, raster guides, and processing metadata.

## Target projection

Use **top-down oblique projection, square-grid, front-facing three-quarter game
view**. Ground cells remain screen-aligned squares; object tops and fronts are
visible, parallel edges retain their direction, and height projects upward over
the row behind. This is an illustrated parallel-projection convention; “3/4” does
not specify a physical camera angle. Read [projection](references/projection.md)
and inspect the bundled reference when choosing a guide. Record the projection
profile with the result, and use it consistently across poses and frames.

## Choose geometry and guidance

- **Flat floor:** generate an opaque square surface from a sparse SVG raster.
  Keep the complete square. Inspect repeated neighbors for color/pattern continuity,
  not just full alpha. Read [floor and object workflow](references/floor-and-objects.md).
- **Full-cell raised object:** retain a full square logical base and explicit
  elevation. A raised lava tile includes a front wall. For exact joins, use
  authored SVG faces plus generated materials; for a whole-object AI render,
  measure and report any geometry drift. Read [SVG workflows](references/svg-workflows.md).
- **Partial-base or floating object / character:** use a plain, explicitly reserved
  calibration color and sparse height/pose guide. Measure the intact visible floor,
  normalize uniformly, remove the calibration substrate, and retain that frame
  and anchor. Sparse guides leave appearance to the model.
- **Directions or animation:** keep the camera, anatomy scale, floor registration,
  and root fixed. Turn or pose the subject. All animations use **12 fps**
  (`1000/12` ms per frame). A changing pose may change silhouette bounds; never
  resize each frame to force an equal bounding-box height.
- **Multi-cell, disjoint support, arch, or stacked layers:** declare footprint,
  occupied/support cells, overhead extent, support elevation, and layer/depth
  pieces before generation. Read [geometry and output contract](references/geometry.md).
  Preserve complete separate assets. Do not slice a flattened overlapping scene.

Use a sole SVG raster reference by default, with style described in text. Supply
an identity or support reference when continuity/attachment needs it and record
its role. The bundled scene illustrates projection; it is not a default style
reference to supply to every image call. A style image's object shape can bias
geometry. Inspect each input raster before using it.

## Anchors and extraction

Defaults: 128px ground cell; flat floor 128×128 with center anchor (64,64);
single-cell object 192×320 with projected ground-center anchor (96,248) and
calibration floor `(32,184)–(160,312)`. Frame size is configurable and must grow
for large/tall art. Height does not change grid pitch or scale the entire sprite.

The floor or authored registration determines position/scale independently of
feet and alpha bounds. Shoe toes can extend below the anchor. Floating art keeps
its ground projection; a seated layer retains its ground anchor plus separate
support elevation. Do not apply an elevation twice during recomposition.

Use the explicitly recorded calibration color (default RGB 123,209,75), never
background-color guessing. Reserve its hue in overlapping object parts.
Normalize before keying; keep the resulting frame and anchor. Mixed edges have
an approximate matte. A fully covered floor cannot be measured by the visible-
floor detector: use authored geometry/registration or report unsupported input.
The bundled single-cell processor is not a general multi-cell or layer extractor.

## Deliver and evaluate

Deliver transparent sprites (opaque flat floors), per-sprite ground anchors,
logical occupancy, art bounds, projection, elevation, and animation order/timing.
Use the portable [output contract](references/geometry.md). Inspect placement,
light/dark cutouts, repeated terrain, and animation at the stored ground point.
Never claim exact AI geometry, seamless terrain, or successful separation solely
from metadata. Keep failures and report limits; do not conceal them with clipping,
axis stretching, anchor fitting, or grading changes.

The [13-case eval suite](evals/cases.json) is specified before fresh generation.
Use [the eval protocol](evals/protocol.md) to prepare isolated output destinations
and independent review. A prepared case is not a passed case. Freeze its rubric
and this skill snapshot before a run; do not tune the skill to make that run pass.
