# Dancing player retry

This fresh retry used the updated six-action recipe and the sole authored SVG raster guide. The source now has opposite raised-arm directions and opposite crossed steps in the final pair.

Processing failed at the unchanged default:
```text
Error: Art crosses a sheet gutter; regenerate isolated panels instead of clipping
```

The final two panels' raised fingertips extend up to 8 source pixels into the horizontal row gutter. There are 285 off-panel pixels with alpha >=32, including fully opaque pixels (maximum 255), in bounds [683,665,959,673]. The bottom-row source panels begin at y=673. Slicing the sheet would clip those fingers, so no accepted frames, normalized spritesheet or animation result were produced. No threshold or geometry adjustment was made.

Artifacts:
- `source.png`: untouched generated PNG.
- `generation.json`: exact submitted prompt, sole relative reference, transparency setting, tool and source SHA256.
- `source.sha256`: hash of the untouched source.
- `guide.svg`, `guide.png`, `guide-4x.png`, `guide.json`: authored guide geometry/raster/layout.
- `processing-failure.json`: processing error, exact panel rectangles and pixel diagnosis.
- `processing.log`: processing command and error.
- `diagnostics/source-light.png`, `diagnostics/source-dark.png`: source composited over inspection backgrounds.
- `diagnostics/gutter-violation.png`: magenta marks the actual offending pixels; purple lines mark declared panel bounds. This is a diagnostic only, not an edited asset.

Run from the repository root:
```sh
.venv/bin/python tools/tilekit.py process-on-floor /tmp/tile-foundry-dance-retry-lg3b0f1_/source.png /tmp/tile-foundry-dance-retry-lg3b0f1_/guide.json /tmp/tile-foundry-dance-retry-lg3b0f1_/processed --min-alpha 32 --fps 8
```

Two fresh generations total were made across the original attempt and this retry. The first attempt remains intact in /tmp/tile-foundry-dance-0o6fquib and has a repeated final arm direction. This retry corrected the pose pair but introduced the gutter intrusion. The authorized retry is exhausted. No repository files were changed.
