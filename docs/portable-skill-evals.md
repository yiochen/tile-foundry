# Portable skill revision and eval suite

The complete `skills/build-overlap-tiles/` folder is reusable outside this project.
Its instructions reference no playground, source checkout, application name or
project asset directory. Shared processing now lives in bundled Python scripts;
`tools/` keeps compatibility wrappers and the project-specific Tiled adapter.
The original game-art image is bundled as a projection reference with provenance.

The perspective profile is **top-down oblique projection, square-grid,
front-facing three-quarter game view**. Square ground cells keep their pitch;
height projects upward and can cross the upper cell boundary. A ground root is
not a visible shoe tip, floating object's bottom, or cropped alpha center.
No physical camera angle is inferred from the stylized reference.

The suite was specified before changing the skill instructions and before any
new generation. All 13 now have fresh results in [the v2 findings](skill-eval-v2-findings.md),
with 14 generation calls. The original pixel-gated assessment recorded one passed
case and twelve failed cases. A separate [LLM visual assessment](llm-visual-eval-findings.md)
reviews the same unchanged images; the playground defaults to that latest policy.

| Case | Expected behavior |
| --- | --- |
| Seamless square floor | Full opaque 128px square; texture/color continuity in 3×3 and 5×5 repeats |
| Raised lava tile | Full cell base, 32px front wall, upward elevation and connected repeats |
| Full-cell raised object | Full base with 64px height and no opaque coverage gaps/taper |
| Partial-cell tall object | 48px centered base, 160px height, clean floor removal |
| Floating object | 48px clearance above its preserved projected ground root |
| Eight character directions | Same identity, 160px nominal standing scale, root consistency |
| 2×2 object | 256×256 ground footprint at the shared grid scale |
| 3×2 object | 384×256 rectangular footprint with full art and fixed anchor |
| Disjoint-support arch | Outer support cells, walkable center, separately authored overhead/depth pieces |
| Animated waves | Full base and visible elevation; 12 frames at 12 fps; spatial/temporal continuity |
| Animated lava | Same placement/height/timing invariants with moving surface detail |
| Stool plus seated character | Two complete separate layers; proper attachment and support elevation applied once |
| Dancing character | 12 frames at 12 fps, stable anatomy scale/root, clean extraction and looping |

Directions use neutral standing poses to compare anatomy scale. Both
directions and dance use independent LLM visual inspection;
toe lengths, crouching and raised arms legitimately change the bounding box. Metadata alone
cannot establish scale, foot placement, perspective, separation or seam quality.

Choose an empty workspace in the target project or an isolated directory:

```sh
SKILL_DIR="/absolute/path/to/copied/build-overlap-tiles"
RUN_ROOT="/absolute/path/to/target-project/eval-runs/run-001"
python "$SKILL_DIR/scripts/prepare_evals.py" --run-root "$RUN_ROOT"
```

This creates 13 destination-specific requests, a frozen skill/suite and a run
manifest with `not-run` statuses. The grader lives in the copied skill and accepts
the independently selected prepared run root, suite, submission, review and report path. Independent visual review
is required before a structural success can become a pass. Pixel seam/coverage/
height metrics are diagnostics, while file integrity, declared geometry and
12 fps metadata remain deterministic delivery checks. The skill includes a
hash-bound reviewer-packet builder and a portable visual-review policy. Generation
attempts are frozen; the fresh v2 run used no retries or skill tuning. A requested
grading-policy change produces a new assessment, preserving the original record.

The original two-case run is preserved separately with its own `cases.json`.
Its original 8 fps generation records stay unchanged. The old frames and flat lava are excluded from the playground. Its current
eval view publishes only results matching the current case rubric.

Validation: copied-skill commands run from an unrelated temporary project;
requests resolve under the caller's output root; grading respects visual verdicts
instead of pixel cutoffs, leaves uncertain judgments open, and still rejects
missing/altered sources, wrong destinations, stale reviews and 8 fps durations.
These are synthetic helper tests, not AI generations.
