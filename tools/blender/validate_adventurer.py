"""Validate the authored rig; visual screenshots remain necessary for anatomy."""
import bpy
import json
import math
from pathlib import Path
import sys

output=Path(sys.argv[sys.argv.index('--')+1]).resolve()
(output/'validation').mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene
rig=next(o for o in scene.objects if o.type=='ARMATURE')
checks={'frames':24,'fps':scene.render.fps,'unweightedVertices':0,'badWeightSums':0,
        'minimumOutwardElbowDistance':float('inf'),'maximumWristBendDegrees':0,
        'maximumHandGoalErrorWorld':0,'footMatrixMaximumDelta':0}
for obj in scene.objects:
    if obj.type!='MESH':continue
    groups={g.index for g in obj.vertex_groups if g.name in rig.data.bones}
    for vert in obj.data.vertices:
        total=sum(g.weight for g in vert.groups if g.group in groups)
        checks['unweightedVertices']+=total<1e-6
        checks['badWeightSums']+=abs(total-1)>1e-5
first_feet={};first_bones={}
for frame in range(1,26):
    scene.frame_set(frame);bpy.context.view_layer.update()
    for side,s in [('L',1),('R',-1)]:
        upper=rig.pose.bones['upper_arm.'+side]
        fore=rig.pose.bones['forearm.'+side];hand=rig.pose.bones['hand.'+side]
        outward=s*(upper.tail.x-upper.head.x)
        checks['minimumOutwardElbowDistance']=min(checks['minimumOutwardElbowDistance'],outward)
        angle=(fore.tail-fore.head).angle(hand.tail-hand.head)
        checks['maximumWristBendDegrees']=max(checks['maximumWristBendDegrees'],math.degrees(angle))
        goal=bpy.data.objects['CTRL • fist '+side]
        checks['maximumHandGoalErrorWorld']=max(checks['maximumHandGoalErrorWorld'],(fore.tail-goal.location).length)
        matrix=rig.pose.bones['foot.'+side].matrix.copy()
        if frame==1:first_feet[side]=matrix
        checks['footMatrixMaximumDelta']=max(checks['footMatrixMaximumDelta'],max(abs(a-b) for row,ref in zip(matrix,first_feet[side]) for a,b in zip(row,ref)))
    if frame==1:first_bones={b.name:b.matrix.copy() for b in rig.pose.bones}
    if frame==25:checks['closingKeyMatrixMaximumDelta']=max(abs(a-b) for bone in rig.pose.bones for row,ref in zip(bone.matrix,first_bones[bone.name]) for a,b in zip(row,ref))
assert checks['unweightedVertices']==checks['badWeightSums']==0,checks
assert checks['minimumOutwardElbowDistance']>.1,checks
assert checks['maximumWristBendDegrees']<.1,checks
assert checks['footMatrixMaximumDelta']<1e-6,checks
assert checks['closingKeyMatrixMaximumDelta']<1e-4,checks
scene.frame_set(1)
(output/'validation/rig-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print('RIG_VALIDATION',json.dumps(checks))
