# Raised terrain from an opaque phase atlas

Use this route when authored faces should preserve a full base, fixed wall height,
and registration while AI supplies the moving material. The source is appearance
material, not a sheet of transparent objects. Read the shared prompt-scoping rule
in [prompts](prompts.md) before calling image generation.

Create the layout and a plain raised template before generation:

```sh
python "$SKILL_DIR/scripts/material_animation.py" guide "$OUTPUT_DIR/guide"
python "$SKILL_DIR/scripts/svg_tools.py" template "$OUTPUT_DIR/template" --height 32 --palette lava --plain
```

Use `--palette ocean` for water, or author matching SVG faces/masks for another
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
