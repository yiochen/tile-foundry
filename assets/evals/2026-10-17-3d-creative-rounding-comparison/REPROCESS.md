# Canvas-rounding processing comparison

This is a new processing-only comparison of `lava-tile` and
`seated-character-separated` from `2026-10-17-3d-creative-reskin-all`.
It uses the same three original generated PNGs, exact original generation
recipes/prompts/tool arguments (including their historical original call paths),
and unchanged guide/reference/model/capture inputs. No new image-generation call
was made. The original frozen skill, deliveries, run metadata, reviews and rubric
were not edited by this reprocessing operation.

The only extractor change computes the common least-squares whole-canvas scale
first, then requires each actual source dimension to be within one source pixel
of its mapped guide dimension. The previous directional-ratio extrapolation
rejected the 971×1620 portraits despite residuals of only −0.735294 and +0.441176
source pixels from the common scalar 2.530560661764706. This corrects canvas
rounding; it does not correct image content or establish geometry adherence.
The clipping, gutters, maximum one-pixel transparent virtual padding, equal-axis
scale, zero-offset and no-fitting checks are unchanged.

Commands run from the repository root:

```sh
.venv/bin/python skills/build-overlap-tiles/scripts/prepare_evals.py \
  --run-root assets/evals/2026-10-17-3d-creative-rounding-comparison \
  --case lava-tile --case seated-character-separated
.venv/bin/python assets/evals/2026-10-17-3d-creative-rounding-comparison/reprocess.py
.venv/bin/python -m unittest discover -s tests -p 'test_registered_sheet.py'
.venv/bin/python -m unittest discover -s tests
```

`prepare_evals.py` froze the updated skill before extraction and prepared the new
requests with their comparison output paths. `reprocess.py` then:

1. Copied the unchanged sources, exact original generation recipes, authored
   guides, supplied references, geometry captures, editable model and scene code.
   Each case's `provenance/reused-source.json` inventories original and copy paths
   with verified matching SHA-256 hashes. Historical case metadata/scripts are
   retained under `provenance/original-case-metadata/`; historical normalized PNGs,
   preview images and reviews were not copied into this comparison.
2. Ran the **new frozen** `extract_registered_sheet.py` with `--kind object
   --min-alpha 32` on lava, then independently on the complete stool and complete
   character canvases using their original one-panel guides. Exact CLI argument
   vectors, captured stdout/stderr and exit codes are in
   `processing-command-log.json` and the case `processing-logs/` files. All three
   extractions exited successfully.
3. Assembled v2 manifests using the frozen `assemble_result.py`. Lava keeps the
   authored 128×128 footprint, 32px height, 192×320 frame and ground anchor
   `(96,248)`. The layered result keeps both complete independent sprites, their
   common ground anchor, the original scene's attachment `(96,220.48)`, and the
   character's 48px support elevation baked into art exactly once. Each sprite
   explicitly links its own original PNG and source hash.
4. Composited the new independently extracted stool and character at their
   unchanged stored roots with offsets `(0,0)` and no additional lift. Produced
   light/dark individual and recomposed previews at native size and nearest-neighbor
   2×. No art bounds were fitted; no flattened scene was sliced.
5. Rebuilt canonical submissions from the new `request.txt` output paths and
   saved provenance as `workflow: 3d-imagegen-reskin`, original image-generation
   calls 1/2, this processing run's image-generation calls 0, and the reused source
   run. Original generation recipes retain their historical processing fields;
   the current operation is described by the new execution records and logs.

All 18 registered-sheet tests and all 143 unit tests passed. Source, recipe,
reference and frozen-skill hash inventories were verified. Light/dark previews,
including each isolated layer and the recomposition, were visually inspected.
Independent review, grading, run trial status updates and gallery integration
are handled separately; successful extraction does not establish visual quality.

The script is intentionally single-use for this prepared destination: the
extractor rejects nonempty output directories, preserving every recorded attempt.
