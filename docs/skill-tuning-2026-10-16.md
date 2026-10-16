# Skill forward tests: 16 October 2026

The failures have mixed causes. Some are model noncompliance with clear size or
projection instructions; others are avoidable prompt, processing or delivery
contract problems. A failed delivery does not establish that all its visual
criteria failed.

## Evidence from the original run

| Family | Supported cause | Change |
| --- | --- | --- |
| Animated lava/waves | Executor requested transparent material atlases although the compositor requires opaque textures; final sprite instructions were pasted into intermediate material prompts | Explicit source-role routing, call-scoped prompts, opaque atlas helper |
| Terrain joins | Per-tile broad lighting and bevels introduce row resets; generated atlas layout can put bright gutter pixels inside material samples | Continuous terrain lighting; separate one-material authored-flow route |
| Lantern | Prompt already specified a 160px crown, root and 48px base; the model made a much taller lantern and rotated its base | Filled whole-subject envelope, visual ratios alongside pixels; retain failures |
| Directions/dancer | Model redraws calibration floors and changes subject scale; the square-aspect prerequisite rejects even otherwise extractable frames | Preselected width/center calibration using one uniform scale, with observed geometry retained for visual review |
| Character cutouts | The floor key erased almost-neutral clothing whose unstable hue happened to match the key | Strong saturation confidence in the explicitly reserved key; same-source processing comparison |
| Seated layers | Prompt mixes temporary floor retention with final floor removal; raw separated character omits required registration | Call-scoped source instructions; explicit limits of the floor processor. Not rerun here |
| Large objects/arch | Converging or mirrored projection and panel overflow despite explicit instructions; disjoint/depth tooling also needs authored registration | Clarify extractor/registration choice before generation. Not claimed fixed or rerun here |
| Seamless floor | Prior strict RGB comparison rejected a visually acceptable repeat | Already resolved by the separately preserved LLM assessment; no grading change in these forward tests |

The original sources and exact prompts are in
`assets/evals/2026-10-11-skill-v2/`. The audit particularly compared
`animated-lava/generation-material.json`, `dancing-player/prompt-player.txt`,
`seated-character-separated/prompt-character.txt`, and the latest independent
reviews under `assessments/2026-10-14-llm-visual-v1/`.

## Test isolation and iteration

Every executor starts with `fork_turns: none` and receives only its realistic
request, frozen skill and runtime/tool access. It does not see earlier outcomes,
the rubric, suspected defect or intended fix. Each selected case gets exactly one
fresh built-in image call per run. New revisions are separate runs; no attempt
is overwritten or selected away. All original 13 case definitions remain
unchanged. Independent reviewers see sanitized evidence packets, original art,
guides, complete processed frames, registered previews and ungraded playback.

| Run | Cases | Image calls | Purpose |
| --- | --- | --- | --- |
| `2026-10-16-skill-r1` | Lantern, dance, animated lava | 3 | Source-scoped prompts, filled height envelope, opaque material route |
| `2026-10-16-skill-r2` | Lantern, directions, animated waves | 3 | Relative height/base ratios and holdouts |
| `2026-10-16-skill-r3` | Directions, dance, animated lava/waves | 4 | Width/center calibration and continuous terrain lighting |
| `2026-10-16-skill-flow` | Authored flowing lava | 1 | Additional case specified before generation; one material with authored periodic motion |
| `2026-10-16-skill-r4` | Dance | 1 | Palette-aware calibration hue after foreground cutout damage was observed |
| `2026-10-16-chroma-processing` | Same round-4 dance source | 0 | Clean processing executor and independent review; unchanged generated pixels, source layout and normalization |

The original animation requests explicitly require a 4×3 source-panel layout.
Fresh agents therefore chose model-drawn phase atlases in those cases. The new
flow case requests a 4×3 runtime sheet without requiring model-drawn source
phases. It is a different contract, not a replacement grade for those cases.

Width/center calibration keeps the measured floor center as root and normalizes
its width to the shared pitch, uniformly on both axes. It does not warp a floor
into a square, fit feet, resize to silhouette height, or prove physical contact.
The legacy strict square-floor mode remains available. Neither mode changes the
visual rubric; independent review can still reject contact, scale or projection.

The flow helper wraps the complete AI material through one cycle and blends
moving detail toward the initial material near authored face boundaries. Motion
is explicitly authored; the model supplies one texture. Geometry, alpha and
stored root remain fixed. This is unsuitable for character poses or splashes.

## Delivery and review findings

