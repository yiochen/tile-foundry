# Findings from real workflow trials

The initial pass generated four complete objects independently using the supplied
style reference: crate, toy brick, tree, and cottage. It then cleaned alpha,
cropped, normalized, packed, assembled, exported, and verified the scene in an
actual Chromium browser. Geometry guides are included for subsequent generations;
the initial four calls used the style reference rather than those guides.

## What mattered

1. **Generated transparency still needed inspection.** All four outputs had RGBA
   channels, but faint alpha haze and stray pixels enlarged naive bounding boxes.
   A configurable alpha floor of 64/255 worked for this specific batch. Keep the
   original files and compare at final size; that threshold is not universal.
2. **Original canvas sizes were inconsistent.** The source tree was 1024×1536;
   other objects had different dimensions. Crop the complete silhouette first and
   scale its visible width consistently. Do not scale to each canvas's height.
3. **Tall sprites need headroom.** The tree's art is 128×253 after normalization.
   A 128×128 cut would destroy it. We chose 192×320 fixed frames, leaving room for
   overhang and antialiasing while retaining a 128px square logical cell.
4. **Anchor coordinates need to survive every stage.** Explicit source ground
   contacts are stored in `assets/source-config.json`. Fractional resampling can
   otherwise yield slightly different frame anchors; normalization applies a small
   recorded subpixel translation so every final ground anchor is exactly (96,312).
5. **Trimmed atlas frames need their own anchor.** Packing removes transparent
   margins, then subtracts the trim origin from the anchor. Unit tests reconstruct
   every RGBA pixel of processed sprites, including weak antialias texels.
6. **Draw order must depend on ground contact.** Both browser and Tiled exports
   draw back rows before front rows. Consecutive trees in the village and a dense
   stress scene make occlusion visible. Insertion order does not control depth.
7. **Shared ground boundaries are easier to control deterministically.** The three
   floor variants preserve the full 8px edge band. All band pixels are checked,
   while small grass details vary inside it. Floor and object art remain separate.
8. **Prompt instructions need a concrete file contract.** An independent agent
   followed the packaged skill and reproduced cuts and an atlas. It initially had
   to infer the pack-manifest schema from repository examples; the skill reference
   now includes a minimal schema and image-path rules.
9. **Width-only normalization did not make solid cells join.** The initial block
   was 128×112 overall, leaving grass between 128px-spaced rows. Its opaque width
   also tapered from 122px in the far band to 126px in the near band. The original
   alpha/anchor/atlas tests did not catch either failure. `check-solid` now repeats
   a sprite in a 3×3 neighborhood, checks the central cell for coverage, and compares
   near/far opaque side spans. This check applies to joinable solid cells, not trees.
10. **Orthographic geometry needs explicit acceptance.** A first correction still
    widened toward the camera. A second call made the geometry guide primary and
    required equal near/far widths and stud sizes. `block-v2.png` is the accepted
    source; `block.png` is retained. Scaling the antialiased outer silhouette to
    128px still gave a 126px opaque body. A uniform scale to 130px full art produces
    128px opaque near/far widths and zero uncovered pixels in the repeated central
    128×128 cell at alpha ≥250. This is a measured two-pixel fringe allowance, not
    a perspective warp or a universal two-pixel fix.

## SVG-first experiments

We authored the same block as an SVG: exact 128×128 rectangular top, 32px front
wall, four identically sized studs, and a fixed (96,312) ground anchor. CairoSVG
rasterizes it into a transparent 192×320 sprite and a 768×1280 AI reference.
SVG face masks and geometry metadata are exported alongside it. Only this block
primitive is implemented so far; general props need their own authored geometry.

Four new built-in imagegen calls produced two whole-object renders and two flat
material swatches. Actual expanded prompts, inputs and untouched outputs are
checked in. Uniform AI normalization uses the reviewed options in
`assets/experiment-config.json`; the new AI sprites use 130px art width to include
their observed antialias fringe. None is warped or silhouette-clipped.

| Path | Opaque body height / 160px target | Far / near width | Missing cell pixels | Silhouette IoU |
| --- | --- | --- | --- | --- |
| Original free sprite | 110px | 122 / 126px | 2,830 | 66.2% |
| SVG + polished style reference | 131px | 128 / 128px | 0 | 81.8% |
| SVG as sole image reference | 160px | 128 / 128px | 0 | 98.8% |
| SVG + generated material | 160px | 128 / 128px | 0 | 100% |

