# Visible floors and objects on calibration floors

All commands run from the repository root. Python needs the repository's
`requirements.txt`; image generation uses the available built-in tool. Supply the
local SVG **raster** reference, not raw SVG text, to that tool. Inspect the raster
before using it. Save the untouched model PNG and exact expanded prompt.

## Visible floor: “generate a lava tile”

A visible ground tile is artwork, distinct from a disposable calibration floor.
Default to a flat top-down square, 128×128 at runtime, no raised front wall.

```sh
python tools/calibration_guides.py floor tmp/lava/guide
```

Supply `tmp/lava/guide-4x.png` as the sole reference. Example expanded prompt:

> Generate one complete opaque square top-down lava ground material for a colorful
> 2D game. The supplied plain SVG square defines the full canvas coverage only.
> Invent the surface: glowing orange molten channels between dark volcanic crust,
> clear shapes readable at 128px. Fill the entire square to every edge. Aim for
> opposite-edge continuation so repeated tiles look coherent. No cube, front
> wall, perspective tilt, frame, labels, empty margins, or objects on the ground.
> The output is an opaque square material, not an isolated transparent sprite.

Use `transparent_background: false`. Keep raw `source.png` and `generation.json`.
Process the complete material without cropping, filling alpha gaps, or stretching:

```sh
python tools/tilekit.py floor-material tmp/lava/source.png tmp/lava/tile.png
```

`tile.json` stores size/footprint 128×128, center anchor (64,64), original size,
and uniform scale. Non-square sources and transparent gaps are refused. Inspect
an actual 3×3 repeat for edge discontinuities. A full square is geometrically
repeatable; it does not establish continuous lava patterns. If seamlessness is
required, preserve an approved opposite-edge band in later variants, as described
in [prompt recipes](prompts.md). Report visible seams instead of hiding them.

## Object on a tile

The plain green tile is a calibration substrate, not the final ground art. Use
it for scale and center position, then remove it. Keep actual floor layers separate.

```sh
python tools/calibration_guides.py object tmp/player/guide
```

For another pose/object, author the sparse SVG geometry and update its layout JSON;
preserve the floor and panel rectangles. Use a bounding box for broad height
constraints or a stick pose for posture. Do not draw costume details if the model
should invent a design. The supplied box/pose is guidance, not final anatomy.

Example generation instruction:

> Generate a complete original [subject/design brief] on this plain green square.
> The reference is a geometry guide: its square establishes position and scale;
> its stick figure establishes posture. Invent anatomy, clothing, proportions,
> materials, and expressive details. Retain the screen-aligned square's placement
> and dimensions; keep it flat, plain RGB 123,209,75, with no rim or cast shadow.
> Place the character's ground location at the square's center. Shoe toes may
> extend below it; airborne poses keep that same projected ground location below
> their feet. Do not copy the stick strokes into the artwork. Keep the full
> character inside its panel. Outside the square and character is genuine alpha
> transparency. Reserve the green calibration hue for the floor, especially where
> the character overlaps it. No checkerboard paint, labels, borders, or scenery.

Use `transparent_background: true`. Inspect original alpha before processing.

```sh
python tools/tilekit.py process-on-floor tmp/player/source.png tmp/player/guide.json tmp/player/processed --min-alpha 32
```

The command measures the last wide opaque floor band using median side edges
(so an intermittent hand protrusion does not enlarge the floor), checks its aspect, scales
uniformly from its observed width to 128px, and places the observed center at
(96,248) in a full 192×320 frame. It keys only the registered floor region (3px
filter-fringe allowance). The default key has hue tolerance ±28°, an 8° hue
feather, and a saturation transition .02→.12. RGB is never guessed from the image.
Changing `--key-rgb` in guide creation records another explicit saturated color;
processing uses that recorded value. Avoid pale accents in these new guides.

`processed/result.json` stores source panel bounds, observed floor, alpha cleanup,
normalization, and key parameters. Every frame retains size, footprint, and anchor.
Cutout alpha bounds never determine scale or position. Keying is approximate at
opaque mixed edges; changing the character to green may require another key.
A floor warped or substantially occluded by art can defeat this detector; reject
and revise the generation rather than tune feet manually.

