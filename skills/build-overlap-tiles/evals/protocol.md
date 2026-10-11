# Behavioral skill evals

Cases are in [cases.json](cases.json). The two deliberately short user prompts
exercise mode selection, original image generation, calibration, artifact delivery,
and review. They are not tests that the skill contains particular words.

## Fresh run

1. Give an independent executor only the user prompt, the repo skill path, and an
   isolated output directory. It may read referenced skill files and tools, but
   should not see the grader's expected answer or reuse past experiment art.
   Available generation tooling is required for a fresh run. One call per case,
   with at most one explicitly recorded retry for a refused output, is sufficient
   for this smoke eval; record a blocked/failed case honestly if generation fails.
2. Ask it to perform the request using the skill, preserving raw source, guide,
   exact generation recipe, and processed result. It must not alter repo files.
   Independently inspect what it produces; do not accept its self-assessment as
   visual grading. Follow the skill's independent-forward-testing guidance when
   delegation is available and authorized; otherwise a fresh executor session
   can run the same protocol. No special model or API key is assumed.
3. Copy the complete run into `assets/evals/<run-id>/<case-id>/`. Never overwrite
   an earlier run. Create `submission.json` beside it using paths relative to that
   file (a single shared generation source is allowed for all six dance frames):

```json
{
  "caseId": "dancing-player",
  "userPrompt": "generate a player dancing spritesheet on tile",
  "source": "source.png",
  "generationRecipe": "generation.json",
  "guide": "guide.json",
  "result": "processed/result.json"
}
```

The generation recipe follows [the workflow record schema](../references/floor-and-objects.md).
For lava, `result` points at the JSON sidecar from `floor-material`, typically
`tile.json`. For dance it points at `process-on-floor`'s `result.json`.
Failed attempts stay in the run, with a reason; don't convert them to passes by
relabeling existing images or relaxing the authored geometry.

## Grade artifacts and behavior

Run from the repository root:

```sh
python tools/eval_tile_skill.py --case lava-tile --submission assets/evals/RUN/lava-tile/submission.json --output docs/evals/RUN/lava-tile.json
python tools/eval_tile_skill.py --case dancing-player --submission assets/evals/RUN/dancing-player/submission.json --output docs/evals/RUN/dancing-player.json
```

The grader checks the preserved source hash and actual prompt/reference record,
output geometry and alpha, unchanged floor-derived normalization, independent
source-panel floor measurements, explicit key choice, panel order/timing, and
source gutter separation (strict panels or explicit fully transparent separator
recovery). It produces actual floor-repeat or anchored animation
review artifacts via `tilekit.py`; synthetic assets never stand in for a fresh
behavioral run. A missing visual review gives `needs-visual-review`, not a pass.

An independent reviewer examines source/guide/final images and the generated
repeat/animation previews, and writes `review.json` with each `visualChecks` ID:

```json
{
  "reviewer": "independent reviewer",
  "checks": {
    "lava-readable": {"pass": true, "note": "Observed lava at runtime scale."},
    "floor-projection": {"pass": true, "note": "Opaque flat square."},
    "repeat-inspected": {"pass": true, "note": "Repeat inspected; visible seams described here."}
  },
  "limitations": ["One sample does not establish reliability."]
}
```

Re-run the grader with `--review path/to/review.json`. All automatic and required
visual checks must pass for `status: passed`. Exit 0 means passed, 1 means failed,
and 2 means missing visual review. Keep automatic failure and visual failure
separate; an attractive image with guessed anchors still fails the geometry case.
Visual quality remains a judgment, not a claim of exact matting or seamless motion.

## Recheck saved runs

Saved fixtures replay the artifact grader without further image generation. This
checks the pipeline and evidence, not whether today's agent follows the skill:

```sh
npm run eval:skill
```

That command replays the checked-in run, including its expected failed first
dance attempt and the successful corrected/recovered attempt. A run's
`run.json` records expected statuses so the negative example must stay failed.
For an individual case or a new run:

```sh
python tools/eval_tile_skill.py --case lava-tile --submission assets/evals/RUN/lava-tile/submission.json --review assets/evals/RUN/lava-tile/review.json --output docs/evals/RUN/lava-tile.json
```

New skill behavioral scores require a new run ID and fresh generation. Unit tests
exercise deliberate bad submissions (wrong anchor, contaminated gutter, missing
source/prompt record), rather than matching the instruction text.
