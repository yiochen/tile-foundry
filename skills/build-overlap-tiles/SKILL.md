---
name: build-overlap-tiles
description: Generate floor tiles, isolated objects, and character animation sheets for Tile Foundry using SVG guides, floor-derived scale and anchors, and removable calibration colors. Use for game tile or spritesheet generation, normalization, atlas packing, and overlap previews.
---

# Build overlap tiles

Run commands from the repository root. Generate new artwork with the available
image-generation tool; use `tools/tilekit.py` for deterministic processing.
Preserve original outputs, actual expanded prompts, and every supplied reference.

## Choose the workflow

- **Visible floor**, such as “generate a lava tile”: use a sparse square SVG as
  the sole image reference and generate a complete opaque ground material. Read
  [floor and object workflow](references/floor-and-objects.md), floor mode.
  The output is the floor itself; do not chroma-key its material colors.
- **Object/player on a tile**, including dancing or airborne poses: use a plain
  reserved-color calibration floor plus a sparse pose or height guide. Read
  [floor and object workflow](references/floor-and-objects.md), object mode.
  Measure the intact floor → uniformly normalize → key the reserved color →
  retain that frame and anchor. A stick pose leaves appearance to the model;
  detailed SVG art is appropriate when preserving an existing design.
- **Raised blocks, precise heights, or connected terrain**: read
  [SVG-led workflows](references/svg-workflows.md) and
  [geometry](references/geometry.md). Retain authored SVG geometry and composite
  AI material when exact silhouettes are required. Existing demo rebuilds use
  `python tools/build_demo.py` and `python tools/build_experiments.py`.

Use a sole SVG raster reference by default. Describe appearance in text. Add an
identity/style reference only when requested or needed for continuity, and record
it; a reference's object shape can bias generated geometry. These are practical
defaults from small experiments, not proof of reliable geometric fidelity.

## Geometry that survives post-processing

Keep logical footprint, art bounds, and anchor separate. Ground tiles default to
128×128 with center anchor (64,64). Calibration objects default to a 128px floor,
192×320 frame, and cell-center anchor (96,248). Legacy block/village art uses
(96,312); do not transfer that bottom anchor to calibrated characters.

The measured floor sets scale and position. Character height, shoe length, and
jump elevation do not alter grid pitch. The visible shoe bottom can extend below
the center; it is not an anchor error. Never fit animation anchors to boot
landmarks or recompute them after keying/cropping. Store `groundAnchorAlignment:
"center"` for calibration-object scenes and preserve it in Tiled export.

For animation, generate known isolated panels with transparent gutters, then
process each panel's intact floor independently. Strict `process-on-floor` rejects
art in planned gutters. If panels remain isolated, the documented transparent-
separator recovery can preserve protruding fingers without clipping. Aspect
distortion, touching panels, and frame overflow still fail. Never slice a flattened overlapping
scene or stretch a single axis to make a rejected output pass.

The calibration floor uses explicitly reserved RGB (123,209,75) by default;
chroma keying is intentional, not background-color inference. Reserve its hue in
object parts overlapping the floor, or choose another saturated key color.
Mixed boot/floor pixels have an approximate matte. Use a plain floor without
pale accents; detached-corner extraction is an alternative when exact retained
component pixels matter. Do not remove actual ground textures by this key.

## Deliver and check

Save sources and prompts before processing. Ship normalized PNGs, a result JSON
with measured floor/normalization/key settings, and per-frame anchors, timing,
and sheet layout for animations. Inspect cutouts against light and dark grounds,
and animations at the stored anchor; assess design consistency and motion as well
as alpha. Report limitations rather than claim exact AI geometry or seamlessness.

Only remove observed weak-alpha haze with an explicit reviewed threshold;
`process-on-floor --min-alpha 32` is the starting default. Raise it to 64 only
when inspection supports that choice. Preserve full silhouettes; enlarge frames
explicitly if needed. Generic `pack`, `validate`, `export-tiled`, `split-grid`,
and `split-components` commands are available through `tilekit.py --help`.

Run `python -m unittest discover -s tests`, `npm run assets`, `npm run build`,
and `npm run verify` after integration changes. Inspect actual desktop/mobile
screenshots. The existing **Characters** lab compares the saved seven trials;
`python tools/build_character_experiments.py` rebuilds them.

For behavioral tests of this skill, use [the eval protocol](evals/protocol.md).
It includes the short lava and dancing-player prompts, fresh generation runs,
artifact grading, and independent visual review. Do not substitute existing
courier outputs or a procedural drawing for a fresh-generation eval.
