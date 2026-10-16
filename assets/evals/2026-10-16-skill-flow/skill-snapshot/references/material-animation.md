# Raised terrain animation

Choose the animation source before generation. For flowing surfaces, prefer one
AI material with authored periodic texture motion. Use a phase atlas when the
request specifically needs model-drawn evolving features. Both preserve authored
geometry; neither establishes good seams or motion without visual inspection.

## One material with authored flow

This route generates appearance once and animates its texture coordinates. It
does not ask the image model to draw twelve aligned phases. Preserve that
distinction in provenance; do not describe the output as twelve AI-drawn poses.

Before generation, record twelve phases, 12 fps, horizontal one-tile-per-cycle
UV translation and a 16px stationary edge blend in `registration.json`.

```sh
python "$SKILL_DIR/scripts/guide_tools.py" floor "$OUTPUT_DIR/guide"
python "$SKILL_DIR/scripts/svg_tools.py" template "$OUTPUT_DIR/template" --height 32 --palette lava --plain --terrain
```

Use `--palette ocean` for waves. `--terrain` removes the block helper's broad
lighting gradients and bevel highlights that otherwise restart at every tile.
The front face is still darker, with the requested physical extent.

Inspect the square guide, then generate a single flat, full opaque seamless
[lava/water] material suitable for continuous flowing motion. Ask for connected
features, constant average illumination, periodic opposite edges, no rim,
directional lighting gradient, perspective, layout gutters or raised geometry.
Set `transparent_background: false`, retain the original and recipe, and use
`role: "appearance-material"` in the source record.

```sh
python "$SKILL_DIR/scripts/material_flow.py" compose "$OUTPUT_DIR/template" "$OUTPUT_DIR/source.png" "$OUTPUT_DIR/processed" --strength .7 --edge-band 16
```

The helper wraps the entire generated texture through one cycle, maps it onto
the authored faces, and smoothly blends moving detail to the initial material
near each face boundary. Boundaries stay phase-independent so neighboring tiles
can use offset phases. It records source offsets, blend parameters, hashes and
unchanged alpha; it does not infer geometry from the art. The whole source is
sampled, with no gutter windows or generated object cropping. The PNGs and timing
sidecar work with `assemble_result.py`.

The boundary blend is an explicit animation design choice: flow is strongest
inside a tile. It cannot fix a conspicuously nonperiodic original texture, make
feature morphing or splashes, or animate a character. Inspect native/2× repeats,
offset-phase neighbors and 12 fps playback, including the last-to-first step.
Preserve failures rather than declaring a loop successful from its clock alone.

## Model-drawn phase atlas

Use this route when authored faces should preserve a full base, fixed wall height,
and registration while AI supplies the moving material. The source is appearance
material, not a sheet of transparent objects. Read the shared prompt-scoping rule
in [prompts](prompts.md) before calling image generation.

Create the layout and a plain raised template before generation:

```sh
python "$SKILL_DIR/scripts/material_animation.py" guide "$OUTPUT_DIR/guide"
python "$SKILL_DIR/scripts/svg_tools.py" template "$OUTPUT_DIR/template" --height 32 --palette lava --plain
```

Add `--terrain` for connected surfaces. Use `--palette ocean` for water, or author matching SVG faces/masks for another
surface. The block helper's anchor is the near ground edge `(96,312)`; the
animation helper converts that metadata to ground center `(96,248)` without
moving the image. Do not apply another 64px shift.

Inspect the opaque square guide, then request only the atlas:

> Replace the twelve gray square samples with twelve successive phases of
> [moving lava / rolling water] in row-major order, forming a one-second loop.
> Keep the exact sample layout and square boundaries. Every sample is a flat,
> fully opaque material texture, filled to its edges. Keep all gutters and
> outer margins opaque too. Use a fixed palette, texture scale and lighting.
> Phase 12 leads into phase 1. Continue surface patterns across opposite edges
> in every phase, including neighbors displaying different phases. No raised
> objects, perspective, scene, text, borders, transparent pixels or cutout shapes.

Set `transparent_background: false`. Do not include the eventual transparent
sprite dimensions or request the front wall in this image prompt. Save the whole
original atlas and exact recipe. In an eval submission its source role is
`appearance-material`, with the actual opaque generation flag recorded.

```sh
python "$SKILL_DIR/scripts/material_animation.py" compose "$OUTPUT_DIR/template" "$OUTPUT_DIR/source.png" "$OUTPUT_DIR/guide.json" "$OUTPUT_DIR/processed" --strength .7
```

The helper samples the declared square material regions at one uniform source
scale, then maps their detail into the authored faces. It preserves the SVG alpha
and palette. It records sample rectangles, masks, frame timing and registration;
use its result with `assemble_result.py`. Sampling a material region is appropriate
here; it would be clipping if applied to a whole-object source. Do not use this
route to replace a generated object with a different silhouette after seeing it.

This is a detail-compositing route. It does not create motion that the atlas lacks,
preserve arbitrary large material features, or establish seamless joins. Generated
phase/layout drift and independent face mapping may still produce visible seams
or a poor loop. Inspect all 12 phases, 3×3 neighbors including offset phases, and
actual 12 fps playback on the complete raised tile. Preserve failed attempts.
