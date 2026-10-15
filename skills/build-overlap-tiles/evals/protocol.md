# Portable behavioral eval protocol

[cases.json](cases.json) defines 13 cases. Freeze this suite and the skill in a caller-selected
workspace before each fresh run. Keep results with that run, outside the skill bundle.
It covers appearance, projection, delivery, footprint/anchor geometry, separation,
seams, direction consistency, and 12 fps motion. Synthetic script tests and old
artifacts are not fresh behavioral eval results for this suite.

## Prepare destinations and freeze the contract

Set both paths explicitly. The skill can be copied anywhere; commands do not
require a particular repository or working directory.

```sh
SKILL_DIR="/absolute/path/to/build-overlap-tiles"
RUN_ROOT="/absolute/path/to/eval-runs/run-001"
python -m pip install -r "$SKILL_DIR/scripts/requirements.txt"
python "$SKILL_DIR/scripts/prepare_evals.py" --run-root "$RUN_ROOT"
```

The destination must be empty and outside the skill directory. Preparation copies
this complete skill into `skill-snapshot/`, saves the suite and hashes, and creates
`<case-id>/request.txt` with `{{OUTPUT_DIR}}` replaced by that case's absolute
output directory. `run.json` starts every trial as `not-run`. No artwork is made.
Use repeated `--case CASE_ID` to prepare a subset. Never overwrite an earlier run.

Give an executor only its `request.txt`, the frozen skill path, and available
image-generation tools. Give the expected rubric to the independent reviewer,
not as an executor's answer key. Follow applicable delegation/permission rules;
a fresh separate session can execute the same request without subagents.
The output path in the request is a storage instruction, not text to paint.

## Execute once, retain failures

Use one fresh generation attempt per case, except the seated-layer case's two
planned calls (stool, then character). Record actual calls, references and any
unsupported step. Do not automatically retry, edit the rubric after seeing an
output, tune the skill to pass, recycle old assets, or make manual anchor/scale
adjustments that hide a failure. A later revision requires a new frozen run.

Save all sources, generation recipes, guides, full output PNGs and geometry under
the requested case directory. Copy references into that bundle. The result uses
[the portable output contract](../references/geometry.md), with relative paths.
If a tool limitation prevents a case, record `blocked` with the concrete reason;
do not fabricate a partial success.

Example `submission.json` (fill actual resolved paths and request text):

```json
{
  "caseId": "lava-tile",
  "outputDirectory": "/absolute/path/to/eval-runs/run-001/lava-tile",
  "userPrompt": "Exact contents of request.txt, without its final newline",
  "sources": [{"image": "source-01.png", "recipe": "generation-01.json"}],
  "guide": "guide.json",
  "guideSHA256": "SHA-256 of the authored guide.json",
  "result": "result.json"
}
```

Each generation recipe stores the exact model prompt, `references` relative to
the recipe, `referenceSHA256` and `referenceRoles` keyed by those same paths,
`transparentBackground` (a boolean), `tool`, and `sourceSHA256`. Preserve all
sources; the layered case has at least two source/recipe records. The source,
processed art and registration must be inspectable together.

Source records default to `role: "whole-asset"`: isolated art uses transparent
generation and a geometry reference; flat-floor art uses opaque generation.
For the authored-SVG/material workflow, declare `role: "appearance-material"`
on that source record. Its generated material is a complete opaque square and
may have no raster references (`references: []`, empty hash/role maps). Retain
the SVG faces/masks and material mapping so the reviewer can establish source
faithfulness. This role does not permit replacing whole-object art after generation.

Bundled processors retain their measured geometry in their own sidecars. For
`process-on-floor` or `floor-material`, wrap those outputs in the v2 contract with
`scripts/assemble_result.py`, as described in [geometry](../references/geometry.md).
Author registration constraints before generation; they are not measurements
proving that the output met the requested height or occupancy. Other processors
must supply the same v2 manifest with actual frame geometry and provenance.

## Delivery checks and independent LLM visual review

