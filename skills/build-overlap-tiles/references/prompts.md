# Prompt recipes

Replace the bracketed fields. Save the final expanded prompt alongside source art.
Use the available built-in image-generation tool. Do not assume API credentials exist.

## Complete isolated object

Use case: stylized-concept
Asset type: one complete transparent orthographic 2D game sprite
Input images: [style reference] supplies palette, materials, edge treatment, and
lighting; [geometry guide] supplies projected footprint and baseline. The guide is
not artwork: omit all guide lines, anchor marks, labels, and background.
Subject: [one object and its visible height].
Camera: orthographic parallel projection, top and front visible. Far and near body
edges have the same width, side edges remain parallel, and repeated details have
the same size at every depth. No perspective taper, vanishing points, wide-angle
lens, or diamond grid. A tilted orthographic camera may foreshorten depth equally.
Composition: one isolated complete silhouette with transparent margins. Ground
contact stays at the guide's baseline. Height extends upward. Include hidden-back
parts so the sprite can be rearranged with any neighbor.
Lighting: upper-left light, consistent darker front faces.
Constraints: real alpha transparency, opaque object interior, clean silhouette,
no glow, bloom, aura, detached marks, checkerboard paint, ground, neighbors, labels,
frames, or cast shadow extending outside the footprint.

## Controlled variant

Use the approved [object] as the geometry, style, lighting, and scale reference.
Change only [material/color/surface pattern]. Preserve the outer footprint,
ground-contact point, top/front division, camera angle, and complete silhouette.
Keep the background genuinely transparent. Keep height unchanged unless requested.
Validate alignment afterward; an instruction alone does not guarantee exact pixels.

## Flush solid-cell block

Use [approved style] for material and [geometry guide] as the primary shape.
Generate an opaque rectangular top-and-front body. Its left and right edges are
straight and parallel; far and near widths are equal. No trapezoid, side-plane
convergence, glow, external shadow, or protruding bevel. Repeated studs have equal
sizes in both rows. Keep corners almost square. At the intended uniform scale,
the opaque body must span the full [128px] column pitch, and its vertical coverage
must reach or overlap the next row at [128px] pitch. Keep height upward from the
fixed ground contact. Validate opacity in a repeated neighborhood and equal side
spans; regenerate if taper remains. Do not stretch only one axis to hide a failure.

## Height variant

Use [approved object] for style and [height guide] for geometry. Preserve footprint
width and ground-contact baseline. Change only vertical elevation to [height].
Extend art upward rather than scaling the entire object. Keep the same lighting,
materials, and edge treatment. Keep the entire sprite isolated and transparent.

## Seam-preserving floor variant

Edit only the interior of [approved repeatable floor tile]. Keep its outer [8 px]
edge band and opposite-edge continuation unchanged. Add [small details] away from
the boundary. Keep the same top-down projection, base color, and lighting.
Compare the actual boundary pixels afterward. Composite the original edge band
back programmatically if generation changed it; preserve the unedited source.

## Transparent extraction repair

Remove only the surrounding alpha haze/glow of this supplied sprite. Preserve all
solid object pixels, shape, ground contact, scale, and lighting. Produce a crisp
antialiased silhouette on a genuinely transparent background. Add no shadow,
background, text, frame, or new features. Inspect final-size edges afterward.
