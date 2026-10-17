# 3D capture, then AI reskin

Use this route for objects with defined shapes and especially for directional
characters or skeletal animation. Build or import a model in Blender or Three.js,
apply its skin/materials, rig it, author the motion, and capture a registered pose
sheet. The image model then changes the surface art style. A captured pose is a
much richer reference than a stick guide, but image editing can still move feet,
change proportions, reflow panels or invent details. Test the complete reskin.

## Model and capture

Keep the editable model, skin, skeleton, weights, bind pose and animation. Record
an imported asset's origin/license; the bundled procedural adventurer needs no
external asset. It is a runnable reference rig, not a substitute for every subject.
For another object or production character, author/import that actual subject and
use the same registration/capture contract. Do not deliver the generic rig when
the user requested a different design.

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

## Reskin the entire sheet

Copy the inspected pose sheet to `references/` and record its exact hash and role
as the edit target. A floor-registration sheet may be a second supplied geometry
reference; identify it separately and explicitly exclude its floor from output.
The bundled game scene is for understanding projection, not an automatic style
reference. Use text for style unless the user requests a supplied style image.

Keep the current image call scoped to its source, for example:

> Reskin this complete rendered pose sheet into polished hand-painted game
> sprites: rich local color, soft painted highlights and clean readable forms.
> Keep the same character design and outfit in every panel. Paint the existing
> poses in place. Preserve the complete canvas, panel count/order, empty gutters,
> camera, anatomy proportions, head/torso/hand/foot locations and planted contact.
> Preserve each pose's size and position; do not independently center or enlarge
> sprites. Keep the first-to-last sequence cyclic. Return isolated sprites on a
> transparent canvas with no calibration floor, labels, external shadows or new
> scene. The second reference, if supplied, shows ground registration only.

Add the actual canvas dimensions, rows/columns, direction order or frame count,
subject and desired art style. Do not paste unrelated final export instructions
into the image prompt. Request transparent generation. Save the untouched source
PNG and exact expanded prompt, tool arguments and reference hashes, including
failed output. One generation per frozen eval attempt; a revision is a new run.

## Extract without fitting

Use authored rectangles from `guide.json`. Only a uniform scale of the *whole*
source canvas is allowed for tool output resolution; integer dimensions can have
at most one pixel of whole-canvas rounding. Never detect/move individual panels,
fit feet, change per-pose scale, stretch axes, apply the 3D alpha silhouette to
the AI art, or clip new hair/clothes to make the result conform.

```sh
python "$SKILL_DIR/scripts/extract_registered_sheet.py" \
  "$OUTPUT_DIR/source-01.png" "$OUTPUT_DIR/render/guide.json" \
  "$OUTPUT_DIR/processed" --kind animation --min-alpha 32
```

Use `--kind directions` for the eight-view sheet. The example explicitly deletes
only source pixels below alpha 32/255 globally, matching the low-alpha cleanup of
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
Masks/depth/landmarks from 3D are diagnostic references, not a mechanism for
forcing a visual pass. A successful capture does not establish successful reskin.

For exact geometry with no image-redraw risk, keep the final output as a 3D
render and put the desired appearance on model materials/UV textures before
capture. This is a separate route; label it accurately when evaluating it.

Three.js references: [OrthographicCamera](https://threejs.org/docs/pages/OrthographicCamera.html)
and [SkinnedMesh](https://threejs.org/docs/pages/SkinnedMesh.html).
