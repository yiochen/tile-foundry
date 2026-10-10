# Tile Foundry

A reproducible image-generation → tile-processing → React-preview workflow for
square-grid, three-quarter-view game art. Full sprites have different heights and
overlap rows behind them; their logical cells stay the same size.

![Village lane preview](docs/preview-scene.png)

## Start

Requires Python 3.10+ and Node.js 20.19+ or 22.12+.

```sh
python -m pip install -r requirements.txt
npm ci
python tools/build_demo.py
npm run dev
```

Open the address printed by Vite. For remote/mobile use, forward that port through
your normal remote-development setup. The playground adapts to a phone screen.
The generated assets and assembled demo are checked in, so no image API key is
required to run or rebuild the demo.

## What's here

| Path | Purpose |
| --- | --- |
| `tools/tilekit.py` | CLI for guides, alpha cleanup/crops, grid/component splitting, normalization, atlas packing, validation, Tiled export |
| `tools/build_demo.py` | Rebuild all derived demo assets from the original generated PNGs |
| `src/` | React scene editor and cuts/atlas preview |
| `assets/source/` | Original AI-generated transparent images, untouched |
| `assets/source-config.json` | Reviewed cleanup, art-width, and optional source-anchor settings |
| `assets/prompts/generation.json` | Actual prompts used for the initial four assets |
| `skills/build-overlap-tiles/` | Agent skill with reusable prompts and acceptance checks |
| `public/assets/village.tmj` | Editable Tiled village map with image-collection object tiles |
| `public/assets/stress.tmj` | Dense overlap test map |
| `docs/` | Browser screenshots and workflow findings |

## Useful commands

```sh
# Geometry guides for low, medium, and tall art
python tools/tilekit.py guides assets/guides

# Remove observed weak-alpha haze, then crop the complete silhouette
python tools/tilekit.py clean-alpha assets/source/tree.png tmp/tree-clean.png --min-alpha 64
python tools/tilekit.py crop-alpha tmp/tree-clean.png tmp/tree-crop.png --padding 4

# Split a regular sheet; never use cell-sized cuts on a flattened overlapping scene
python tools/tilekit.py split-grid public/assets/sheet.png tmp/grid-cuts --cell 192 320 --columns 2 --rows 2 --spacing 24

# Find separate silhouettes on a transparent sheet
python tools/tilekit.py split-components public/assets/sheet.png tmp/component-cuts --min-area 100

# Uniform scale, full tall frame, fixed ground anchor
python tools/tilekit.py normalize tmp/tree-clean.png tmp/tree-normal.png --frame 192 320 --anchor-out 96 312 --art-width 128

# Atlas trimming updates each ground anchor; gutters extrude edge pixels
python tools/tilekit.py pack public/assets/tiles.json tmp/atlas.png --padding 4 --extrusion 2
python tools/tilekit.py validate public/assets/tiles.json

# Export a saved playground scene to editable Tiled format
python tools/tilekit.py export-tiled public/assets/village.json public/assets/tiles.json public/assets/village.tmj
```

Every image-processing command retains useful JSON metadata. Use `--help` on a
subcommand for input options. Output paths are explicit; originals are not replaced.

## Playground

- Scene / Sprite cuts / Atlas views; village and dense overlap presets.
- Grid, ground anchors, and authored collision overlays.
- Compare trimmed-atlas rendering with individual PNG rendering.
- Inspect, place, and erase by logical cell; undo up to 30 edits.
- Import/export scene JSON and export the actual preview PNG.
- Separate logical footprint, visible-art bounds, and drawing anchor in the inspector.

## Add another asset

Generate a complete isolated PNG using the repo skill. Keep the source and its
actual prompt. Add its source configuration and demo registration in
`tools/build_demo.py`, then rebuild. For a standalone PNG, use the generic CLI
without changing the demo. If the visible silhouette's bottom is not its ground
contact, explicitly supply source anchor coordinates; never guess from image size.

To use the skill with a coding agent, point it at
`skills/build-overlap-tiles/SKILL.md`; copy that folder into your agent's skill
directory if its discovery system requires installation. The skill is packaged
in this repo and does not change your account-level skills automatically.

## Verify

```sh
python -m unittest discover -s tests
python tools/build_demo.py
npm run build
npx playwright install chromium
npm run verify
```

The browser check starts a temporary local Vite server, tests desktop/mobile,
cell editing and undo, scene import/export, all preview modes, renderer parity,
and captures real screenshots in `docs/`. Set `CHROMIUM_EXECUTABLE` to use an
existing Chromium binary. No external page or login is used for this check.

The current demo covers independent one-cell objects. Connected raised terrain,
complex bridges, and multi-cell depth interactions need authored adjacency/depth
rules. See [workflow findings](docs/workflow-findings.md).

The supplied style reference is not redistributed. The four sample objects were
generated with the built-in image-generation tool; their source files and exact
prompts are retained. Floor tiles are deterministic procedural assets with a shared
boundary band. The code is MIT-licensed.
