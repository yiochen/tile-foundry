# 3D capture, then AI reskin

Use this route for objects with defined shapes and especially for directional
characters or skeletal animation. Build or import a model in Blender or Three.js,
apply its skin/materials, rig it, author the motion, and capture a registered pose
sheet. The image model turns the blockout into finished artwork, with shape freedom chosen by subject. A captured pose is a
much richer reference than a stick guide, but image editing can still move feet,
change proportions, reflow panels or invent details. Test the complete reskin.

## Model and capture

Keep the editable model, skin, skeleton, weights, bind pose and animation. Record
an imported asset's origin/license; the bundled procedural adventurer needs no
external asset. It is a runnable reference rig, not a substitute for every subject.
For another object or production character, author/import that actual subject and
use the same registration/capture contract. Do not deliver the generic rig when
the user requested a different design.

The sample capture command covers the two character modes. For a different
subject, author a capture script in the output bundle using the same camera
mapping; retain that script and its model. A static object uses one complete
panel and `assetKind: "object"` in the guide. The fixed-sheet extractor supports
`--kind object`, with the same uniform mapping and clipping checks. Larger bases
need a larger authored frame/cell footprint rather than a smaller model scale;
record occupancy and elevation in the portable output contract.

The bundled Three.js renderer supplies a skinned character, color/materials,
planted dancing poses or eight upright directions, plus separate color, alpha,
depth, neutral-standing and floor-registration passes. Optional Node dependencies
are declared in `scripts/package.json`; existing compatible project dependencies
may be used with `--runtime-root /absolute/path/to/npm-project`.

```sh
npm install --prefix "$SKILL_DIR/scripts"
npm exec --prefix "$SKILL_DIR/scripts" -- playwright install chromium
node "$SKILL_DIR/scripts/render_3d.mjs" dance "$OUTPUT_DIR/render" --scale 2
# For an eight-view neutral turnaround, use directions instead of dance.
```

The output directory must be new. `sheet.png` is the high-resolution floor-free
edit target; `guide.png` shows the same captures on calibration cells. `guide.json`
records the full canvas, exact panel rectangles, runtime frames/anchors and
capture scale. `neutral.png`, `scene.json`, `scene/rig.json`, `scene/poses.json`,
`capture.json`, color frames, masks and depth passes preserve the original setup.
Inspect these before generation, including facing order and the loop boundary.
Paths in `guide.json` are relative to that file. Point submissions at
`render/guide.json` when that is where the capture lives; copying only the guide
to the output root leaves its authored-render references unresolved. Move a
complete capture bundle, or rebase paths before freezing the run.

Leave room for painted edges, hair and clothing detail inside every panel. The
sample dance bends its elbows and leaves about 28px of horizontal clearance in
the 192px frame; its feet, root and model scale stay fixed. For broader motion,
choose a larger fixed frame before capture. Do not let reskin headroom become
per-pose camera fitting or a later crop of generated limbs.

For this projection the required world-to-screen rule is:

```
screenX = anchorX + cellSize * worldX
screenY = anchorY + cellSize * worldZ - cellSize * worldY
```

World Y is height, X/Z are ground, and one ground unit is one cell. The helper
uses a 45-degree orthographic view with an explicit vertical projection stretch
of sqrt(2). This is an anamorphic parallel capture matching the square-grid
illustration convention; an ordinary perspective or isometric camera does not
implement this rule. With a 192×320 frame, 128px cell and anchor (96,248), the
floor corners are (32,184)–(160,312). A vertical 1.25-unit segment projects to
160px. Depth of hair or shoes can legitimately change the apparent silhouette.

Keep camera/view/projection matrices, framing, light, model scale and root fixed
across poses. Rotate the model for directions. Animate joints at phases k/12 for
a twelve-frame, one-second loop; do not duplicate the endpoint as frame twelve.
Store 12 fps timing. Feet may lift intentionally, but their projected ground root
does not move. A seated or floating model retains that root and records separate
support elevation/clearance. Render the floor in an auxiliary pass and hide it
for the color pass. Never normalize individual poses to their alpha bounds.

The direct render has authored geometry and known registration. Raster edge
coverage can vary with render engine, antialiasing and hardware: preserve engine
versions/settings rather than promising identical PNG bytes across platforms.
For opaque full-cell terrain, inspect edge alpha after the actual capture and
sampling path; supersampling can soften an otherwise exact base. Choose
pixel-aligned capture settings before rendering rather than painting over gaps.
Parallel geometry also does not make a material seamless. A stationary edge blend
in an animated shader can become a visible grid band: inspect spatial repeats
at every phase and with offset-phase neighbors, even for untouched 3D renders.

## Reskin the entire sheet

Copy the inspected pose sheet to `references/` and record its exact hash and role
as the edit target. A floor-registration sheet may be a second supplied geometry
reference; identify it separately and explicitly exclude its floor from output.
The bundled game scene is for understanding projection, not an automatic style
reference. Use text for style unless the user requests a supplied style image.

Choose the shape-edit policy before the image call. For characters or hard-to-model
organic subjects, the mesh is a scaffold for pose, nominal scale and contact, not
a finished silhouette. Allow refined anatomy, hair, garments, hands and shoes;
replace visible primitive forms. Preserve joint action, facing, body scale,
ground/support positions and the available frame. Do not freeze crude hair caps,
box boots or capsule anatomy merely because they registered well in an earlier
material-only test. For simple blocks and structures, keep the modeled shape and
base extent, improving surface art, bevels and detail. Mixed scenes need explicit
per-part policies, especially a rigid support with an organic character.

