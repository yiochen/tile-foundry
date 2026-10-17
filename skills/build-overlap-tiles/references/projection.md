# Target projection

The name is **top-down oblique projection**, also called a **three-quarter RPG
view**. It is a plan-oblique-like parallel convention: the horizontal grid stays
square and screen-aligned, while vertical elevation is drawn upward. “Front-facing”
distinguishes this profile from a diamond-grid isometric view. An illustrated
reference need not represent one physically exact camera pitch.

Inspect [the supplied game-art scene](../assets/perspective-reference.jpg).
Its ground lattice has horizontal/vertical grid axes; roofs, block tops, fronts,
and tall trees are readable together. Some shapes use artistic foreshortening.
The classification is a visual inference; no measured camera angle or exact
engineering subtype is claimed. Use this image to understand composition and
projection. Do not feed the whole scene into generation by default, reuse its
characters, or extract overlapping tiles from it.

## Reproducible profile

Record `projection: "top-down-oblique-square-grid"`, `cellSize: 128`,
`heightAxis: [0,-1]`, and `elevationScale: 1` (one projected pixel per declared
visual-height pixel). Ground coordinates and elevation are separate:

```
screenX = originX + groundX
screenY = originY + groundY - elevationPx
```

This affine rule preserves the ground lattice. Set the projected ground root
before elevating art; do not recenter a floating or tall silhouette afterward.
Default ground placement for cell `(column,row)` is
`((column+.5)*cellSize, (row+.5)*cellSize)`. Subtract the stored local ground
anchor when drawing the complete sprite. Sort/decompose depth using ground
support and authored occlusion, not alpha bounds or the height of the canvas.

For a 128px full-base block, its ground rectangle is 128×128; moving its top
up by 32px creates a 32px front wall and a 160px body. The top can extend above
the cell's upper edge. Large art gets more canvas headroom, not a smaller scale.

## Per-subject art cameras

Characters and round collectibles may use an ordinary orthographic art camera,
while sharing terrain's logical grid and projected root. Use
`character-orthographic` with actual camera matrices. A 35° elevation is an
example, not a recovered angle from the reference. This camera foreshortens floor
depth and is unsuitable for seamless square terrain. Preserve rounded forms in
the authored 3D design rather than stretching a completed character sprite.
Attachments between differently projected assets need matching contact points.
The supplied image suggests artistic per-subject adjustments; its actual source
pipeline is unknown.

## Generation language

> Square-grid top-down oblique game projection, front-facing three-quarter view.
> Keep the ground plane screen-aligned and the supplied cell pitch unchanged.
> Show the top and front of raised forms. Height projects vertically upward;
> tall artwork can overlap the cell or row behind it. Preserve parallel side
> edges and equal feature scale at near/far depths. No diamond-grid rotation,
> vanishing-point convergence, or camera rotation between frames. Use the
> geometry guide's exact footprint, projected ground root, and elevation.

Keep this profile in every generation recipe. For directional characters, rotate
only the subject around its ground root. Preserve nominal standing/anatomical
height across directions; do not resize crouches or raised-arm poses to a common
silhouette box. Match lighting direction separately from the camera.

## Sources for terminology

[An artist's top-down oblique sprite workflow](https://hogpen-games.itch.io/cyrat/devlog/1467259/creating-top-down-oblique-projected-sprites)
uses vertical-height displacement with a top-down camera to reveal top/front.
[Engineering oblique projection](https://eng.libretexts.org/Courses/Illinois_Institute_of_Technology/Introduction_to_Engineering_Drawing_and_Design/03%3A_Module_C_-__Auxiliary_views_section_views_isometric_and_oblique_projections/3.04%3A_Oblique_projections)
explains parallel receding lines and a true-shape plane. These support the
projection family, not an exact camera reconstruction from the supplied image.
