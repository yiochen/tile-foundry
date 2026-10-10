# SVG-led workflow experiments

Choose what owns geometry before generating appearance.

| Path | Good fit | Geometry owner | Main limitation |
| --- | --- | --- | --- |
| Complete AI sprite | Trees, foliage, irregular props | Model, then reviewed by a person | Needs anchors and acceptance checks; weak for strict solid joins |
| SVG raster → whole-object AI render | Regular objects needing rich illustration | Model using an exact reference | A reference can drift; a second style image can override proportions |
| SVG faces + generated flat materials | Strict footprints, heights, repeatable variants | SVG and scripts | Face layout, bevels, lighting and distinctive features must be authored |

## Exact template and raster reference

```sh
python tools/svgkit.py template tmp/new-block --height 32 --palette coral
```

This writes editable `template.svg`, `shaded.svg`, their 192×320 PNGs,
`reference-4x.png` (768×1280), four alpha face masks, and `geometry.json`.
The frame anchor is (96,312), top face 128×128, front face 32px high. Elevation
extends upward; near/far width stays 128. The flat raster is for image generation;
the shaded raster supplies deterministic lighting for material compositing.

The current primitive is a block with four studs, not a universal prop generator.
To support a new shape, author its projected silhouette and face masks in code or
SVG. Keep mask coordinates aligned with the frame and contact anchor. Custom
dimensions can use `--width`, `--depth`, `--frame`, and `--anchor`. Enlarge the frame
for extra height instead of allowing clipping. Body edges must align to pixel
boundaries; use an even width with the CLI's integer anchor.

## Whole-object AI detailing

Inspect the raster before referencing it. Use the SVG raster as the sole image
first; describe the desired style in text. Ask for detail inside the existing
silhouette, equal stud sizes, parallel side edges, unchanged top/front division,
true alpha, and no external shadow. See the expanded actual prompts in
`assets/prompts/svg-only-block.json` and `svg-guided-block.json`.

If a style image is necessary, clearly call it material/style only. This remains
a soft constraint. The trial with both images shortened a 160px body to 131px;
the sole-SVG trial matched the opaque body dimensions after uniform normalization.
Neither is guaranteed to preserve exact pixels. Measure the anchor, clean only
observed haze, normalize uniformly, then check coverage, side bands, and silhouette
against the template. Do not stretch axes independently or clip a misprojected
render and claim the camera is fixed. A clipping mask cannot correct internal
stud scaling or misplaced face boundaries.

## Geometry-owned material path

Generate an **opaque, flat, evenly lit material swatch** with no objects, studs,
edges, bevels, floor, text or perspective. Request gentle grain/marks appropriate
at the final 128px width. Save the raw source and expanded prompt. Actual examples
are `assets/source/plastic-material.png`, `wood-material.png`, and matching prompt
JSONs. They were made with built-in imagegen, without API credentials.

```sh
python tools/svgkit.py material tmp/new-block assets/source/plastic-material.png tmp/new-block-material.png --strength .7
python tools/tilekit.py check-solid tmp/new-block-material.png tmp/new-block-check.json --anchor 96 312 --pitch 128 128 --min-alpha 250 --min-coverage 1 --edge-tolerance 1
```

The script subtracts broad lighting from the material, fits the remaining detail
to each face, and blends it into SVG shading. It copies the SVG alpha exactly.
The SVG palette sets the dominant color; the generated swatch supplies grain and
local color variation. Choose the palette explicitly rather than expecting a
swatch to recolor the whole object.
This is AI surface detail with authored geometry and lighting, rather than an AI
redraw forcibly resized into a rectangle. Adjust `--strength` in [0,1] and inspect
the result; material detail can be too quiet or too busy.

Reuse the same material across multiple heights/palettes. The tested heights are
16,32,64,96px; both materials passed exact-alpha, coverage and parallel-edge checks.
That says nothing about continuous wood grain across cells, internal stylistic
quality, or connected terrain. Mixed heights still need visual overlap checks.

## Rebuild and compare saved trials

```sh
python tools/build_experiments.py
npm run dev
```

Open **Workflows**. Compare four paths, toggle the SVG outline, switch the fourth
card's material and height, and inspect the mixed-height scene. The first three
cards have a fixed 32px height target; controls affect only the last card.
`assets/experiment-config.json` records reviewed anchors and normalization.
`docs/workflow-comparison.json` retains coverage, silhouette IoU, body dimensions,
and exact-alpha results. IoU is a silhouette metric, not a measure of overall
image quality. One output per SVG-reference strategy is a useful pilot, not a
statistical reliability estimate. AI calls are not rerun by the build script.
