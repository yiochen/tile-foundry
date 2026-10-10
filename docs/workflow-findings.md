# Findings from the first real pass

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

## Verification

- 14 Python tests cover anchor preservation, clipping refusal, fractional anchors,
  alpha cleanup, both sheet-cutting methods, atlas reconstruction/extrusion, and
  Tiled placement math.
- The React production build succeeds. Fonts are bundled locally.
- Browser verification exercises PNG/atlas parity, all three views, overlays, cell
  placement and undo, JSON imports and downloads, PNG export, and 390/320px layouts.
  `browser-verification.json` records the actual results.
- `preview-desktop.png`, `preview-mobile.png`, `preview-scene.png`,
  `preview-guides.png`, `preview-cuts.png`, `preview-atlas.png`, and
  `preview-stress.png` are actual browser screenshots, not generated UI mockups.
- Tiled files are checked against the documented JSON structure, image references,
  and anchor-offset math. A native Tiled editor was not available for visual QA.

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
