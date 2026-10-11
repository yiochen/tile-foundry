# Lava tile

Fresh built-in image generation using the sole authored square raster reference.
The source PNG is copied byte-for-byte and its SHA256 is in `generation.json`.
The recipe reference paths are relative to the recipe for portability.

- `source.png`: untouched generated 1254x1254 RGB source.
- `generation.json`: exact submitted prompt, reference, tool, transparency setting, and source SHA256.
- `guide.svg`, `guide.png`, `guide-4x.png`, `guide.json`: authored square reference and layout.
- `tile.png`, `tile.json`: complete opaque 128x128 runtime material with center anchor (64,64).
- `repeat-3x3.png`, `repeat-3x3-zoom.png`: actual repeat review and nearest-neighbor zoom.
- `review.json`: processing checks and visual inspection notes.

## Reprocess

From the Tile Foundry repository root, substitute the output directory below if moved:

```sh
.venv/bin/python tools/tilekit.py floor-material /tmp/tile-foundry-lava-L6CJpQXW/source.png /tmp/tile-foundry-lava-L6CJpQXW/tile.png
```

The tile was processed with uniform whole-image resampling, no cropping,
no alpha filling, and no color key. One generation attempt succeeded; there
were no failed attempts or retries.

The 3x3 repeat is coherent overall, but small channel mismatches at some joins
and a noticeable repeating motif remain. AI output is not certified exact or
seamless. No repository integration changes were made, so build/browser/Tiled
checks for integrated assets were not run.