## Dancing spritesheet

For a short prompt, use a six-frame dance, three columns by two rows, 8fps.
This is a declared default, not an inferred user requirement; honor specified
frame counts, poses, character references, and timing by authoring a suitable guide.

```sh
python tools/calibration_guides.py dance tmp/dance/guide
```

This authors six different sparse stick poses, one plain calibration square per
192×320 panel, and 32px transparent gutters. The guide canvas is 640×672; its
4× raster and JSON describe the same row-major panel geometry. Use that single
composite image as the reference in **one** generation call for design continuity.

Add these instructions to the object recipe:

> Make a six-frame dancing-player spritesheet, exactly three columns and two rows
> matching the reference's isolated panels. Invent one distinctive player design
> and keep face, outfit, palette, proportions, scale, camera, and lighting
> consistent across all frames. Follow each stick pose with believable dancing
> limbs; show six distinct poses following the guide's arm directions and stance.
> Do not duplicate panels or mirror a pose into the wrong panel. Repeated holds
> are appropriate only when requested.
> Keep one plain green square in every panel. Preserve the reference canvas aspect
> and panel layout. All gutter regions stay genuinely transparent; no character,
> shadow, floor, effects, or text may cross into a neighboring panel. No labels.

For the default six-pose guide, explicitly spell out row-major actions in the
submitted prompt: (1) both elbows bent outward; (2) lean left, left arm raised;
(3) lean right, right arm raised; (4) both hands overhead, wide stance;
(5) right arm raised, left arm low, crossed step; (6) left arm raised, right arm
low, the opposite crossed step. In particular, the final pair must differ in arm
direction and foot crossing. The first forward test repeated that pair despite
the visual guide, so inspect those panels rather than assuming pose compliance.

Inspect the full source for clipped limbs, panel drift, extra/merged frames, and
identity drift. Then process:

```sh
python tools/tilekit.py process-on-floor tmp/dance/source.png tmp/dance/guide.json tmp/dance/processed --min-alpha 32 --fps 8
```

Input aspect may differ by at most 1% due to tool output rounding. Cuts use the
known guide layout scaled to the returned canvas; source cut rectangles are
recorded. Cleaned alpha in a gutter causes rejection. Each panel's observed floor
sets its own scale and anchor. The output includes six full-frame PNGs, a 576×640
sheet without gutters, and `result.json` with row-major order and 125ms duration.
Store the same center anchor for every frame; dancing toes do not change it.

Review playback at this fixed ground point for scale jitter, inconsistent design,
pose progression, and keying damage. A six-frame strip is a pilot animation,
not automatically a smooth or seamless loop. If poses are repeated or wrong,
retain that failure and retry once with clearer per-panel instructions.

If the only layout failure is an isolated fingertip drifting into a planned
gutter, inspect the full source and use explicit safe recovery:

```sh
python tools/tilekit.py process-on-floor tmp/dance/source.png tmp/dance/guide.json tmp/dance/recovered --min-alpha 32 --fps 8 --allow-gutter-drift
```

Recovery finds a completely transparent row/column separator inside each planned
gutter, then partitions the entire cleaned canvas there. It retains every cleaned
source-alpha pixel in exactly one panel and records the actual cuts plus
`panelIsolation: "transparent-separators"`. The floor still determines all anchors
and scales. This does not cut overlapping art, move feet, or discard fingertips.
No transparent separator, a distorted canvas, or output-frame overflow causes
rejection. Do not increase alpha thresholds to erase real limbs. The first
forward retry needed this recovery for raised fingers despite having separate
characters; its strict rejection and recovered result are both retained.

After the single generation retry, report a blocker or generate isolated poses
using the same floor/pose contract and a requested/approved identity reference.
Pack those complete frames into the final sheet. Keep all failures and references;
do not add a style reference merely to emulate old experiments.

## Generation record

A portable generation recipe contains `prompt` (the exact submitted text),
`references` (paths relative to the recipe), `transparentBackground`, `tool`, and
`sourceSHA256` (hash of the unchanged generated source). Preserve each referenced
file, the guide SVG/layout/raster, and all attempts. This records what actually
ran; model version/seed may be unavailable and should not be invented.
