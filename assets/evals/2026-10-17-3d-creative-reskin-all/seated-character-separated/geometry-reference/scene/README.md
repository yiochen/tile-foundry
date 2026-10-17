# Fresh direct 3D control: seated-character-separated

The editable ObjectLoader scene is model.json. The complete deterministic modeled builder is 3d_controls_static_scene.js and the seated weighted rig is 3d_controls_static_rig.js. No prior raster was reused and no AI call was made.

From this bundle directory after installing runtime dependencies:

```sh
node scene/3d_controls_static.mjs seated-character-separated /absolute/new-output --suite scene/suite.json --runtime-root /absolute/npm-runtime --scale 2
```

The fixed affine mapping is screenX=anchorX+128*x, screenY=anchorY+128*z-128*y; the flat floor uses a true top-down camera. Art bounds never determine registration.
