# Prompt clauses

Expand only clauses relevant to the request; preserve the exact submitted text
alongside source art. Use the available generation tool and inspect references.

## Shared projection and placement

Square-grid top-down oblique projection, front-facing three-quarter game view.
Ground cells stay screen-aligned. Show tops/fronts of raised forms; height extends
upward, past the cell upper boundary where needed. Keep parallel edges and equal
near/far feature scale. Keep the camera fixed across poses and frames. No diamond
grid, vanishing points, per-frame camera rotation or whole-sprite height scaling.

Keep the supplied footprint and projected ground root. Complete transparent art
can extend outside its logical cell. All requested output files belong under
[absolute output destination]. Preserve originals, references, expanded prompts
and placement/processing metadata.

## Full-cell raised object

Full [width×depth] base at [cell pitch], with [elevation] projected front-wall
height. Keep true square/rectangular ground coverage and parallel sides. Let the
top extend upward; do not shrink the object into the cell. Avoid external glow,
shadows or bevels that obscure measured base edges. Inspect repeated joins.

## Floating object or separated support layer

Keep projected ground root [root] and [clearance/support elevation]. It remains
below the floating/sitting art even after floor/support removal. Final [character]
alpha must contain no floor or [support object]. Deliver a complete separate
[support object] too. Match the attachment pose against its supplied seat/contact
point. Preserve layers and declared elevation without applying the offset twice.

## Identity, direction and motion

One recognizable design with constant anatomy scale, proportions, palette,
lighting and camera. Rotate/pose only the subject. Neutral standing directions
retain the same nominal height and root; action silhouettes may change bounds.
Animate at exactly 12 fps, with [frame count] complete isolated frames in [order].
Keep the full poses inside panels. Maintain transparent separation and inspect
last-to-first looping, not merely individual frames.

## Connected terrain

Opposite edges must continue texture and color/lighting smoothly. No visible seam
or abrupt global gradient at tile joins. For animated terrain, continue across
neighbors in every frame and inspect offset-phase neighbors plus the temporal
loop. Preserving a geometric alpha rectangle alone does not satisfy this clause.
