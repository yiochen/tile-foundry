# LLM visual validation · llm-visual-v1

Use an independent vision-capable LLM to judge the delivered artwork against the
user request and each case's visual criteria. Inspect the actual images with an
image-viewing tool; filenames, manifests and numeric summaries are not visual
evidence. Record the reviewer/session identity and the policy ID above.

Give the reviewer the request, rubric, guides/references, originals, processed
sprites and placement/repeat/animation previews. Withhold earlier verdicts,
failure explanations and pixel-difference scores until the review is complete.
`scripts/prepare_review.py` builds a packet and hash-bound review template.
Use its curated registration and listed images. The helper rebuilds placement
views instead of forwarding cached gallery screenshots or result prose, which
can reveal earlier grades. Do not supply those other files to the reviewer.

Judge visible, practical quality at native game scale and 2×. For a floor, inspect
3×3 and 5×5 repeats: are joins, gaps or abrupt lighting/pattern changes visible?
Repeating motifs alone are not a seam. Opposite-edge RGB differences measure
different samples in a textured image; they do not decide visual success.

For objects, compare proportions, support, projection, apparent height and
placement against the guide. Treat requested visual heights as design targets;
explain a noticeable mismatch without inventing exact landmark measurements.
For directions and motion, compare anatomy scale and the projected ground root,
allowing for pose changes, shoe length and legitimate airborne motion. Never use
silhouette bounds alone to infer standing height or contact. Inspect all frames
and actual 12 fps playback to judge motion and the loop boundary. If playback or
an obscured landmark cannot be inspected confidently, leave that criterion open.

For each visual criterion record `pass: true`, `false`, or `null`, a specific
`note`, and `evidence` listing the images/previews inspected. Use `false` for an
observable defect, and `null` for insufficient evidence. A missing processed
asset cannot earn a visual pass from an attractive source image. State what raw
sources show separately from what the runtime delivery establishes. An LLM
review is qualitative evidence, not proof of pixel-exact geometry.

The grader combines two independent parts:

- **Delivery checks:** file/provenance integrity, dimensions, declared anchors and
  occupancy, required layers/frames and exact 12 fps metadata remain deterministic.
- **Visual checks:** the LLM's evidence-based judgments decide appearance,
  continuity, proportions, placement and motion. Image-derived seam, coverage,
  bounds and clearance metrics are non-gating diagnostics. Optional landmark
  estimates are also diagnostics, with uncertainty recorded by the reviewer.

A delivery failure or an observed visual failure fails the case. With no failure,
missing or uncertain visual evidence yields `needs-visual-review`, never a pass.
Do not change artwork or retry generation during assessment. To adopt a new
grading policy, save a separately identified assessment with its policy, grader
snapshot, reviews and reports. Preserve the original frozen run and grades.
