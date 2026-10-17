# Blender dancing adventurer experiment

Blender 5.2.2 LTS and the third-party `mcp-for-blender` 2.1.9 bridge are installed.
The live addon reported protocol 13. A stdio MCP client successfully called
`get_scene_info`, `execute_blender_code` and `look` against localhost:9876.
Codex's global `blender` MCP entry uses the pinned package and disables bridge
telemetry. An already-open Codex session may need a new session to discover the
new tool menu; this experiment used the actual MCP protocol directly.

The current editable source is
[`dancing-adventurer-v2/dancing-adventurer.blend`](../assets/blender/dancing-adventurer-v2/dancing-adventurer.blend).
The playground's **Blender** tab contains 12 fps playback, scrubbing, an optional
orbitable GLB, before/after MCP captures, camera comparison, prompt and sources.

## Authored model and capture

- Procedurally authored chibi adventurer: shaped face, eye/iris/pupil layers,
  brows, nose, ears, layered hair locks, tailored blue tunic, ivory trim, belt,
  brass buckle, pouches, modeled fingers/thumbs and shaped leather boots.
- 131 mesh objects, 31,697 base vertices, a 22-bone armature, continuous weighted
  elbow/knee and shoulder meshes, native procedural material grain and lighting.
- A planted two-second dance: 24 unique poses at 12 fps. The matching closing key
  is frame 25; it is omitted from the sprites and included at t=2s in the GLB.
- Cycles, 32 samples with denoising, 768×1280 transparent captures. Complete
  frames are uniformly sampled to 192×320; no pose bounds fitting or cropping.
- The logical footprint remains 128×128, root (96,248). A 35° ordinary
  orthographic character camera avoids the grid profile's vertical elongation.
  Its physical floor is foreshortened. The comparison capture uses a 45° camera
  plus √2 vertical projection stretch at the same world scale. Camera matrices,
  pixel aspect and world units per logical cell are recorded explicitly.

This is an editable stylized prototype, not a production sculpt or a facial rig.
The GLB uses base materials and glTF linear skinning; native procedural materials
and volume-preserving deformation are authoritative in the `.blend` and captures.

## Arm correction and validation

The first rig's -90° arm IK pole angle pulled elbows inward across the chest.
Correct wrist target positions and stable feet did not catch that anatomical
error. Initial render inspection missed it. After the user's feedback, MCP
`look(mode="angles")` captured front, right and three-quarter views; these made
the fold unambiguous.

The corrected rig uses outward elbow poles, wrist rotations aligned with the
evaluated forearm direction, continuous weighted elbow/knee/shoulder surfaces and
volume-preserving skinning. MCP multi-angle and six-pose animation captures were
inspected after correction and retained in `v2/validation`. The original capture
is retained in `v1/validation`.

The complete 24-frame rig audit reports no unweighted vertices or invalid weight
sums, outward elbows throughout the loop, zero wrist bend relative to forearms,
identical foot transforms, and a matching closing pose. Maximum hand IK goal error
is 0.000087 world units (about 0.006 runtime pixels). The projected root differs
from the declared pixel location by under 0.0002px due to numerical arithmetic.
All captured frames retain clear transparent boundaries. These checks verify
this authored control; they do not certify an AI reskin.

## Three imagegen calls, all retained

1. `v1/source-01.png`: a 24-pose style-only atlas edit. Painted surfaces improved,
   but characters enlarged and rows shifted. Opaque art crossed authored gutters,
   so fixed-layout extraction rejected it. No runtime animation was exported.
2. `v1/source-02.png`: a single-frame paint-over of the earlier rig, queued before
   the arm repair. Whole-frame extraction succeeded. It remains a before example,
   not artwork for the corrected rig.
3. `v2/source-01.png`: a fresh single-frame surface/style edit of the corrected
   pose. Whole-frame extraction succeeded. Placement looks much closer to the
   source than the atlas trial; small silhouette and material-edge changes remain.
   This is a static proof, not evidence of temporal consistency across a reskinned
   animation.

Every call's original PNG, exact prompt, supplied reference role/hash and source
hash are retained. Processing uses one whole-canvas scale and the declared global
32/255 alpha threshold. No per-pose scale, foot fitting, renderer silhouette mask,
color guessing or clipping is applied. Successful extraction is not an eval pass.
The existing 14-case eval grades are unchanged; this was a focused character test.

Repository verification passed: 145 unit tests, asset generation, production
build, and browser checks including 24-frame scrubbing/looping, GLB loading and
390px/320px layouts. Actual desktop, mobile and 3D-view screenshots were inspected.
All 6,320 PNGs under source/public assets passed CRC and full decoding checks.

## Reproduce from the repository root

Use a new output directory to retain earlier attempts:

```sh
blender -b --python tools/blender/build_adventurer.py -- --output /absolute/new-output
blender -b /absolute/new-output/dancing-adventurer.blend --python tools/blender/validate_adventurer.py -- /absolute/new-output
blender -b /absolute/new-output/dancing-adventurer.blend --python tools/blender/capture_adventurer.py -- /absolute/new-output
blender -b /absolute/new-output/dancing-adventurer.blend --python tools/blender/export_adventurer.py -- /absolute/new-output
python tools/blender/package_adventurer.py /absolute/new-output
```

The packaging command uses the project's shared tilekit and strict registered
extractor. It intentionally requires a new `control` destination. The modeling
and capture script snapshots are also stored with both source bundles.

For a comparable macOS MCP installation:

```sh
brew install --cask blender
uvx --python 3.11 --from mcp-for-blender==2.1.9 mcp-for-blender install-addon --addons-dir "$HOME/Library/Application Support/Blender/5.2/scripts/addons"
codex mcp add blender --env BLENDER_HOST=127.0.0.1 --env BLENDER_PORT=9876 --env DISABLE_TELEMETRY=true -- uvx --python 3.11 --from mcp-for-blender==2.1.9 mcp-for-blender
```

Enable `blender_mcp` in Blender preferences and save preferences. The addon starts
the localhost bridge when Blender opens. The setup used here was verified through
MCP, including image results from the viewport, rather than configuration alone.