The style image competed with the geometric reference: the first SVG trial kept
straight sides but shortened the depth toward the style image. Removing the second
image gave much closer geometry. This does not prove that a style reference always
hurts or that sole-reference rendering always succeeds. Each strategy has one
recorded output. Pixel dimensions alone also miss altered face boundaries and
stud details; inspection remains necessary.

The material path generates an opaque flat swatch rather than an object. The
script removes broad swatch lighting and composites the remaining surface detail
inside SVG face masks over authored SVG shading. It copies alpha exactly. The SVG
palette owns dominant color; swatches supply grain and local variation. Coral
plastic and honey wood each produce elevations 16,32,64,96px from one swatch.
All eight variants have exact SVG alpha, zero uncovered central-cell pixels, and
parallel sides. Tests inspect every opaque body row, not only sample bands.
The browser shows the mixed heights overlapping back rows on the same 128px grid.

For strict repeatable solid geometry, prefer SVG-owned faces and generated
materials. For rich free silhouettes or distinctive illustration, use whole-object
AI art with review. SVG-guided redraw is a useful middle path. A final silhouette
clip is another possible experiment, but cannot fix perspective inside an object;
it was not used to make these results pass. Other worthwhile future trials are
per-face AI detail layers, high-resolution painted templates with protected joins,
and 3D orthographic render guides for more complex objects.

The current material path has authored stud lighting and bevel lines, simpler
than the whole-object AI illustration. Material grain is mapped independently
to faces and repeats between blocks; it is not a seamless surface texture proof.
Mixed-height stacked sprites remain independent props, not an adjacency-aware
elevated terrain mesh. Metrics measure silhouette/opacity, not style quality.

## Verification

- 24 Python tests cover anchor preservation, clipping refusal, fractional anchors,
  alpha cleanup, both sheet-cutting methods, atlas reconstruction/extrusion, and
  Tiled placement math, undersized solid bodies, perspective taper, alpha-threshold
  forwarding, exact SVG coverage at four heights, face partitions, and material
  alpha invariance even under extreme detail input, and rejection of unaligned SVG edges.
- The React production build succeeds. Fonts are bundled locally.
- Browser verification exercises PNG/atlas parity, all four views, overlays, cell
  placement and undo, JSON imports and downloads, PNG export, and 390/320px layouts.
  `browser-verification.json` records the actual results.
- Workflow verification checks all four cards, live wood/96px controls, SVG outline,
  mixed-height PNG export, and 390/320px workflow layouts. `preview-workflows.png`
  and `preview-material-scene.png` are actual browser screenshots.
- An independent agent followed the packaged SVG recipe for a 64px amber/wood
  block. All 11 template and material files were byte-identical across three runs,
  including the latest script revision. Exact alpha, zero missing pixels, and
  128/128px side spans passed. This replay uses saved AI input, not repeated AI calls.
- `preview-desktop.png`, `preview-mobile.png`, `preview-scene.png`,
  `preview-guides.png`, `preview-cuts.png`, `preview-atlas.png`, and
  `preview-stress.png` are actual browser screenshots, not generated UI mockups.
- Tiled files are checked against the documented JSON structure, image references,
  and anchor-offset math. A native Tiled editor was not available for visual QA.
- `solid-block-before.json` measured 2,830 uncovered pixels out of 16,384 (17.27%).
  `solid-block-after.json` measured zero, with equal 128px far/near widths.
  `preview-contact.png` is an actual browser screenshot of 54 adjacent corrected
  blocks. Shared color/texture continuity, mixed-height joins, and screen-space
  filtering still require scene inspection; the alpha check does not prove them.

## Next useful extensions

Add explicit source-footprint measurements for overhanging foliage, a manual
anchor-placement tool for imported PNGs, and saved per-material prompt variants.
For connected elevated terrain, add a height grid with neighbor-dependent exposed
faces, boundary/corner art, and interior-outline removal. This first demo uses
independent objects; overlapping them does not guarantee continuous rock surfaces.

## Data sources

Tiled map and tileset formats: <https://doc.mapeditor.org/en/stable/reference/json-map-format/>
and <https://doc.mapeditor.org/en/stable/manual/editing-tilesets/>.
Sample object generation prompts are retained in `assets/prompts/generation.json`.
The user-supplied reference image is not included in the repository.
