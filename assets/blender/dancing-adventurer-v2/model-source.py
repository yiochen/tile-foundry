"""Author the editable dancing adventurer. Run with Blender, never system Python.

blender -b --python tools/blender/build_adventurer.py -- --output assets/blender/dancing-adventurer-v1
The same build() entrypoint can be run in the live Blender MCP session.
"""
import argparse
import json
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

PI = math.pi
CHARACTER = []
RIG = None


def material(name, color, roughness=.65, metal=0, grain=False):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metal
    if grain:
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 75
        noise.inputs['Detail'].default_value = 2
        ramp = nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position = .18
        ramp.color_ramp.elements[0].color = (*(c*.79 for c in color), 1)
        ramp.color_ramp.elements[1].position = .82
        ramp.color_ramp.elements[1].color = (*(min(1,c*1.14) for c in color), 1)
        links.new(noise.outputs['Fac'], ramp.inputs[0])
        links.new(ramp.outputs['Color'], shader.inputs['Base Color'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .07
        bump.inputs['Distance'].default_value = .008
        links.new(noise.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs[0], shader.inputs['Normal'])
    return mat


def finish(obj, mat, bone=None, sub=0):
    obj.data.materials.append(mat)
    if obj.type == 'MESH':
        for face in obj.data.polygons:
            face.use_smooth = True
        if sub:
            mod = obj.modifiers.new('Smooth authored topology', 'SUBSURF')
            mod.levels = mod.render_levels = sub
    CHARACTER.append(obj)
    if bone:
        bind(obj, bone)
    return obj


def bind(obj, bone):
    group = obj.vertex_groups.new(name=bone)
    group.add(list(range(len(obj.data.vertices))), 1, 'REPLACE')
    modifier = obj.modifiers.new('Adventurer skin', 'ARMATURE')
    modifier.object = RIG
    modifier.use_deform_preserve_volume = True
    obj.parent = RIG


def sphere(name, location, scale, mat, bone=None, segments=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=20, location=location)
    obj = bpy.context.object
    obj.name = name
    # Apply coordinates so armature groups are in the common rest space.
    obj.scale = scale
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return finish(obj, mat, bone)


def mesh(name, verts, faces, mat, bone=None, sub=1):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return finish(obj, mat, bone, sub)


def loft(name, rings, mat, bone=None, n=32, sub=1, cap=True):
    """rings = (cx,cy,z,rx,ry). Authored garment/boot cross sections."""
    verts = [(x+rx*math.cos(a*2*PI/n), y+ry*math.sin(a*2*PI/n), z)
             for x,y,z,rx,ry in rings for a in range(n)]
    faces = []
    for j in range(len(rings)-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n
            faces.append((a,b,b+n,a+n))
    if cap:
        faces.extend([tuple(reversed(range(n))),tuple(range((len(rings)-1)*n,len(rings)*n))])
    return mesh(name, verts, faces, mat, bone, sub)


def tube(name, points, radius, mat, bone=None):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.bevel_depth = radius
    data.bevel_resolution = 3
    spline = data.splines.new('BEZIER')
    spline.bezier_points.add(len(points)-1)
    for p,co in zip(spline.bezier_points,points):
        p.co=co;p.handle_left_type=p.handle_right_type='AUTO'
    obj=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active=obj
    obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    obj=bpy.context.object
    obj.select_set(False)
    return finish(obj,mat,bone)


def limb(name, a, b, radii, mat, bone):
    a,b=Vector(a),Vector(b)
    axis=(b-a).normalized()
    u=axis.cross(Vector((0,1,0))).normalized()
    v=axis.cross(u).normalized()
    verts=[];n=24
    for t,ru,rv in radii:
        p=a.lerp(b,t)
        for i in range(n):
            angle=2*PI*i/n
            verts.append(p+u*ru*math.cos(angle)+v*rv*math.sin(angle))
    faces=[]
    for j in range(len(radii)-1):
        for i in range(n):
            x=j*n+i;y=j*n+(i+1)%n
            faces.append((x,y,y+n,x+n))
    faces += [tuple(reversed(range(n))),tuple(range((len(radii)-1)*n,len(radii)*n))]
    return mesh(name,verts,faces,mat,bone)


def skin_chain(name, centers, radii, weights, mat):
    """Continuous joint topology with explicit adjacent-bone blend weights."""
    centers=list(map(Vector,centers));verts=[];n=24
    for j,(point,radius) in enumerate(zip(centers,radii)):
        tangent=(centers[min(j+1,len(centers)-1)]-centers[max(0,j-1)]).normalized()
        u=tangent.cross(Vector((0,1,0))).normalized();v=tangent.cross(u).normalized()
        for i in range(n):
            angle=2*PI*i/n;verts.append(point+u*radius[0]*math.cos(angle)+v*radius[1]*math.sin(angle))
    faces=[]
    for j in range(len(centers)-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;faces.append((a,b,b+n,a+n))
    faces.extend([tuple(reversed(range(n))),tuple(range((len(centers)-1)*n,len(centers)*n))])
    obj=mesh(name,verts,faces,mat,sub=1)
    groups={key:obj.vertex_groups.new(name=key) for key in sorted({key for row in weights for key in row})}
    for j,row in enumerate(weights):
        for key,value in row.items():groups[key].add(list(range(j*n,(j+1)*n)),value,'REPLACE')
    modifier=obj.modifiers.new('Continuous blended skin','ARMATURE');modifier.object=RIG
    modifier.use_deform_preserve_volume=True;obj.parent=RIG
    return obj


def make_rig():
    global RIG
    data=bpy.data.armatures.new('Adventurer skeleton')
    RIG=bpy.data.objects.new('Adventurer • root fixed at ground center',data)
    bpy.context.collection.objects.link(RIG)
    bpy.context.view_layer.objects.active=RIG
    RIG.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    def bone(name,a,b,parent=None):
        bo=data.edit_bones.new(name);bo.head=a;bo.tail=b
        if parent:bo.parent=data.edit_bones[parent]
    bone('root',(0,0,0),(0,0,.24))
    bone('hips',(0,0,1.02),(0,0,1.24),'root')
    bone('spine',(0,0,1.24),(0,0,1.55),'hips')
    bone('chest',(0,0,1.55),(0,0,1.77),'spine')
    bone('neck',(0,0,1.77),(0,0,1.92),'chest')
    bone('head',(0,0,1.92),(0,0,2.58),'neck')
    for side,s in [('L',1),('R',-1)]:
        bone('thigh.'+side,(s*.18,0,1.09),(s*.235,-.035,.63),'hips')
        bone('shin.'+side,(s*.235,-.035,.63),(s*.26,0,.18),'thigh.'+side)
        bone('foot.'+side,(s*.26,0,.18),(s*.26,-.26,.12),'shin.'+side)
        bone('toe.'+side,(s*.26,-.26,.12),(s*.26,-.38,.10),'foot.'+side)
        bone('upper_arm.'+side,(s*.34,0,1.69),(s*.65,-.015,1.43),'chest')
        bone('forearm.'+side,(s*.65,-.015,1.43),(s*.87,-.045,1.19),'upper_arm.'+side)
        bone('hand.'+side,(s*.87,-.045,1.19),(s*.98,-.06,1.06),'forearm.'+side)
        bone('thumb.'+side,(s*.90,-.13,1.16),(s*.94,-.15,1.07),'hand.'+side)
    bpy.ops.object.mode_set(mode='OBJECT')
    RIG.show_in_front=True
    RIG.data.display_type='OCTAHEDRAL'
    RIG.select_set(False)
    return RIG


def build_model():
    skin=material('Skin • warm peach',(.67,.34,.18),.65)
    blush=material('Cheeks • rose',(.64,.22,.15))
    hair=material('Hair • chestnut',(.065,.019,.006),.62,grain=True)
    hair_hi=material('Hair • copper strands',(.11,.039,.011),.62)
    hair_dark=material('Hair • deep parting',(.055,.016,.007),.6)
    blue=material('Tunic • royal blue woven cloth',(.022,.12,.42),.78,grain=True)
    blue_light=material('Tunic • folds and piping',(.044,.205,.59),.76)
    cream=material('Tunic • ivory trim',(.83,.69,.40),.75,grain=True)
    dark=material('Trousers • slate',(.045,.066,.10),.84,grain=True)
    leather=material('Leather • chestnut',(.17,.065,.025),.56,grain=True)
    leather_hi=material('Leather • warm edges',(.30,.13,.048),.62)
    sole=material('Boot • dark sole',(.051,.027,.016),.85)
    brass=material('Buckle • aged brass',(.72,.41,.085),.3,.65)
    white=material('Eyes • warm white',(.91,.92,.84),.3)
    iris=material('Eyes • hazel green',(.105,.19,.102),.32)
    black=material('Eyes and brows • deep umber',(.022,.011,.007),.38)
    mouth=material('Mouth • warm shadow',(.16,.031,.021),.7)

    # Body: an actual garment with flared hem, waist shaping and shoulder slope.
    tunic=loft('Tunic • tailored body',[(0,0,1.00,.34,.225),(0,0,1.025,.35,.23),
        (0,0,1.12,.34,.22),(0,0,1.28,.267,.187),(0,0,1.46,.31,.205),
        (0,0,1.61,.35,.21),(0,0,1.69,.32,.185),(0,0,1.78,.135,.11)],blue)
    # Continuous weights across the torso, rather than independent rigid capsules.
    groups={n:tunic.vertex_groups.new(name=n) for n in ['hips','spine','chest']}
    for vert in tunic.data.vertices:
        z=vert.co.z
        if z<1.25:weights={'hips':1}
        elif z<1.52:
            t=(z-1.25)/.27;weights={'hips':1-t,'spine':t}
        else:
            t=min(1,(z-1.52)/.16);weights={'spine':1-t,'chest':t}
        for key,value in weights.items():groups[key].add([vert.index],value,'REPLACE')
    mod=tunic.modifiers.new('Cloth follows spine','ARMATURE');mod.object=RIG
    mod.use_deform_preserve_volume=True;tunic.parent=RIG
    loft('Ivory hem',[(0,0,1.009,.351,.235),(0,0,1.037,.353,.236),(0,0,1.052,.349,.233)],cream,'hips')
    # V collar rests on the chest, with a short dark opening behind it.
    mesh('V neck opening',[(-.115,-.174,1.744),(0,-.224,1.54),(.115,-.174,1.744)],[(0,1,2)],skin,'chest',0)
    tube('V collar left',[(-.122,-.168,1.76),(-.092,-.198,1.67),(0,-.228,1.54)],.019,cream,'chest')
    tube('V collar right',[(.122,-.168,1.76),(.092,-.198,1.67),(0,-.228,1.54)],.019,cream,'chest')
    for s in [-1,1]:
        tube('Tailored front fold',[(s*.23,-.163,1.62),(s*.18,-.192,1.39),(s*.16,-.202,1.30)],.008,blue_light,'spine')
        tube('Skirt fold',[(s*.17,-.192,1.22),(s*.21,-.199,1.10),(s*.26,-.16,1.053)],.009,blue_light,'hips')
    # Belt with real frame buckle and tongue, not a flat painted rectangle.
    loft('Leather belt',[(0,0,1.227,.282,.201),(0,0,1.239,.289,.207),(0,0,1.324,.285,.205),(0,0,1.336,.278,.20)],leather,'hips')
    tube('Brass buckle frame',[(-.065,-.226,1.242),(-.065,-.226,1.323),(.065,-.226,1.323),(.065,-.226,1.242),(-.065,-.226,1.242)],.014,brass,'hips')
    tube('Buckle tongue',[(0,-.24,1.25),(0,-.24,1.31)],.007,brass,'hips')
    for x in [.10,.145,.19]:sphere('Belt punched hole',(x,-.205,1.283),(.008,.004,.008),sole,'hips',16)
    for s in [-1,1]:
        pouch=sphere('Belt pouch',(s*.305,-.04,1.19),(.10,.115,.145),leather,'hips')
        sphere('Pouch flap',(s*.31,-.123,1.25),(.096,.035,.067),leather_hi,'hips')
        sphere('Pouch button',(s*.31,-.158,1.23),(.019,.009,.019),brass,'hips',16)

    sphere('Neck',(0,0,1.82),(.115,.113,.17),skin,'neck')
    head=sphere('Face • shaped jaw and cheeks',(0,-.005,2.18),(.403,.327,.443),skin,'head',48)
    # Narrow lower jaw and widen the cheeks on the original mesh.
    for vertex in head.data.vertices:
        z=vertex.co.z
        if z<2.08:vertex.co.x*=.78+.22*max(0,(z-1.737)/.343)
    for s in [-1,1]:
        sphere('Ear',(s*.397,-.006,2.16),(.086,.073,.125),skin,'head')
        sphere('Ear inner',(s*.438,-.047,2.16),(.035,.031,.068),blush,'head',24)
        sphere('Cheek tint',(s*.246,-.263,2.07),(.069,.012,.032),blush,'head',24)
        sphere('Eye white',(s*.158,-.302,2.19),(.110,.033,.112),white,'head')
        sphere('Hazel iris',(s*.151,-.332,2.185),(.058,.010,.074),iris,'head')
        sphere('Pupil',(s*.151,-.343,2.185),(.037,.006,.056),black,'head',24)
        sphere('Eye glint',(s*.151-.018,-.350,2.215),(.014,.004,.018),white,'head',16)
        tube('Upper eyelid',[(s*.057,-.309,2.228),(s*.14,-.330,2.286),(s*.25,-.282,2.23)],.013,black,'head')
        tube('Eyebrow',[(s*.066,-.319,2.345),(s*.16,-.326,2.371),(s*.26,-.275,2.33)],.022,hair_dark,'head')
    sphere('Nose bridge',(0,-.317,2.133),(.045,.047,.07),skin,'head')
    sphere('Nose tip',(0,-.355,2.106),(.058,.055,.042),skin,'head')
    tube('Smile',[(-.085,-.301,1.995),(0,-.33,1.974),(.083,-.301,1.999)],.012,mouth,'head')
    sphere('Lower lip',(0,-.312,1.963),(.044,.013,.014),blush,'head',24)

    # Hair cap leaves the face clear. Individual tapered sculpted locks follow
    # curved paths; a raised central ridge gives each lock a broad, shaped volume.
    rings=[]
    for j in range(9):
        phi=.10+j/8*1.65
        rings.append((0,.03,2.20+.46*math.cos(phi),.426*math.sin(phi),.355*math.sin(phi)))
    cap=loft('Hair • shaped crown',rings,hair,'head',48,1)
    # Raise the front hairline; lower rear cap produces a short nape.
    for v in cap.data.vertices:
        if v.co.y<0 and v.co.z<2.38:
            v.co.z=2.38+(v.co.z-2.38)*.25

    def lock(name, control, width, mat):
        a,b,c,d=map(Vector,control);verts=[];n=9;cross=8
        for j in range(n):
            t=j/(n-1)
            p=(1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d
            tangent=(-3*(1-t)**2*a+(3*(1-t)**2-6*t*(1-t))*b+(6*t*(1-t)-3*t*t)*c+3*t*t*d).normalized()
            radial=(p-Vector((0,.025,2.22))).normalized()
            u=tangent.cross(radial).normalized();v=u.cross(tangent).normalized()
            w=width*(.65+.6*math.sin(PI*t))*(1-t)**.65+.001
            for i in range(cross):
                angle=2*PI*i/cross
                verts.append(p+u*w*math.cos(angle)+v*w*.48*math.sin(angle))
        faces=[]
        for j in range(n-1):
            for i in range(cross):
                k=j*cross+i;l=j*cross+(i+1)%cross
                faces.append((k,l,l+cross,k+cross))
        faces.extend([tuple(reversed(range(cross))),tuple(range((n-1)*cross,n*cross))])
        return mesh(name,verts,faces,mat,'head',1)
    rng=random.Random(46)
    # Swept bangs in overlapping layers, asymmetric to avoid a helmet silhouette.
    for i in range(8):
        x=-.34+i*.095
        z=2.37+(.07 if i%3==0 else -.015)
        lock('Hair • swept fringe %02d'%i,[(x*.5,.02,2.65),(x+.10,-.17,2.74),(x+.09,-.39,2.54),(x-.06,-.351,z)],.089 if i%2 else .107,hair_hi if i%3==1 else hair)
    for j in range(7):
        x=-.24+j*.073
        lock('Hair • swept crown',[(x-.12,.15,2.61),(x-.04,.05,2.80),(x+.15,-.15,2.78),(x+.18,-.28,2.58)],.095,hair_hi if j%3==0 else hair)
    for s in [-1,1]:
        for j in range(6):
            t=j/5
            lock('Hair • temple layered lock',[(s*.22,.10+t*.10,2.57),(s*.41,.07-t*.17,2.57),(s*(.46+rng.uniform(0,.035)),-.02-t*.17,2.35),(s*(.36+.04*t),-.08-t*.11,2.14+.10*t)],.082,hair_hi if j%3==1 else hair)
        for j in range(5):
            y=.07+j*.052
            lock('Hair • back tuft',[(s*.14,y,2.58),(s*.35,y+.05,2.50),(s*.43,y,2.29),(s*.32,y+.03,2.13)],.078,hair)

    for side,s in [('L',1),('R',-1)]:
        thigh='thigh.'+side;shin='shin.'+side;foot='foot.'+side
        hip=(s*.18,0,1.09);knee=(s*.235,-.035,.63);ankle=(s*.26,0,.18)
        h,k,a=map(Vector,[hip,knee,ankle])
        skin_chain('Trousers • continuous knee',
            [h+Vector((0,0,.06)),h,h.lerp(k,.5),h.lerp(k,.85),k,k.lerp(a,.16),k.lerp(a,.4),k.lerp(a,.8)],
            [(.10,.10),(.125,.12),(.115,.11),(.10,.10),(.095,.095),(.09,.09),(.083,.083),(.075,.075)],
            [{thigh:1},{thigh:1},{thigh:1},{thigh:.85,shin:.15},{thigh:.5,shin:.5},
             {thigh:.15,shin:.85},{shin:1},{shin:1}],dark)
        # The boot shaft follows the shin; vamp/sole follow a separate foot bone.
        loft('Boot • fitted shaft',[(s*.26,0,.16,.103,.105),(s*.253,-.004,.22,.107,.105),(s*.243,-.02,.48,.116,.113),(s*.24,-.026,.53,.124,.119)],leather,shin)
        loft('Boot • rolled cuff',[(s*.24,-.026,.49,.13,.125),(s*.24,-.026,.535,.137,.131),(s*.24,-.026,.557,.124,.119)],leather_hi,shin)
        loft('Boot • shaped toe and heel',[(s*.26,-.105,.055,.13,.247),(s*.26,-.11,.07,.14,.252),(s*.26,-.11,.13,.143,.254),(s*.26,-.082,.20,.126,.211),(s*.26,-.015,.255,.104,.13)],leather,foot)
        loft('Boot • sole',[(s*.26,-.11,0,.137,.255),(s*.26,-.11,.025,.146,.261),(s*.26,-.11,.065,.145,.260)],sole,foot)
        tube('Boot • welt',[(s*.26-.13,-.20,.077),(s*.26-.08,-.35,.077),(s*.26+.08,-.35,.077),(s*.26+.13,-.20,.077)],.008,leather_hi,foot)
        tube('Boot • front seam',[(s*.24,-.148,.49),(s*.25,-.123,.29),(s*.26,-.20,.20)],.007,leather_hi,shin)
        for z in [.29,.36,.43]:
            tube('Boot lace',[(s*.26-.032,-.126,z),(s*.26+.032,-.126,z+.018)],.006,cream,shin)

        a=(s*.34,0,1.69);b=(s*.65,-.015,1.43);c=(s*.87,-.045,1.19)
        upper='upper_arm.'+side;fore='forearm.'+side;hand='hand.'+side
        av,bv,cv=map(Vector,[a,b,c])
        skin_chain('Tunic • continuous shoulder',
            [(s*.235,0,1.65),av,av.lerp(bv,.20),av.lerp(bv,.5),av.lerp(bv,.83),av.lerp(bv,.90)],
            [(.13,.14),(.145,.15),(.154,.147),(.14,.137),(.122,.12),(.12,.12)],
            [{'chest':1},{'chest':.5,upper:.5},{upper:1},{upper:1},{upper:1},{upper:1}],blue)
        limb('Ivory sleeve cuff',a,b,[(.78,.127,.125),(.82,.134,.132),(.9,.128,.125),(.94,.12,.119)],cream,upper)
        skin_chain('Arm • continuous elbow',
            [av.lerp(bv,.45),av.lerp(bv,.75),av.lerp(bv,.9),bv,bv.lerp(cv,.15),bv.lerp(cv,.6),cv],
            [(.094,.093),(.093,.092),(.09,.09),(.09,.09),(.095,.09),(.086,.08),(.067,.067)],
            [{upper:1},{upper:1},{upper:.85,fore:.15},{upper:.5,fore:.5},{upper:.15,fore:.85},{fore:1},{fore:1}],skin)
        # Leather wrist wrap and a modeled curled fist (four knuckles and thumb).
        limb('Leather wrist wrap',b,c,[(.79,.078,.079),(.82,.083,.083),(.98,.076,.078),(1.01,.071,.074)],leather,fore)
        sphere('Hand • palm',(s*.938,-.048,1.105),(.106,.082,.113),skin,hand)
        for i in range(4):
            x=s*(.886+i*.032)
            sphere('Hand • curled finger',(x,-.103,1.102-i*.008),(.032,.044,.066),skin,hand,20)
            tube('Finger crease',[(x-.009,-.141,1.095-i*.008),(x+.008,-.141,1.090-i*.008)],.0027,blush,hand)
        sphere('Hand • thumb',(s*.90,-.132,1.16),(.045,.047,.071),skin,'thumb.'+side,24)


def animate():
    # IK goals are world-space and are NOT parented to hips. Feet stay planted.
    def target(name,loc):
        obj=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(obj)
        obj.location=loc;obj.empty_display_size=.08;obj.empty_display_type='SPHERE'
        return obj
    hand_goals={};foot_goals={};hand_rest={}
    for side,s in [('L',1),('R',-1)]:
        ankle=target('CTRL • planted ankle '+side,(s*.26,0,.18))
        pole=target('CTRL • knee pole '+side,(s*.26,-1.2,.65))
        ik=RIG.pose.bones['shin.'+side].constraints.new('IK')
        ik.target=ankle;ik.pole_target=pole;ik.chain_count=2;ik.pole_angle=-PI/2
        foot=RIG.pose.bones['foot.'+side]
        # Preserve the original foot orientation in world space under leg IK.
        rotation=target('CTRL • fixed sole orientation '+side,(s*.26,0,.18))
        rotation.rotation_euler=RIG.data.bones[foot.name].matrix_local.to_euler()
        con=foot.constraints.new('COPY_TRANSFORMS');con.target=rotation
        con.owner_space='WORLD';con.target_space='WORLD'
        foot_goals[side]=ankle
        hand=target('CTRL • fist '+side,(s*.72,-.16,1.94))
        elbow=target('CTRL • elbow pole '+side,(s*1.5,.15,1.6))
        ik=RIG.pose.bones['forearm.'+side].constraints.new('IK')
        ik.target=hand;ik.pole_target=elbow;ik.chain_count=2;ik.pole_angle=PI/2
        # Both elbows now point outward. The old -90° setting folded them
        # inward across the chest even though the wrist targets were correct.
        hand_goals[side]=hand
        hand.rotation_mode='QUATERNION'
        rest=RIG.data.bones['hand.'+side].matrix_local.to_3x3()
        y=rest.col[1].normalized();normal=Vector((0,-1,0))
        normal=(normal-y*normal.dot(y)).normalized()
        hand_rest[side]=(Matrix((y.cross(normal),y,normal)).transposed(),rest)
        con=RIG.pose.bones['hand.'+side].constraints.new('COPY_ROTATION')
        con.target=hand;con.owner_space='WORLD';con.target_space='WORLD'
    # Two second loop with two accents and subtle secondary head/chest motion.
    for frame in range(1,26):
        bpy.context.scene.frame_set(frame)
        phase=2*PI*(frame-1)/24
        sway=math.sin(phase)
        hips=RIG.pose.bones['hips'];hips.rotation_mode='XYZ'
        hips.location=(.035*sway,-.035*(1-math.cos(phase*2)),0)
        hips.rotation_euler=(0,.035*sway,-.045*sway)
        hips.keyframe_insert('location',frame=frame);hips.keyframe_insert('rotation_euler',frame=frame)
        chest=RIG.pose.bones['chest'];chest.rotation_mode='XYZ'
        chest.rotation_euler=(.025*math.sin(phase*2),.035*sway,.065*sway)
        chest.keyframe_insert('rotation_euler',frame=frame)
        head=RIG.pose.bones['head'];head.rotation_mode='XYZ'
        head.rotation_euler=(-.025*math.sin(phase*2),-.065*sway,-.075*sway)
        head.keyframe_insert('rotation_euler',frame=frame)
        for side,s in [('L',1),('R',-1)]:
            goal=hand_goals[side]
            goal.location=(s*(.53+.025*math.cos(phase)), -.18+.035*s*sway,1.94+s*.12*sway+.04*math.cos(phase*2))
            goal.keyframe_insert('location',frame=frame)
            bpy.context.view_layer.update()
            forearm=RIG.pose.bones['forearm.'+side]
            y=(forearm.tail-forearm.head).normalized();normal=Vector((0,-1,0))
            normal=(normal-y*normal.dot(y)).normalized()
            desired=Matrix((y.cross(normal),y,normal)).transposed()
            source,rest=hand_rest[side]
            goal.rotation_quaternion=(desired@source.transposed()@rest).to_quaternion()
            goal.keyframe_insert('rotation_quaternion',frame=frame)
    bpy.context.scene.frame_start=1;bpy.context.scene.frame_end=24
    bpy.context.scene.render.fps=12
    bpy.context.scene.frame_set(1)


def camera(name,elevation=35,anamorphic=False):
    data=bpy.data.cameras.new(name);obj=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    angle=math.radians(elevation)
    obj.location=(0,-10*math.cos(angle),10*math.sin(angle))
    obj.rotation_euler=(-obj.location).to_track_quat('-Z','Y').to_euler()
    data.type='ORTHO';data.ortho_scale=5.05;data.shift_y=.275
    obj['projection_profile']='square top/front affine' if anamorphic else 'character orthographic 35 degrees'
    return obj


def setup_scene():
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.samples=32
    scene.cycles.use_denoising=True
    scene.render.resolution_x=768;scene.render.resolution_y=1280
    scene.render.resolution_percentage=100
    scene.render.film_transparent=True
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.world.color=(.35,.35,.35)
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.62,.71,.85,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.38
    def light(name,loc,power,size,color):
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=loc
        obj.rotation_euler=(Vector((0,0,1.4))-obj.location).to_track_quat('-Z','Y').to_euler()
    light('Key • soft upper left',(-3,-4,6),500,4,(1,.82,.64))
    light('Fill • cool front',(3,-2,3),230,3,(.66,.80,1))
    light('Rim • warm crown',(1,2,5),650,3,(1,.76,.48))
    scene.camera=camera('Camera • character',35)
    camera('Camera • grid comparison',45,True)
    scene['ground_anchor_px']=[96,248]
    scene['logical_footprint_px']=[128,128]
    scene['frame_px']=[192,320]
    scene['source']='Authored Blender mesh, materials, armature and keyframes; no imagegen'
    return scene


def build(output):
    global CHARACTER
    CHARACTER=[]
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    make_rig();build_model();animate();scene=setup_scene()
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    bpy.context.view_layer.update()
    p=world_to_camera_view(scene,scene.camera,Vector((0,0,0)))
    print('GROUND_PIXEL',p.x*192,(1-p.y)*320)
    # Set an inviting camera view when the editable file opens.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA'
                area.spaces.active.overlay.show_overlays=False
                area.spaces.active.shading.type='MATERIAL'
    bpy.ops.object.select_all(action='DESELECT')
    RIG.select_set(True);bpy.context.view_layer.objects.active=RIG
    scene.render.filepath=str(output/'hero.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'dancing-adventurer.blend'))
    metadata={'blender':bpy.app.version_string,'fps':12,'frames':24,'durationSeconds':2,
        'frameSize':[192,320],'captureSize':[768,1280],'anchor':[96,248],
        'actualProjectedRoot':[p.x*192,(1-p.y)*320], 'logicalFootprint':[128,128],
        'projection':{'type':'orthographic','elevationDegrees':35,'orthoScale':scene.camera.data.ortho_scale,'shiftY':scene.camera.data.shift_y,'pixelAspect':[1,1]},
        'rig':{'bones':len(RIG.data.bones),'root':[0,0,0],'feet':'world-space leg IK and fixed sole transform constraints'},
        'camera':{'type':'orthographic','elevationDegrees':35,
            'worldMatrix':[list(r) for r in scene.camera.matrix_world],
            'projectionMatrix':[list(r) for r in scene.camera.calc_matrix_camera(bpy.context.evaluated_depsgraph_get(),x=768,y=1280)],
            'worldUnitsPerLogicalCell':128/(320/scene.camera.data.ortho_scale),'pixelAspect':[1,1]},
        'meshes':sum(o.type=='MESH' for o in CHARACTER),'vertices':sum(len(o.data.vertices) for o in CHARACTER),
        'aiCalls':0,'status':'authored 3D prototype, not a scored eval or final AI reskin'}
    (output/'capture.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print('ADVENTURER_SAVED',str(output),json.dumps(metadata))
    return scene


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    parser.add_argument('--render',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    scene=build(args.output)
    if args.render:bpy.ops.render.render(write_still=True)
