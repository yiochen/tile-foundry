# LLM visual assessment of the saved 13-case run

Assessment: `2026-10-14-llm-visual-v1`, under
`assets/evals/2026-10-11-skill-v2/assessments/`. This is a new assessment of the
existing images, with **zero new generation calls**, no art changes and no
processing retries. Original requests, sources, frozen skill/suite and original
reviews/reports remain intact.

An independent vision-capable LLM receives each request, visual rubric, source
and reference images, processed sprites and placement/repeat previews. It sees
neither earlier verdicts nor pixel-difference scores. Reviews record observations,
inspected evidence, reviewer identity, policy ID and hashes of source/processed
images, guide and result metadata. The grader and review policy are snapshotted
with this assessment for replay.

A workflow audit caught old failure explanations in cached gallery screenshots
and raw result prose. The packet builder now filters registration fields and
rebuilds placement images. Final reviews use a fresh reviewer and only those
sanitized packets; the initial audit supplies no final grades.

The policy is [llm-visual-v1](../skills/build-overlap-tiles/references/visual-review.md).
Visual seams, proportions, anatomy scale, placement and motion depend on visible
evidence. Edge RGB differences, alpha bounds, coverage and clearance estimates
are non-gating diagnostics. Exact artifact hashes, dimensions, declared anchors/
occupancy, frame/layer delivery and 12 fps metadata remain deterministic checks.
Missing or uncertain visual evidence yields `needs-visual-review` if delivery
checks pass; a missing runtime delivery still fails.

**Latest combined outcomes: 4 passed, 9 failed.** The original assessment was
1 passed, 12 failed. The floor, raised lava and orb changed to passed after
qualitative inspection; no image pixels were changed to obtain those grades.

| Case | Latest outcome | Evidence |
| --- | --- | --- |
| Seamless square floor | Passed | Native and 2× 3×3/5×5 repeats show no obvious joins or abrupt lighting changes |
| Raised lava | Passed | Visible raised front wall, full base and visually continuous repeated material |
| Full-cell plinth | Passed | Complete authored base/wall with faithful generated material |
| Floating orb | Passed | Clean cutout, centered ground projection and plausible requested clearance |
| Lantern | Failed | Visible base/projection and height mismatch against the sparse guide |
| Eight directions | Failed | Stable identity/root, but visibly taller than the requested standing guide |
| 2×2 fountain | Failed | Tapered perspective and shallow/shifted base inside the registered footprint |
| 3×2 greenhouse | Failed | Converging perspective and shallow/shifted foundation |
| Disjoint-support arch | Failed | No runtime sprites or registered depth pieces delivered |
| Animated waves | Failed | No processed runtime frames delivered |
| Animated lava | Failed | No processed runtime frames delivered |
| Seated character layers | Failed | No normalized runtime layers delivered |
| Dancing player | Failed | No calibrated runtime frames delivered |

The five missing runtime deliveries have open runtime visual criteria. Raw arch
and stool sources also show projection concerns, recorded separately from the
delivery failure. Playback/loop quality remains open without runtime playback.
The two multi-cell cases lack a neighboring tall-row occlusion preview, so their
overlap criteria remain open; their observed projection/placement defects already
fail the cases. LLM review does not turn missing evidence into a pass.

The playground shows the latest LLM findings and separate image diagnostics.
Its assessment selector retains the original grading against the same art, with
separate report URLs. It does not select an older success over a newer failure.

```sh
# Replay latest assessment: no generation calls
npm run eval:skill
# Replay original frozen grader/reviews
python tools/run_skill_evals.py --assessment original
```

Replay success means the recorded outcomes reproduce; it does not mean every
artwork passed. These LLM judgments do not establish pixel-exact geometry.
