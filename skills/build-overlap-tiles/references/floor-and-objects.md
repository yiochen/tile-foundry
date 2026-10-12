# Floors, calibration objects and animation

Commands use `SKILL_DIR` (this copied skill's directory) and the requested
`OUTPUT_DIR`, from any working directory. Install bundled Python dependencies.
Use an inspected local SVG raster as the image reference; retain SVG/layout too.
Follow the [projection profile](projection.md) and [output contract](geometry.md).

## Flat visible floor

A visible floor is final artwork, distinct from disposable calibration color.
Generate a complete opaque square, 128×128 at runtime, without a front wall.
For a raised lava tile, use the raised-object workflow instead.

```sh
python "$SKILL_DIR/scripts/guide_tools.py" floor "$OUTPUT_DIR/guide"
```

Prompt example:

> Generate one opaque square [material] floor in the supplied screen-aligned
> square. Fill every edge with a repeatable surface. Continue patterns and colors
> across opposite edges; avoid lighting gradients that jump at joins. No raised
> cube, props, borders, empty margins or text. Keep the top-down ground plane.

Use `transparent_background: false`. Preserve `source.png` and its recipe.

```sh
python "$SKILL_DIR/scripts/tile_tools.py" floor-material "$OUTPUT_DIR/source.png" "$OUTPUT_DIR/tile.png"
```

This uniformly downsamples the whole square and refuses transparent gaps or
non-square input. Inspect actual 3×3/5×5 repeats at native and enlarged scale.
Require connected texture, no seams and no sudden gradient jumps when requested;
merely recording that a repeat was inspected is not a pass. An approved edge band
can be preserved in interior edits, but retain the raw image and disclose processing.

## Partial-base or floating object

```sh
python "$SKILL_DIR/scripts/guide_tools.py" object "$OUTPUT_DIR/guide"
```

The bundled example is a sparse stick figure over a plain 128px square in a
192×320 frame. Author another height/pose guide without costume details when
appearance should remain creative. For floating art, put the guide's ground root
beneath the subject and specify its elevation/clearance independently.

> Generate [subject] in square-grid top-down oblique projection. The plain square
> defines position and scale; the sparse guide defines [posture/base/height].
> Invent the visual design. Preserve square size/location and its uniform reserved
> RGB 123,209,75, without a rim or cast shadow. Keep the projected ground root at
> its center. [Subject] has [height] and [clearance/support elevation]. Shoe toes
> may extend below the root; floating art keeps that ground projection beneath it.
> Reserve the calibration hue in overlapping object parts. Keep the complete
> subject inside its panel and use true alpha outside object and floor. Omit
> guide strokes, labels, scenery and checkerboard paint.

Use `transparent_background: true`, then inspect source alpha and visible floor.

```sh
python "$SKILL_DIR/scripts/tile_tools.py" process-on-floor "$OUTPUT_DIR/source.png" "$OUTPUT_DIR/guide.json" "$OUTPUT_DIR/processed" --min-alpha 32
```

The processor measures the last wide opaque band with median side edges, checks
square aspect, uniformly normalizes its width to 128px and its center to `[96,248]`,
then keys the explicitly registered floor region. The default key uses ±28° hue,
8° feather and saturation transition .02–.12. `--key-rgb` in guide creation records
another reserved color. Cutout bounds never determine scale or root position.

Mixed edges are approximate. A covered/warped floor, green object parts in the
key region, or frame overflow can invalidate extraction. Reject/report the
failure rather than fitting feet, guessing background colors, or clipping art.
This command does not handle arbitrary multi-cell or hidden support layers.

## Direction sheets and animation

Directions rotate the subject around its ground root with a fixed camera and
nominal anatomy scale. Use neutral upright poses when testing height consistency.
Keep separate complete frames; never normalize each to its own alpha height.

All animation schedules are 12 fps, `1000/12` ms per frame. The bundled six-pose
example guide is a starting point; frame count, frame size and pose layout can be
authored for the request. The 12-frame evals require a 12-panel guide; do not
silently reuse a six-panel guide for them.

```sh
python "$SKILL_DIR/scripts/guide_tools.py" dance "$OUTPUT_DIR/guide"
```

Use one composite raster for continuity when panels can remain independent.
Add exact frame count, row-major poses/actions and camera/scale constraints to
the object prompt. Pose words must describe required action without over-specifying
costume. Every panel retains the plain square; gutters stay truly transparent.
Repeated holds are acceptable only when requested. Inspect identity, limbs,
pose progression, complete silhouette and source panel separation.

```sh
python "$SKILL_DIR/scripts/tile_tools.py" process-on-floor "$OUTPUT_DIR/source.png" "$OUTPUT_DIR/guide.json" "$OUTPUT_DIR/processed" --min-alpha 32 --fps 12
```

Cuts use the known guide layout, allowing at most 1% source-aspect rounding.
Alpha in planned gutters is refused. If independent art merely protrudes into a
planned gutter, an inspected recovery can partition at actual transparent seams:

```sh
python "$SKILL_DIR/scripts/tile_tools.py" process-on-floor "$OUTPUT_DIR/source.png" "$OUTPUT_DIR/guide.json" "$OUTPUT_DIR/recovered" --min-alpha 32 --fps 12 --allow-gutter-drift
```

Recovery assigns every retained source-alpha pixel to one panel and records cuts.
It refuses touching art or missing separators; do not raise alpha thresholds to
erase real limbs. Keep failures. Do not automatically retry eval cases; their
protocol fixes the allowed attempt budget before a run.

Review playback on light/dark grounds at the stored root and declared 12 fps.
Check anatomy scale rather than constant silhouette bounds: dance/crouch/jump
poses legitimately change visible extent. Raised animated terrain also needs
spatial repeats at every frame and last-to-first temporal-loop review. Source
recipes and per-frame timing/geometry must survive delivery.
