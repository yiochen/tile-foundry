# Fresh direct 3D control: character-directions

No image-generation call or old PNG is an input. Appearance and motion are authored in retained Three.js source. The original full color capture is `source-01.png`; extraction keeps all alpha and uses fixed authored panel rectangles. The ground root, camera and scale never fit to silhouette bounds.

From this case directory, with compatible Node dependencies (`three` 0.186.1 and `playwright` 1.64.0) installed in NODE_PROJECT and Pillow installed in PYTHON:

```sh
node render/scene/3d_controls_motion.mjs character-directions /absolute/new-output --runtime-root /absolute/NODE_PROJECT --python /absolute/PYTHON
node render/scene/3d_controls_motion_inspect.mjs /absolute/new-output /absolute/NODE_PROJECT
```

The saved runner detects its bundled `case.json`, character scene and unchanged extractor; no external art or skill directory is needed. It refuses to overwrite an attempt. Browser rasterization may vary with Chromium/GPU. `commands.json` preserves the actual repository invocation.

Review `previews/playback.html`, all light/dark phase images, and (for terrain) every phase of synchronized and offset-phase 3×3 neighbors at native and 2×. The shader uses a 16px phase-independent edge transition: interior motion is strongest, boundary motion is intentionally stationary. This is authored animation, never model-drawn phases. Pixel diagnostics and declared geometry do not replace visual review.
