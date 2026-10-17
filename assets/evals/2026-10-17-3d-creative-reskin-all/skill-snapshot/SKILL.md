---
name: build-overlap-tiles
description: Generate square-grid game floors, objects, characters, and animation sheets using projected 3D blockouts and subject-aware AI reskinning, with reusable ground anchors, independent footprints, and 12 fps animation.
---

# Build overlap tiles

Use this skill in any target project. Resolve `SKILL_DIR` to the directory
containing this file and `OUTPUT_DIR` to the user-requested asset destination.
Keep outputs there; do not assume a repository layout, engine, playground, or API
credentials. Bundled commands work from any current directory:

```sh
python -m pip install -r "$SKILL_DIR/scripts/requirements.txt"
python "$SKILL_DIR/scripts/guide_tools.py" object "$OUTPUT_DIR/guide"
```

Generate new artwork with the available image-generation tool. Use bundled scripts
for deterministic processing. Retain original generated images, exact expanded
prompts, references, SVGs, raster guides, and processing metadata.

## Target projection

Use **top-down oblique projection, square-grid, front-facing three-quarter game
view**. Ground cells remain screen-aligned squares; object tops and fronts are
visible, parallel edges retain their direction, and height projects upward over
the row behind. This is an illustrated parallel-projection convention; “3/4” does
not specify a physical camera angle. Read [projection](references/projection.md)
and inspect the bundled reference when choosing a guide. Record the projection
profile with the result, and use it consistently across poses and frames.

## Capture geometry, then reskin every final asset

Use **3D blockout → registered capture → imagegen reskin** for floors, objects,
characters, multi-cell structures, separated layers, directions and animations.
The untouched render is a geometry reference/control; it is not the final artwork.
Apply the image-generation pass to every delivered asset, including simple blocks
and every separately authored layer or depth piece. Read
[3D capture and reskin](references/three-dimensional.md).

Choose the shape freedom by what the model already accomplishes:

- **Characters and difficult organic forms:** treat the crude mesh as pose, scale
  and support guidance. Redesign its local silhouette, anatomy, face, hair, hands,
  footwear and clothing into finished artwork. Replace primitive-looking shapes;
  do not ask to preserve every contour or restrict the call to painting materials.
  Keep nominal body scale, facing, joint action and support contacts consistent
  across views. Hair and fabric can change edges within the authored frame.
- **Blocks, floors and simple modeled structures:** preserve their useful outer
  geometry, base extents, height and straight alignment. Improve materials,
  shading, bevels and small details without unnecessary shape redesign.
- **Mixed subjects:** state these freedoms per part. For example, retain a stool's
  modeled seat/support geometry while refining the seated character's silhouette.

For both, keep the same camera, logical footprint, ground root, support elevation,
attachment points and complete panel layout. Shape freedom does not authorize a
larger character, a moved foot anchor, a rotated ground base or a resized frame.
Declare usable clearance before capture, rather than fitting or clipping the
result later. Judge creative refinement and registration separately.

Capture floor-free object/pose sheets as edit targets and calibration floors as
auxiliary references. A flat visible floor is an opaque square plane and remains
opaque after reskinning; use the whole-square processing command in
[floor and object workflow](references/floor-and-objects.md). Raised terrain keeps
its full base and explicit front-wall height. Inspect spatial repeats through
all animation phases, including offset phases. Use [material animation](references/material-animation.md)
for optional motion authoring, then reskin the captured phase sheet as well.
All animations use **12 fps** (`1000/12` ms per frame).

For large objects, arches or stacked layers, declare footprints, support/overhead
cells, attachment elevations and depth pieces before generation. Capture and
reskin each complete independent layer/piece. Derive a whole-object preview by
compositing those pieces at stored roots; never slice a flattened overlapping
scene. Read [geometry and output contract](references/geometry.md).

Describe style in text by default. An identity/support image may be supplied when
continuity or attachment needs it; record its role. The bundled scene illustrates
projection and is not a default style image. Inspect every input raster.

[Sparse SVG workflows](references/svg-workflows.md) remain useful for historical
comparisons or explicitly requested alternatives. They do not replace the 3D plus
imagegen final-art pass in this workflow. Read [prompt clauses](references/prompts.md)
to keep source-generation instructions separate from final export instructions.

## Anchors and extraction

Defaults: 128px ground cell; flat floor 128×128 with center anchor (64,64);
single-cell object 192×320 with projected ground-center anchor (96,248) and
calibration floor `(32,184)–(160,312)`. Frame size is configurable and must grow
for large/tall art. Height does not change grid pitch or scale the entire sprite.

The floor or authored registration determines position/scale independently of
feet and alpha bounds. Shoe toes can extend below the anchor. Floating art keeps
its ground projection; a seated layer retains its ground anchor plus separate
support elevation. Do not apply an elevation twice during recomposition.

For disposable calibration floors, choose width/center registration before
generation (`--registration floor-width`). This preserves a single uniform scale
without certifying or correcting a redrawn floor's aspect. The default strict
square-floor mode remains available. Review physical contact, proportions and
projection visually in either mode; a frame's stored root is not proof of contact.

Use the explicitly recorded calibration color (default RGB 123,209,75), never
background-color guessing. Choose it before generation for the subject's palette:
for unrestricted character clothing, prefer magenta RGB 255,0,255 with
`--key-rgb 255 0 255`; olive/khaki trousers can be damaged by the green key.
Reserve the complete key hue interval in overlapping object parts, not just its
exact RGB value. For magenta subjects choose another explicit contrasting key.
Normalize before keying; keep the resulting frame and anchor. Mixed edges have
an approximate matte. A fully covered floor cannot be measured by the visible-
floor detector: use authored geometry/registration or report unsupported input.
The bundled single-cell processor is not a general multi-cell or layer extractor.

## Deliver and evaluate

Deliver transparent sprites (opaque flat floors), per-sprite ground anchors,
logical occupancy, art bounds, projection, elevation, and animation order/timing.
Use the portable [output contract](references/geometry.md). Inspect placement,
light/dark cutouts, repeated terrain, and animation at the stored ground point.
Never claim exact AI geometry, seamless terrain, or successful separation solely
from metadata. Keep failures and report limits; do not conceal them with clipping,
axis stretching, anchor fitting, or grading changes.

The [eval suite](evals/cases.json) is specified before fresh generation.
Use [the eval protocol](evals/protocol.md) to prepare isolated output destinations
and independent LLM visual review. Use the [visual-review policy](references/visual-review.md)
for perceptible seams, proportions, anchors and motion; pixel metrics are
diagnostics. Deterministic checks still enforce delivery integrity and declared
geometry/timing. A prepared case is not a passed case. Freeze its rubric and this
skill snapshot before a run; do not tune the skill to make that run pass. Record
an explicitly requested grading-policy change as a separate assessment of the
unchanged images, preserving the original grades.

When explicitly asked to improve this skill, use a new frozen run for each
revision. Give fresh executors only the request and frozen skill, retain every
attempt, and keep the rubric fixed. Check both deliverability and visual quality:
fixing a processing error does not establish a good animation or correct perspective.
