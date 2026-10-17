"""Capture complete fixed frames from the authored .blend; no pose fitting."""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

output=Path(sys.argv[sys.argv.index('--')+1]).resolve()
scene=bpy.context.scene
rig=next(o for o in scene.objects if o.type=='ARMATURE')
scene.camera=bpy.data.objects['Camera • character']
scene.render.pixel_aspect_x=scene.render.pixel_aspect_y=1
scene.render.resolution_x=768;scene.render.resolution_y=1280
scene.cycles.samples=32
frames=output/'capture';frames.mkdir(exist_ok=True)
landmarks=[]

def pixel(point):
    p=world_to_camera_view(scene,scene.camera,point)
    return [p.x*192,(1-p.y)*320]

for frame in range(1,25):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    landmarks.append({'frame':frame-1,'root':pixel(Vector((0,0,0))),
        'ankles':{side:pixel(rig.matrix_world@rig.pose.bones['foot.'+side].head) for side in ['L','R']},
        'footMatrices':{side:[list(row) for row in rig.pose.bones['foot.'+side].matrix] for side in ['L','R']}})
    scene.render.filepath=str(frames/f'frame-{frame-1:02d}.png')
    bpy.ops.render.render(write_still=True)

(output/'landmarks.json').write_text(json.dumps(landmarks,indent=2)+'\n')
scene.frame_set(1)
scene.camera=bpy.data.objects['Camera • grid comparison']
scene.render.pixel_aspect_x=math.sqrt(2)
scene.render.pixel_aspect_y=1
# The non-square-pixel camera projection is baked into capture, not a sprite edit.
# Calibrate X to match the character profile's unchanged world scale.
origin=pixel(Vector((0,0,0)))
x=pixel(Vector((1,0,0)))
scale_x=x[0]-origin[0]
target_x=320/5.05
scene.camera.data.ortho_scale*=scale_x/target_x
bpy.context.view_layer.update()
mapping={'origin':pixel(Vector((0,0,0))),'unitX':pixel(Vector((1,0,0))),
         'unitGroundY':pixel(Vector((0,1,0))),'unitHeightZ':pixel(Vector((0,0,1)))}
scene.render.filepath=str(output/'grid-projection.png')
bpy.ops.render.render(write_still=True)
(output/'grid-projection.json').write_text(json.dumps(mapping,indent=2)+'\n')
scene.camera=bpy.data.objects['Camera • character']
scene.render.pixel_aspect_x=scene.render.pixel_aspect_y=1
scene.frame_set(1)
scene.render.filepath=str(output/'hero.png')
# No new save needed: preserve the original editable setup and its camera.
print('CAPTURE_COMPLETE',len(landmarks),json.dumps(mapping))
