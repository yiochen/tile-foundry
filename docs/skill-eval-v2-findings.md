# Fresh 13-case skill run

This records the **original grading**. The later [LLM visual assessment](llm-visual-eval-findings.md)
uses the same unchanged images and preserves these grades separately. In particular,
the floor's RGB cutoff did not establish a perceptible seam; the original failure
description below overstated the visual evidence. The playground defaults to the
latest assessment and offers the original in its assessment selector.

All cases were rerun against the frozen skill and rubric in
`assets/evals/2026-10-11-skill-v2/`. Three independent executors received the
requests and workflow instructions; root separately inspected sources, cutouts,
placement/repeat previews and processing diagnostics, then recorded reviews.
There were **14 built-in imagegen calls**, one per case and two planned calls
for stool plus character. No generation retries or skill tuning occurred.

**One case passed; twelve failed.** The gallery publishes failures alongside
successful outputs. A matching stored anchor does not prove actual contact,
requested scale, texture continuity or usable layer separation.

| Case | Grade | Observed result |
| --- | --- | --- |
| Seamless square floor | Failed | Opaque square, but cut stone/moss contours and RGB edge deltas above 8 |
| Raised lava | Failed | Exact authored 32px wall/base; discontinuous molten-channel joins |
| Full-cell raised plinth | Passed | Complete authored 128px base and 64px wall with freshly generated stone detail |
| Partial-cell lantern | Failed | Clean floor extraction; roughly 232px root-to-top height and oversized/angled base |
| Floating orb | Failed | Root retained; 51px clearance usable, but 85px object height instead of 64px |
| Eight directions | Failed | Consistent player and roughly uniform height; about 181px rather than 160px, physical contact tolerance unverified |
| 2×2 fountain | Failed | Complete output, but foreshortened/shifted base does not fill registration |
| 3×2 greenhouse | Failed | Complete output, but oversized width and compressed/shifted ground depth |
| Disjoint-support arch | Failed | Overhead end crosses its isolated panel; safe depth-piece extraction refused |
| Animated waves | Failed | Material opacity/layout drift; no valid raised runtime frames |
| Animated lava | Failed | Material opacity/layout drift; no valid raised runtime frames |
| Stool plus seated character | Failed | Independent raw layers, but warped stool floor and missing character floor prevent verified recomposition |
| Dancing player | Failed | Twelve source poses; transparent-separator recovery succeeded, then floor aspect validation refused normalization |

The full-base static cases used the skill's documented generated-material/SVG
route. That geometry is authored, not a claim that AI produced exact geometry.
Other objects used sparse SVG guidance and floor or authored-canvas registration.
Original image bytes and actual prompts are retained, including failures.

Lossless packaging corrections converted authored reference records to the
portable path/hash maps, request aliases to submission fields, and asset/direction
type names to canonical enums. Original sidecars are retained. These changed no
artwork, references, prompts, dimensions, anchors or attempt budgets.

Dancing's first provisional diagnosis inferred an opaque background from an
inline preview. Inspection of the actual PNG found transparent separator bands.
The frozen documented recovery partitioned every retained pixel into twelve raw
panels without clipping. All resulting calibration floors still exceeded the
allowed aspect range (about 1.062–1.133), so no runtime cutouts were fabricated.
A **12 fps raw-source diagnostic** is preserved; it is not a passing calibrated
animation. Physical-root measurements were not invented for missing outputs.

The playground's **Evals** tab shows the current suite's exact prompts, expanded
model prompts/references, original art, processed sprites, checks and diagnostics.
**Animations** filters the same current cases. The old two-case pilot is removed
from the published gallery; its raw repository archive remains provenance.

Run `python tools/run_skill_evals.py --assessment original` to replay this original
grading. `npm run eval:skill` replays the latest recorded assessment.
An exit-success replay means the recorded grades were reproduced, including
failures; it does not mean every case passed. Run `npm run assets` to publish the
latest recorded outcome for each unchanged case rubric. The site never chooses
an older success to hide a newer failure.