Round 1/2 lanterns remain too tall. Relative sizing improved the base's alignment
in round 2 but did not solve height compliance. The first two terrain deliveries
now contain twelve usable PNG frames, but independent review still observes
spatial seams. Those processing successes are not visual passes.

Round 3 produces all eight direction sprites and twelve dance sprites. Independent
review still finds physical support/root offsets and cutout defects. The dance's
olive trousers are visibly damaged by the green key despite successful extraction.
The skill now selects a calibration hue for the subject palette and reserves its
entire matte interval. Round 4 used magenta, but independent review still found
cutout damage and root/contact problems. A different key hue alone did not solve
the processing defect.
The direction manifest also uses a noncanonical direction encoding; its frozen
`eight-directions` failure remains. The output contract now explicitly lists
compass codes, independently of the full names used in prompts.

Inspection of the keyer found its saturation confidence rose from .02 to .12:
almost-neutral pixels could be erased based on an unreliable hue. The default
transition is now .40 to .50 and the explicit calibration key must be sufficiently
saturated. A regression test covers neutral garments under both green and magenta
keys. This does not recover foreground colors that genuinely overlap the key or
guarantee removal of a pale, incorrectly rendered calibration floor.

The processing comparison reuses the exact round-4 source and recipe, with zero
new image calls. A clean executor runs the frozen processor without seeing prior
outputs or reviews. All twelve panel rectangles, measured floors, normalization
transforms, frame sizes and roots match the original processing. Alpha never
decreases, existing visible RGB is unchanged, and 2,489 pixels regain some alpha;
the receipt is `dancing-player/processing-comparison.json`. That isolates a real
processor effect, while the independent visual review determines its quality.
That review still rejects cutout quality because small pinholes, ragged edges and
detached specks remain. It also rejects root/contact stability and the visible
12-to-1 whole-body position pop; design height remains unknown. The comparison
passes all delivery checks but remains `failed`. Restoring damaged pixels is an
improvement, not a claim of production-ready separation.

The additional authored-flow case passes the review's spatial-seam, height,
placement, frame-consistency and provenance criteria, with all deterministic
delivery checks passing. Temporal-loop remains `null`: sampled browser frames
cannot establish smooth 12 fps playback confidently. Its combined status is
`needs-visual-review`, not passed. Model-drawn phase-atlas cases still fail seams.

The first lantern executor also needed a format-only canonical serialization of
its richer delivery record. Original records remain as `*-authored.json`; no
prompt, source, reference or processing changed. The portable contract now has
concrete recipe/submission examples.

Atlas runs exposed another delivery-contract omission: the material-layout guide
lacked runtime `cellSize` and `anchor` fields expected by the grader. Those frozen
runs retain their failed `registered-guide` checks. The helper now declares
runtime frame/anchor separately from source canvas/sample rectangles. No old
guide or grade was rewritten to conceal that issue.

Browser testing also found a playback script using a conflicting global `top`
binding. The shared helper now uses module scope. Frozen snapshots remain intact;
case-local preview workarounds are documented. Playback was tested in Chromium
for phase progression, seek, light/dark and offset neighbors.

Reports and hash-bound reviews live under each run's `reports/` and `reviews/`.
The playground retains every generation and original grading in its attempt
selector. Source previews remain labeled when no runtime delivery exists.

```sh
python tools/run_skill_evals.py --run assets/evals/2026-10-16-skill-r1
python tools/run_skill_evals.py --run assets/evals/2026-10-16-skill-r2
python tools/run_skill_evals.py --run assets/evals/2026-10-16-skill-r3
python tools/run_skill_evals.py --run assets/evals/2026-10-16-skill-flow
python tools/run_skill_evals.py --run assets/evals/2026-10-16-skill-r4
python tools/run_skill_evals.py --run assets/evals/2026-10-16-chroma-processing
```

Replay success means preserved outcomes reproduce, including failures. It does
not mean all artwork passed. These small, unpaired samples demonstrate concrete
workflow defects and improvements; they do not estimate a model success rate or
isolate the causal effect of each individual prompt phrase.

## Repository verification

All 107 unit tests pass. Asset generation, production build, skill validation,
and browser verification pass, including all 14 gallery cases, original/raw and
runtime players, mouse/touch scrubbing, and 390px/320px layouts. The latest
processing comparison was also checked directly on desktop and mobile with its
same-source label, preserved prompt and twelve-frame player. Screenshots are
saved as `docs/preview-eval-processing-desktop.png` and
`docs/preview-eval-processing-mobile.png`.
