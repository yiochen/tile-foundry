# SVG geometry and AI appearance

Choose what owns geometry. A whole-object model render can drift from a guide;
authored SVG faces with generated material keep the silhouette deterministic.
Use the latter when exact full-base joins or specific elevations are required.

```sh
python "$SKILL_DIR/scripts/svg_tools.py" template "$OUTPUT_DIR/template" --height 32 --palette coral
```

This bundled example produces a four-stud block: editable SVG, raster reference,
shaded SVG, face masks and geometry metadata. It is an example primitive, not a
general shape generator. Its historical default anchor is the near ground edge
`[96,312]`; for the shared center-anchor output contract, retain the same image
and declare projected ground center `[96,248]`. These are different points on
the same 128px base; do not shift the art or change pitch to convert conventions.
The top moves upward by `height`, while footprint dimensions stay fixed.

Author other silhouettes/masks and larger frames as needed. Keep registration,
visible elevation and footprint in one coordinate system. Do not silently clip
art to the floor rectangle: roofs, foliage and elevated surfaces may extend above
or outside it. A full-base object can occlude its calibration floor, so use
registered authored geometry rather than pretending the floor is still measurable.

For a complete AI redraw, inspect the SVG raster, use it as the sole reference,
and describe appearance in text. Ask for the same base, root, top/front division,
parallel edges, equal detail scale and genuine alpha. Validate the result; a
clipping mask cannot repair internal perspective or altered proportions.
Use an additional identity/style reference only when needed and record its role.
A neutral material sphere is an option when a shape-bearing style image would
compete with the guide, but it does not lock geometry.

For material compositing, generate an opaque flat material swatch with gentle
surface detail, uniform lighting, and no object, bevel, studs, scenery or camera
perspective. Preserve its original image and exact prompt. Then:

```sh
python "$SKILL_DIR/scripts/svg_tools.py" material "$OUTPUT_DIR/template" "$OUTPUT_DIR/source-material.png" "$OUTPUT_DIR/sprite.png" --strength .7
python "$SKILL_DIR/scripts/tile_tools.py" check-solid "$OUTPUT_DIR/sprite.png" "$OUTPUT_DIR/coverage.json" --anchor 96 312 --pitch 128 128 --preview
```

`check-solid` uses the near base edge `[96,312]` for its repeated-coverage geometry,
not the sprite's center root `[96,248]`. The compositor keeps the SVG alpha and
lighting, fitting generated detail to each face. The chosen SVG palette sets
base colors. Inspect texture strength and reuse one material across heights at
the same footprint scale. This does not by itself align material patterns across
neighbors: full-cell alpha and true seamlessness are separate acceptance checks.
