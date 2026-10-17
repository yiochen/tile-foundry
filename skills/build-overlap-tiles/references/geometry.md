# Geometry and portable output contract

Coordinates use a top-left pixel-edge origin. Keep these separate:

- **Logical footprint:** dimensions in ground pixels and explicit occupied cells.
- **Support / collision:** actual ground-contact cells or polygons, authored
  independently of alpha. A floating object can occupy a grid region without
  ground support; an arch's overhead span does not fill its walkable center cell.
- **Art bounds / frame:** full silhouette extent and its storage canvas.
- **Ground anchor:** projected world root expressed in local frame coordinates.
- **Elevation / attachment:** visible height or support offset, never a new pitch.

Single-cell defaults are 128px pitch, frame `[192,320]`, anchor `[96,248]`,
with calibration rectangle `[32,184,160,312]`. A flat floor uses `[128,128]` and
`[64,64]`. A 2×2 footprint is `[256,256]`; 3×2 is `[384,256]`. Enlarge frames
explicitly, retaining the same cell scale. An arch spanning three cells might
occupy `[[0,0],[2,0]]` on the ground and `[[0,0],[1,0],[2,0]]` overhead.

Place sprites at `worldGround - localAnchor`. Atlas trimming changes the local
anchor by subtracting the trim origin; retain the original-frame anchor too.
Never fit anchors to cropped bounds, direction-specific boot tips, or animation
poses. A generic engine export must apply each asset's stored frame/anchor and
support cells. Simple one-root Y sorting cannot establish correct arch or
interlocking multi-cell occlusion; author depth pieces and inspect passage views.

The default projection remains `top-down-oblique-square-grid`. A separately
authored character camera may use `character-orthographic` with finite 4×4
`camera.worldMatrix` and `camera.projectionMatrix`, orthographic type, elevation,
pixel aspect and world units per logical cell. Preserve the camera record in the
processed result. Its ground anchor still places it on the logical grid; never
relabel foreshortened character art as square-grid geometry.

## Output destination

Resolve all generated files under the requested `OUTPUT_DIR`. Paths in a recipe,
manifest, or submission are relative to that file, and must stay inside the asset
bundle. Preserve input/reference copies in `references/`; do not depend on a
source-project directory or absolute local path after export. Do not overwrite
an earlier attempt. The file roles below can be adapted to the target project's
layout; evals use them as a delivery contract.

- `source-*.png`: unchanged generated images, including failed attempts.
- `generation-*.json`: exact expanded prompt, tool, reference roles and paths,
  transparency setting, and source/reference SHA-256 hashes; do not invent unavailable seeds.
- `guide.svg`, raster guide and `guide.json`: authored registration and layout.
- `sprites/`: complete normalized PNGs; separate layers/depth pieces when needed.
- `result.json`: geometry, placement, extraction, frame order and timing.
- `submission.json`: ties the request, source records and result together.
- `previews/`: actual repeated placement, light/dark cutouts, layering and playback.

For machine-readable delivery, use string paths in the canonical records below;
keep any richer tool transcript alongside them. Only rasters actually sent to
the model belong in `references`. An inspected projection reference that was
not supplied is a separate provenance attachment.

```json
{
  "prompt": "Exact text submitted to the image tool",
  "tool": "image_gen.imagegen",
  "transparentBackground": true,
  "sourceSHA256": "SHA-256 of source-01.png",
  "references": ["references/guide.png"],
  "referenceSHA256": {"references/guide.png": "SHA-256 of that input raster"},
  "referenceRoles": {"references/guide.png": "layout edit target"}
}
```

`submission.json` ties those files together. Keep the user's request verbatim
without its file's final newline; this full request need not be the image prompt.

```json
{
  "caseId": "caller-supplied-case-id",
  "outputDirectory": "/absolute/requested/destination",
  "userPrompt": "Exact user request",
  "sources": [{"image": "source-01.png", "recipe": "generation-01.json"}],
  "guide": "guide.json",
  "guideSHA256": "SHA-256 of guide.json",
  "result": "result.json"
}
```

Use `role: "appearance-material"` on a source record for the preselected SVG
material route; that source uses opaque generation. Ordinary assets need no
case ID outside an eval integration. The eval protocol defines its case ID and
destination; never infer or alter those from an output's appearance.

Example result (one partial-base object):

