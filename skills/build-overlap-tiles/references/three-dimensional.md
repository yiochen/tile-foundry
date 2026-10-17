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

For scale-sensitive work, scope the call to **materials and lighting on existing
geometry**. A request for a polished new character can encourage larger hair,
different boots or fuller clothing even when the same prompt says to preserve
scale. A surface finish can be visibly painted while retaining the model's simple
forms; it will not turn a rough blockout into a new detailed character design.
Develop the intended anatomy/outfit in 3D first when that redesign is required.

Use this prompt shape, replacing the subject-specific examples with actual
features visible in the supplied render:

> Apply a hand-painted [desired medium] material finish to this exact rendered
> atlas. Edit the existing surfaces, keeping the character geometry unchanged.
> Preserve [specific hair contour, rounded/boxy body shapes, limb thickness,
> shoe shape, outfit and proportions]. Paint color and shading inside those
> existing shapes, with [desired palette/materials] and the same light direction.
> Keep the original face visibility in every view; a back view stays a back view.
>
> The input is the registered artwork. Keep its outside contours, body height,
> head crowns, sole positions, joints, panel positions and transparent space.
> Preserve every existing margin and gap. Retain all [count/order of views or
> poses], the complete canvas and empty gutters. Return the same atlas with
> its surface finish changed, on genuine transparency, without added parts,
> external shadows, floor, labels or rearrangement.

Keep the distinction concrete. For a model with a smooth hair cap and long boxy
boots, name those shapes rather than requesting a new hairstyle or realistic
leather footwear. Adding facial detail everywhere can turn a rear view into a
front view. A broad "same character" clause is less useful than naming which
existing shapes and visibility must survive. Do not rely on numeric height
instructions alone, or compensate by shrinking the 3D input to offset past AI
enlargement. Keep the same reference while comparing prompt revisions.

Add the actual canvas dimensions, rows/columns, direction order or frame count,
subject and desired art style. Do not paste unrelated final export instructions
into the image prompt. Request transparent generation. Save the untouched source
PNG and exact expanded prompt, tool arguments and reference hashes, including
failed output. One generation per frozen eval attempt; a revision is a new run.
Keep a surface-edit prompt close to the compact example above (roughly 150–200
words is a useful starting point). Name a few shape anchors instead of expanding
every joint and material into a new design brief. Leave world-unit heights,
runtime frame/anchor coordinates, capture-scale conversions and export commands
in the retained 3D manifest. They describe how the input was rendered, not what
the image tool should redraw. A shorter prompt is not a guarantee of fidelity;
check the actual source rather than assuming more constraints ensure adherence.
Once a candidate works, test the resulting skill with a fresh executor that has
only the realistic request, skill and required inputs. Keep style strength and
geometry fidelity visible as separate outcomes; a weak surface change should not
be presented as evidence that unrestricted character redesign preserves scale.

## Extract without fitting

Use authored rectangles from `guide.json`. Only a uniform scale of the *whole*
source canvas is allowed for tool output resolution; integer dimensions can have
at most one pixel of whole-canvas rounding. Fractional outer edges may use at most
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

For exact geometry with no image-redraw risk, keep the final output as a 3D
render and put the desired appearance on model materials/UV textures before
capture. This is a separate route; label it accurately when evaluating it.

Three.js references: [OrthographicCamera](https://threejs.org/docs/pages/OrthographicCamera.html)
and [SkinnedMesh](https://threejs.org/docs/pages/SkinnedMesh.html).