```sh
CASE_ID="lava-tile"
python "$RUN_ROOT/skill-snapshot/scripts/evaluate.py" \
  --run-root "$RUN_ROOT" --cases "$RUN_ROOT/suite.json" --case "$CASE_ID" \
  --submission "$RUN_ROOT/$CASE_ID/submission.json" \
  --output "$RUN_ROOT/reports/$CASE_ID.json"
```

The grader reads the independently selected prepared run root to check the frozen
request and destination; a submission cannot redefine its own storage instruction.
It checks location/path containment, exact request, unchanged sources and
references, readable PNGs, expected frame dimensions/anchor/occupancy/elevation
metadata, floor/material opacity, disjoint support/depth-piece registration,
separate layer roles and a 12 fps schedule. Image-derived edge RGB deltas, coverage,
bounds, apparent height and clearance are **non-gating diagnostics**. They cannot
establish visible seams, perspective, anatomy, contact or separation quality.

Prepare evidence for an independent vision-capable LLM:

```sh
python "$RUN_ROOT/skill-snapshot/scripts/prepare_review.py" \
  --run-root "$RUN_ROOT" --case "$CASE_ID" \
  --output "$RUN_ROOT/review-packets/$CASE_ID"
```

Give the reviewer the packet, review template and [visual-review policy](../references/visual-review.md).
Withhold old verdicts and pixel metrics. Require actual image inspection at native
and 2× scale, with repeats and motion playback where applicable. Use the packet's
filtered registration and fresh placement views; arbitrary cached screenshots
or raw result notes may expose previous failure explanations.

An independent reviewer inspects originals, processed art and actual previews:

- Repeated floors at native and 2× scale: no gaps, discontinuous patterns or
  sudden gradients across either axis. Pixel differences and repeated motifs alone
  do not establish a visible seam.
- Raised full bases: visible front-wall height, complete occupancy and back-row overlap.
- Partial/floating art: proper scale/ground projection and complete floor removal.
- Eight upright directions: correct orientation, consistent anatomy/standing
  height and physically plausible support at the common ground root. Shoe toes
  are not the ground root.
- Large/arch art: shared cell scale, explicit support occupancy, clear middle
  passage and correct foreground/background depth-piece occlusion.
- Layered sitting: stool and character individually clean and complete, with
  actual recomposition at recorded roots/attachment points and no double elevation.
- Animation: all frames at 12 fps, constant anatomy scale/root and camera, readable
  motion and last-to-first looping. Also inspect animated terrain as spatial
  repeats at every phase and with offset-phase neighbors.

Save `review.json` with `policy: "llm-visual-v1"`, `reviewerType: "llm"`,
an independent reviewer identifier, `independent: true`,
`spriteSHA256` mapping every sprite and depth-piece ID to its current PNG hash,
`sourceSHA256` mapping each original source path to its hash,
`resultSHA256` and `guideSHA256` binding the review to the delivered metadata,
and one `{ "pass": true|false|null, "note": "specific observation",
"evidence": ["inspected image/preview path"] }` per `visualChecks` entry.
Use `false` for a visible defect; `null` for insufficient evidence. Requested
visual sizes are design targets, judged against the guide, without invented
pixel precision. Optional landmark estimates belong in `measurements` as
diagnostics. Do not infer standing height solely from an alpha bounding box.
Missing review/evidence cannot pass, and missing runtime frames still fail delivery.

```sh
python "$RUN_ROOT/skill-snapshot/scripts/evaluate.py" \
  --run-root "$RUN_ROOT" --cases "$RUN_ROOT/suite.json" --case "$CASE_ID" \
  --submission "$RUN_ROOT/$CASE_ID/submission.json" \
  --review "$RUN_ROOT/$CASE_ID/review.json" \
  --output "$RUN_ROOT/reports/$CASE_ID.json"
```

Exit codes: passed 0, failed 1, needs independent visual review 2. Keep the full
case report; do not add correction generations or omit failed frames to upgrade
a result. Retain `not-run` until generation actually occurs. If the user requests
a grading-policy change, freeze that policy and grader in a new assessment
directory, independently review the unchanged images, and save new reviews and
reports there. Preserve the original skill snapshot, suite, images and grades;
label the new assessment separately from a fresh generation run.