```json
{
  "version": 2,
  "kind": "object",
  "projection": "top-down-oblique-square-grid",
  "cellSize": 128,
  "groundAnchorAlignment": "center",
  "sprites": [{
    "id": "lantern", "image": "sprites/lantern.png", "size": [192,320],
    "anchor": [96,248], "footprint": [128,128], "occupiedCells": [[0,0]],
    "elevationPx": 160, "baseSize": [48,48], "artRect": [72,70,48,186],
    "registration": {"method": "measured-calibration-floor", "guide": "guide.json"}
  }]
}
```

For animation add `fps: 12`, and each sprite's `index` and
`durationMs: 83.33333333333333` in row-major playback order. Directions add a
`direction` per sprite using compass codes `N`, `NE`, `E`, `SE`, `S`, `SW`, `W`,
`NW` in requested order, without animation timing. Full direction names may be
used in the image prompt; serialize these codes in the manifest.
Distinct pose extents are valid;
consistent anatomy scale must be reviewed independently. A GIF's time quantum
cannot represent exact 12 fps; the PNG sheet/frame metadata is authoritative.
Deliver a browser/APNG/WebP preview that can honor this schedule.

For floating art, record `groundClearancePx` separately from `elevationPx`.
For a seated character, record `role: "character"`, the common ground anchor,
`supportElevationPx: 48`, `supportElevationBakedIntoArt: true`, and its local
attachment point. If the pose already includes that elevation, recompose the
stool and character at their common ground anchor without applying it again.
Store the complete stool separately with `role: "stool"`.

For an arch add `supportCells`, `overheadCells`, and `depthPieces` with image,
`size`, `anchor`, unique `id` and integer `drawOrder`. Keep collision/ground occupancy disjoint;
an alpha bounding rectangle is not its footprint.

## Assemble processor outputs

Author `registration.json` before generation. It declares the intended asset
kind, projection, elevation and logical occupancy; visual review must verify them.
For a processed character animation, a minimal registration is:

```json
{
  "kind": "animation", "projection": "top-down-oblique-square-grid",
  "elevationPx": 160, "occupiedCells": [[0,0]]
}
```

After processing, use the measured center-anchor sidecar:

```sh
python "$SKILL_DIR/scripts/assemble_result.py" \
  --input-result "$OUTPUT_DIR/processed/result.json" \
  --registration "$OUTPUT_DIR/registration.json" --output "$OUTPUT_DIR/result.json"
```

For a flat floor, use `kind: "floor"`, `elevationPx: 0` and the `tile.json`
sidecar written by `floor-material`. Multiple `--input-result` arguments combine
independent outputs; optional registration `sprites` entries declare IDs,
directions or layer roles in that same order. They cannot replace measured
image size, anchor, footprint or art bounds. The assembler preserves processing
records, checks actual PNG sizes and requires animation timing already at 12 fps.
It never changes art, fits roots or silently retimes frames.

SVG-based assets and custom multi-cell/layer processing can author `result.json`
directly using the same contract. Convert a recorded near-edge ground point to
the center by subtracting half the footprint depth, without moving the artwork;
retain the original point and conversion. Do not label near-edge metadata as a
center anchor. Keep every referenced image inside the output asset bundle.

## Processing limits

For rendered 3D references, `extract_registered_sheet.py` transfers the authored
layout using one uniform whole-canvas scale. It keeps the recorded ground root
and rejects opaque gutters or frame clipping; it never measures or fits feet.
Each sprite records `registration.method: "authored-3d-projection"` with source
and guide rectangles. Retain editable model/rig/pose/camera sources and separate
floor/mask/depth captures. Read [3D capture and reskin](three-dimensional.md).
This method registers frames; it does not certify an AI reskin's anatomy/contact.

Bundled `tile_tools.py` supports uniform normalization, explicit chroma removal,
known isolated panels, atlas packing, coverage checks and generic validation.
`process-on-floor` measures one visible calibration floor per panel. Its
`floor-width` basis uses width for uniform scale and center for the root;
`square-floor` additionally requires near-square observed aspect. It does not
infer disjoint support, remove an occluded stool, reconstruct hidden parts, or
normalize arbitrary multi-cell floors. Author those registrations/masks/layers
before generation, use an appropriate processor, or report an unsupported case.
Do not force them through the single-cell detector or infer geometry from alpha.

Reject clipping, per-axis stretching, merged panels, perspective drift, unexplained
anchor changes, missing source provenance, and undeclared layer removal. Opaque
full-cell coverage and equal side spans do not prove seamless color/pattern joins.
