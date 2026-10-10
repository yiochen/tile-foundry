# Tile Foundry

Keep logical footprints, art bounds, and anchors separate. Heights are visual art,
not a reason to scale the whole sprite or change the grid pitch.

Use `tools/tilekit.py` for deterministic image processing; use image generation for
new artwork. Preserve source PNGs and their prompts. Never silently clip a sprite,
remove a background by color guessing, or slice a flattened overlapping scene.

Run `python -m unittest discover -s tests`, `python tools/build_demo.py`,
`npm run build`, and `npm run verify` after relevant changes. Inspect the actual
screenshots, including mobile. Keep the browser renderer and Tiled export aligned
with the stored ground anchor. Do not claim an AI output is geometrically exact.

Repo skill: `skills/build-overlap-tiles/SKILL.md`. Keep its commands runnable from
the repository root. Update documented defaults when the manifest schema changes.