Example for a character sheet:

> Turn this crude 3D pose atlas into a finished hand-painted game adventurer.
> Refine the anatomy and silhouette: shaped hair, expressive face in front views,
> natural hands and boots, and a tailored outfit with readable folds. Replace the
> visible primitive forms. Keep one character design and the reference's nominal
> body scale, facing and joint poses. Make these refinements inside the existing
> head-to-foot scale and panel space; do not enlarge the head, body or shoes to
> add detail. Keep the support/sole centers in place; shoe toes may project forward.
> Rear views show the back of the same design.
>
> Preserve this complete [canvas dimensions], [columns × rows] atlas and its
> [frame count/order]. Keep the camera, panel positions and empty gutters. The
> calibration-floor reference only establishes placement and must not appear in
> the output. Return complete isolated sprites on genuine transparency, without
> labels, ground, cast shadows or rearranged panels.

For a simple structure, replace the design clause with: "Keep the modeled block's
outer shape, square base, wall height and straight edges. Add hand-painted
[materials], bevel shading and small surface detail." An organic prop may need
intermediate freedom: retain the base/support and overall height while refining
its upper silhouette. Name those permissions rather than globally locking contours.

Use the captured dimensions and actual subject in the expanded prompt. Leave
world-unit/export bookkeeping in metadata. Numeric height alone cannot prevent
redrawing at a larger scale. Do not shrink the input or fit the output to
compensate for observed AI enlargement. Compare all candidates at unchanged roots.

Request transparent generation for isolated assets and opaque generation for a
flat floor. Save every untouched source PNG, exact prompt, tool arguments and
reference hashes, including failures. One attempt per planned output; revisions
need a new frozen run. Separate layers/depth pieces require separate planned calls
or a predeclared independently isolated atlas, never flattened-scene subtraction.
For a floor, uniformly downsample the whole opaque square with `floor-material`.
For a static transparent object, author a version-1 `rendered-3d-sheet` guide with
one panel covering the complete capture and `assetKind: "object"` before the call;
use the fixed extractor below. Keep multi-cell footprint and support metadata
from the authored scene when assembling the v2 result.

## Extract without fitting

Use authored rectangles from `guide.json`. Only a uniform scale of the *whole*
source canvas is allowed for tool output resolution. Compute one least-squares
scalar from the guide and source width/height; each actual source dimension must
be within one source pixel of its guide dimension times that same scalar. This
bound is checked on those two residuals, without extrapolating either rounded
axis ratio onto the other axis. Fractional outer edges may use at most
one pixel of recorded transparent virtual padding; source pixels are never cropped
and the original canvas boundary must still be transparent. Never detect/move individual panels,
fit feet, change per-pose scale, stretch axes, apply the 3D alpha silhouette to
the AI art, or clip new hair/clothes to make the result conform.

```sh
python "$SKILL_DIR/scripts/extract_registered_sheet.py" \
  "$OUTPUT_DIR/source-01.png" "$OUTPUT_DIR/render/guide.json" \
  "$OUTPUT_DIR/processed" --kind animation --min-alpha 32
```

Use `--kind directions` for the eight-view sheet. The example explicitly deletes
only source pixels at or below alpha 32/255 globally, matching the low-alpha cleanup of
the floor workflow; record the removed alpha mass and inspect faint details.
Choose this threshold before generation. The default `--min-alpha 0` deletes
nothing and is appropriate for the untouched 3D control. No color key is applied.

The extractor requires transparent space outside the known panels and inside
each panel boundary. It rejects layout drift, joined art, missing panels and
clipping risk rather than inventing registration. On rejection, retain the full
source and diagnostic and report failed delivery; do not recover it by tuning
panel rectangles or thresholds after inspecting the outcome. A source preview is
not a normalized runtime sprite.

The returned v2 `result.json` retains 192×320 frames, root (96,248), per-sprite
`authored-3d-projection` registration and source/guide hashes, with no per-pose
fitting. Keep its relative paths valid when exporting. Fixed metadata establishes
the intended registration, not the generated character's actual contact/height.

## Compare the two stages

Retain the direct 3D frames as a separately labeled control and the AI-reskinned
frames as the candidate. Judge both against the same fixed case definition. Use
independent LLM review at native and 2× scales for projection, design height,
identity, foot contact, complete art, clean alpha and loop continuity. Inspect
all poses at 12 fps and compare the last-to-first transition. Compare the AI
source with the delivered frames to verify that processing did not hide drift.
Compare sheet rows at their stored roots too: within-row consistency can conceal
a row-to-row change in standing height or placement.
Masks/depth/landmarks from 3D are diagnostic references, not a mechanism for
forcing a visual pass. A successful capture does not establish successful reskin.
Direct-render recipes should name the renderer and actual model/material/camera
inputs and record zero image-generation calls. These inputs are authored render
provenance, not claimed images supplied to an AI model. Preserve fresh render
outputs for each control rather than relabeling an older image as a new run.

Every final asset in this workflow must include the imagegen reskin. A failed
reskin stays failed; do not quietly substitute the untouched 3D render. Keep the
render selectable as a separately labeled control. For every delivered independent
layer/piece, record the AI source and the 3D reference it came from. Review both
registration and actual design refinement: a character that merely copies a crude
mesh can preserve geometry while failing the intended visual transformation.

Three.js references: [OrthographicCamera](https://threejs.org/docs/pages/OrthographicCamera.html)
and [SkinnedMesh](https://threejs.org/docs/pages/SkinnedMesh.html).
