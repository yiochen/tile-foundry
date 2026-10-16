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

For a tall partial-base prop, a filled size envelope makes the crown limit more
legible than a line that may be interpreted as only its shaft:

```sh
python "$SKILL_DIR/scripts/guide_tools.py" envelope "$OUTPUT_DIR/guide" --height 160 --base 48 48
```

The envelope is a placeholder, not a requested box-shaped subject. Its top bar
marks the highest crown of the complete design at y=88, including finials/glass;
the ground root stays y=248. Ask for all details to fit this design height. The
48×48 base square stays screen-aligned; do not rotate it into a diamond. This
constrains extent without drawing the final design's features.

In the prompt also state the visible ratio: the entire crown-to-root height is
1.25 floor widths, and the base width/depth is 3/8 of the floor width. Treat
“tall” as the requested aspect within this scale; it does not authorize a
streetlamp several cell widths high. Inspect both the full crown and the base.

> Edit the supplied layout into [subject] in square-grid top-down oblique projection.
> Replace the gray subject placeholder; copy the calibration square's shape,
> placement, and flat color. The plain square
> defines position and scale; the sparse guide defines [posture/base/height].
> Invent the visual design. Preserve square size/location and its uniform reserved
> RGB 123,209,75, without a rim or cast shadow. Keep the projected ground root at
> its center. [Subject] has [height] and [clearance/support elevation]. Shoe toes
> may extend below the root; floating art keeps that ground projection beneath it.
> Reserve the calibration hue in overlapping object parts. Keep the complete
> subject inside its panel and use true alpha outside object and floor. Omit
> guide strokes, labels, scenery and checkerboard paint.

Use `transparent_background: true`, then inspect source alpha and visible floor.

Select the key before generation. The green example fits subjects that avoid
green/olive/yellow-green in the floor region. For characters with an invented
palette, use `--key-rgb 255 0 255` when creating the guide and use that recorded
magenta value in the prompt instead of the green example. Reserve the whole
key hue range, including its feather, in overlapping clothing. The processor
reads `guide.keyRGB`; it never guesses another color. Inspect original versus
processed clothing on light and dark backgrounds: clean floor removal can
still erase trousers or boots. A damaged foreground must fail cutout review.

```sh
python "$SKILL_DIR/scripts/tile_tools.py" process-on-floor "$OUTPUT_DIR/source.png" "$OUTPUT_DIR/guide.json" "$OUTPUT_DIR/processed" --min-alpha 32 --registration floor-width
```

Choose the registration basis before generation. For a disposable calibration
floor, `floor-width` measures the last wide opaque band with median side edges,
uniformly normalizes its width to 128px and its center to `[96,248]`,
then keys the explicitly registered floor region. The default key uses ±28° hue,
8° feather and saturation transition .02–.12. `--key-rgb` in guide creation records
another reserved color. Cutout bounds never determine scale or root position.

Width/center calibration does not require the disposable floor's height to be
exactly 128px after normalization. It never stretches axes or redraws the floor
into a square. The measured rectangle and uniform transform remain in the
sidecar. Inspect source edges and the registered subject: distortion, wrong scale
or shifted physical contact can still fail visual review. When square aspect is
itself a registration precondition, use the default `--registration square-floor`.
This retains the stricter aspect check. Neither mode certifies the artwork.

Mixed edges are approximate. A covered/unidentifiable floor, green object parts in the
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
python "$SKILL_DIR/scripts/guide_tools.py" dance "$OUTPUT_DIR/guide" --key-rgb 255 0 255
```

For twelve phases use `dance "$OUTPUT_DIR/guide" --frames 12 --columns 4 --key-rgb 255 0 255`.
It includes transitions between the six key poses and back to the first, with
equal panels and roots. Supply that actual raster; do not request a different
canvas or panel layout in prose. Ask to replace the sticks and preserve the
calibration squares as a layout edit. Specify total head-to-root design height
and anatomical scale; a hair cap is part of the height budget. Do not include the
eventual instruction to remove the floor in the generation prompt: that is the
processor's job. The generated source must still contain it.

The nominal standing design height is 1.25 calibration-cell widths including
hair. State this relative size alongside the numeric target. If the model still
enlarges the anatomy or redraws distorted floors, preserve the failed source;
more emphatic wording is not evidence that registration succeeded.

Use one composite raster for continuity when panels can remain independent.
Add exact frame count, row-major poses/actions and camera/scale constraints to
the object prompt. Pose words must describe required action without over-specifying
costume. Every panel retains the plain square; gutters stay truly transparent.
Repeated holds are acceptable only when requested. Inspect identity, limbs,
pose progression, complete silhouette and source panel separation.

```sh
python "$SKILL_DIR/scripts/tile_tools.py" process-on-floor "$OUTPUT_DIR/source.png" "$OUTPUT_DIR/guide.json" "$OUTPUT_DIR/processed" --min-alpha 32 --fps 12 --registration floor-width
```

Cuts use the known guide layout, allowing at most 1% source-aspect rounding.
Alpha in planned gutters is refused. If independent art merely protrudes into a
planned gutter, an inspected recovery can partition at actual transparent seams:

```sh
python "$SKILL_DIR/scripts/tile_tools.py" process-on-floor "$OUTPUT_DIR/source.png" "$OUTPUT_DIR/guide.json" "$OUTPUT_DIR/recovered" --min-alpha 32 --fps 12 --allow-gutter-drift --registration floor-width
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
