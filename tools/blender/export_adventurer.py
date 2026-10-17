"""Optional GLB for inspection. The .blend retains native procedural materials."""
import bpy
from pathlib import Path
import sys

output=Path(sys.argv[sys.argv.index('--')+1]).resolve()
# glTF cannot serialize Blender Noise -> ColorRamp -> Bump graphs. Export their
# deliberately authored base colors, rather than the exporter's white fallback.
# This background export does not save or alter the native .blend materials.
for mat in bpy.data.materials:
    if not mat.use_nodes:continue
    shader=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if shader:
        for name in ['Base Color','Normal']:
            for link in list(shader.inputs[name].links):mat.node_tree.links.remove(link)
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.context.scene.objects:
    if obj.type in {'MESH','ARMATURE','EMPTY'}:obj.select_set(True)
scene=bpy.context.scene
end=scene.frame_end
scene.frame_end=25  # matching closing key at t=2s; capture only the 24 unique poses
bpy.ops.export_scene.gltf(filepath=str(output/'dancing-adventurer.glb'),export_format='GLB',
    use_selection=True,export_animations=True,export_frame_range=True,
    export_force_sampling=True,export_animation_mode='SCENE',export_skins=True,
    export_anim_slide_to_zero=True,export_anim_scene_split_object=False)
scene.frame_end=end
print('GLB_COMPLETE')
