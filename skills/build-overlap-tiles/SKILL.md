---
name: build-overlap-tiles
description: Generate and process transparent orthographic game tiles with variable sprite heights, stable ground anchors, reproducible crops, and a React overlap preview. Use for tile generation, tilesheet splitting, sprite normalization, atlas packing, anchor correction, or testing overlapping rows in Tile Foundry.
---

# Build overlap tiles

Run commands from the Tile Foundry repository root. Read
[prompt recipes](references/prompts.md) before generating art, and
[geometry and acceptance](references/geometry.md) before changing anchors or frames.
For regular geometry, material variants, or repeatable height families, read
[SVG-led workflows](references/svg-workflows.md) and choose whether the model or
the SVG owns geometry. Do not assume a raster reference locks the result.

1. Separate logical ground cells from art dimensions. Keep the existing `128 × 128`
   cell and `192 × 320` frame unless the user requires a change. Place the ground
   anchor at `(96, 312)`. Let tall art extend upward. Keep the full hidden silhouette.
2. Generate geometry guides with `python tools/tilekit.py guides assets/guides`.
   Supply a guide and an approved style reference to image generation. Generate
   complete isolated transparent objects; do not slice a finished overlapping scene.
   Generate one object per call by default. Save original PNGs and actual prompts.
   Require orthographic parallel projection: equal near/far widths, parallel side
   edges, and equal-sized repeated details. A guide alone does not enforce geometry.
3. Inspect alpha on a contrasting background. Run `crop-alpha` for individual PNGs,
   `split-grid` for a known regular layout, or `split-components` for separated
   silhouettes on transparent sheets. Refer to `python tools/tilekit.py --help`
   and each command's `--help`. Component splitting cannot separate touching art.
4. Remove weak alpha haze only when observed. Use `clean-alpha --min-alpha 32`,
   inspect, and adjust explicitly. Demo sources need 64. Do not guess background
   colors, binarize strong alpha, or remove intentional faint art silently.
5. Normalize uniformly to a common art width with `normalize`. Supply `--anchor-in`
   for a measured ground contact. Never trust the image bounding box as ground
   contact for floating parts, shadows, asymmetry, or wide foliage. Reject clipping
   and enlarge the frame explicitly when required. Preserve returned JSON metadata.
   For solid cells, measure opaque body width rather than counting the antialiased
   fringe or protruding details. The demo block uses 130px full art to obtain a
   128px opaque body. Keep the logical cell at 128px; do not warp perspective art.
6. For the demo, add sources to `assets/source/`, set per-source options in
   `assets/source-config.json`, and run `python tools/build_demo.py`. This builds
   alpha crops, fixed frames, a trimmed atlas, scene presets, guides, validation, and
   editable Tiled `.tmj` maps. Run `python tools/build_experiments.py` for SVG
   references, material variants and comparison metrics. `npm run assets` rebuilds
   both. Generic atlas packing uses `pack MANIFEST OUTPUT`.
7. Open the React playground with `npm run dev`. Inspect Scene, Sprite cuts, Atlas,
   anchor and collision overlays, dense overlap, and PNG versus atlas rendering.
   Inspect Workflows, SVG outlines, live material/height variants, and the mixed
   height material scene when changing the SVG path. Check desktop and mobile.
   Save an actual browser screenshot; never substitute
   a generated mockup for verification. Mark anchors reviewed only after inspection.
   Run `check-solid` for joinable blocks and inspect the Solid block contact preset.
   Free silhouettes such as trees and cottages must not be required to fill a cell.
8. Run `python -m unittest discover -s tests`, `npm run build`, and `npm run verify`.
   Record concrete remaining limitations. Commit originals, prompts, scripts, source
   configuration, normalized outputs, scene files, and screenshot evidence to Git.

Keep ground textures separate from overlapping sprites. Preserve a shared edge band
across floor variants. For continuous raised terrain, implement neighbor-dependent
tops, exposed faces, edges, and corners; independent silhouettes do not solve that.

Do not replace the user's map or publish new changes without authorization. Existing
authorization to build or update this repository covers its ordinary reversible work.
