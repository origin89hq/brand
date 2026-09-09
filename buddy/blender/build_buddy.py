"""Build an editable, layered bipedal Buddy moose concept in Blender.

Anatomy is a stylized construction study, not a specimen reconstruction.
Shared landmarks drive the skeleton, muscle envelopes, skin and pose rig.
Run: Blender --background --python build_buddy.py
"""
from pathlib import Path
import sys, math, json, hashlib
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT.parent
sys.path.insert(0, str(BRAND / 'buddy/blender'))
from fur import hair_material, attachment_atlas, UV_NAME
sys.path.insert(0,str(Path(__file__).resolve().parent))
from dental import arch as dental_arch, incisor_mesh
from surface_detail import install_muzzle_detail, face_warmth
from proportions import BODY_RATIO, BODY_JOIN, LEG_RATIO, LEG_DROP, HEAD_OFFSET, height as compact_height, design_height

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = 'Buddy | layered character'
scene.unit_settings.system = 'METRIC'
scene['coat_brown']=1.
scene.id_properties_ui('coat_brown').update(min=0.,max=1.,description='Coat palette: 0 = navy, 1 = warm brown. Blends both skin and native fur.')
COLS = {}
for name in ['Skeleton', 'Organs', 'Muscles', 'Skin', 'Features', 'Antlers', 'Fur', 'Rig', 'Shell', 'Studio']:
    col = bpy.data.collections.new(name)
    scene.collection.children.link(col)
    COLS[name] = col

def color(hex):
    a = [int(hex[i:i+2], 16)/255 for i in (1,3,5)]
    return tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in a) + (1,)

def material(name, hex, rough=.6, noise=0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = color(hex)
    p.inputs['Roughness'].default_value = rough
    m.diffuse_color = color(hex)
    if noise:
        n = m.node_tree.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 170
        bump = m.node_tree.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .18; bump.inputs['Distance'].default_value = noise
        m.node_tree.links.new(n.outputs['Fac'], bump.inputs['Height'])
        m.node_tree.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    return m

M = {
    'bone': material('Bone | warm ivory', '#d6c7a4', .65),
    'cartilage': material('Cartilage | blue green', '#669fa1', .54),
    'muscle': material('Muscle | muted terracotta', '#a75c51', .7),
    'organ': material('Organ | ochre volume', '#ba955e', .7),
    'lung': material('Lungs | muted rose', '#b58081', .65),
    'heart': material('Heart | deep red', '#923e43', .6),
    'liver': material('Liver | umber', '#794d3b', .65),
    'kidney': material('Kidneys | muted plum', '#815d74', .6),
    'skin': material('Coat foundation | navy to slate', '#203652', .72, .0008),
    'ear': material('Ear interior | slate velvet', '#5f6b76', .8, .0004),
    'eye': material('Eye | deep warm brown', '#221710', .15),
    'iris': material('Iris | warm hazel', '#79512b', .23),
    'pupil': material('Pupil | soft black', '#080d14', .12),
    'lid': material('Eyelid | deep navy', '#172337', .67),
    'mouth': material('Mouth and nasal cavity | deep slate', '#0b111a', .65),
    'nostril': material('Nostril | warm recessed skin', '#241b17', .52, .0003),
    'hoof': material('Hooves | charcoal horn', '#352b24', .58, .0007),
    'antler': material('Antlers | dry textured bone', '#927a57', .65, .0009),
    'tooth': material('Teeth | natural ivory', '#d8ceb5', .45),
    'clay': material('Clay | cool porcelain', '#bcc8d0', .72),
}
for mat in M.values(): mat.use_fake_user=True
M['hoof'].node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.25
M['hoof_sole']=material('Hooves | worn matte sole','#292119',.88,.0008)
M['hoof_sole'].node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.08
M['antler'].node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.30
# Antler coloration follows the growth from darker bases to pale tapered tips.
nodes=M['antler'].node_tree.nodes; links=M['antler'].node_tree.links
position=nodes.new('ShaderNodeTexCoord'); separate=nodes.new('ShaderNodeSeparateXYZ')
links.new(position.outputs['Generated'],separate.inputs[0])
height=nodes.new('ShaderNodeMapRange'); height.inputs['From Min'].default_value=0.; height.inputs['From Max'].default_value=1.
links.new(separate.outputs['Z'],height.inputs['Value'])
ramp=nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color=color('#6b543b'); ramp.color_ramp.elements[1].color=color('#b9a17b')
ramp.color_ramp.elements.new(.46).color=color('#967b55')
links.new(height.outputs[0],ramp.inputs[0])
tex=nodes.new('ShaderNodeTexCoord'); stretch=nodes.new('ShaderNodeVectorMath'); stretch.operation='MULTIPLY'; stretch.inputs[1].default_value=(150,40,7)
links.new(tex.outputs['Generated'],stretch.inputs[0])
grain=nodes.new('ShaderNodeTexNoise'); grain.inputs['Scale'].default_value=1.; grain.inputs['Detail'].default_value=3.
links.new(stretch.outputs[0],grain.inputs['Vector'])
range_node=nodes.new('ShaderNodeMapRange'); range_node.inputs['To Min'].default_value=.58; range_node.inputs['To Max'].default_value=1.12
links.new(grain.outputs['Fac'],range_node.inputs['Value'])
grain_color=nodes.new('ShaderNodeMixRGB'); grain_color.blend_type='MULTIPLY'; grain_color.inputs[0].default_value=1.
links.new(ramp.outputs[0],grain_color.inputs[1]); links.new(range_node.outputs[0],grain_color.inputs[2]); links.new(grain_color.outputs[0],nodes.get('Principled BSDF').inputs['Base Color'])
grain_bump=nodes.new('ShaderNodeBump'); grain_bump.inputs['Strength'].default_value=.50; grain_bump.inputs['Distance'].default_value=.006
links.new(grain.outputs['Fac'],grain_bump.inputs['Height'])
pores=nodes.new('ShaderNodeTexNoise'); pores.inputs['Scale'].default_value=320.; pores.inputs['Detail'].default_value=3.
links.new(tex.outputs['Generated'],pores.inputs['Vector'])
pore_bump=nodes.new('ShaderNodeBump'); pore_bump.inputs['Strength'].default_value=.30; pore_bump.inputs['Distance'].default_value=.0015
links.new(pores.outputs['Fac'],pore_bump.inputs['Height']); links.new(grain_bump.outputs['Normal'],pore_bump.inputs['Normal']); links.new(pore_bump.outputs['Normal'],nodes.get('Principled BSDF').inputs['Normal'])
def palette_driver(owner,path,index=None,a=0.,b=1.):
    fc=owner.driver_add(path) if index is None else owner.driver_add(path,index)
    driver=fc.driver; driver.expression=f'{a}+(v*({b-a}))'
    variable=driver.variables.new(); variable.name='v'; variable.type='SINGLE_PROP'
    target=variable.targets[0]; target.id_type='SCENE'; target.id=scene; target.data_path='["coat_brown"]'
nodes=M['skin'].node_tree.nodes; links=M['skin'].node_tree.links
attr=nodes.new('ShaderNodeVertexColor'); attr.layer_name='coat_color'
brownattr=nodes.new('ShaderNodeVertexColor'); brownattr.layer_name='coat_color_brown'
mix=nodes.new('ShaderNodeMixRGB'); mix.name='Palette | navy to warm brown'
links.new(attr.outputs['Color'],mix.inputs[1]); links.new(brownattr.outputs['Color'],mix.inputs[2])
palette_driver(mix.inputs[0],'default_value')
links.new(mix.outputs[0], nodes.get('Principled BSDF').inputs['Base Color'])
for name,blue,brown in [('ear','#5f6b76','#927963'),('lid','#172337','#433328')]:
    socket=M[name].node_tree.nodes['Principled BSDF'].inputs['Base Color']
    for i,(a,b) in enumerate(zip(color(blue)[:3],color(brown)[:3])): palette_driver(socket,'default_value',i,a,b)
# A single smooth corneal surface avoids stacked, protruding iris/pupil meshes.
nodes=M['eye'].node_tree.nodes; links=M['eye'].node_tree.links
tc=nodes.new('ShaderNodeTexCoord'); sep=nodes.new('ShaderNodeSeparateXYZ'); links.new(tc.outputs['Generated'],sep.inputs[0])
components=[]
for axis in ('X','Z'):
    sub=nodes.new('ShaderNodeMath'); sub.operation='SUBTRACT'; sub.inputs[1].default_value=.5; links.new(sep.outputs[axis],sub.inputs[0])
    sq=nodes.new('ShaderNodeMath'); sq.operation='MULTIPLY'; links.new(sub.outputs[0],sq.inputs[0]); links.new(sub.outputs[0],sq.inputs[1]); components.append(sq)
add=nodes.new('ShaderNodeMath'); add.operation='ADD'
for i,node in enumerate(components): links.new(node.outputs[0],add.inputs[i])
rt=nodes.new('ShaderNodeMath'); rt.operation='SQRT'; links.new(add.outputs[0],rt.inputs[0])
ramp=nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
ramp.color_ramp.elements[0].position=0.; ramp.color_ramp.elements[0].color=color('#090e14')
for pos,c in [(.24,'#0a0e14'),(.265,'#4e311a'),(.40,'#604124'),(.455,'#241c16'),(.50,'#11151b')]:
    ramp.color_ramp.elements.new(pos).color=color(c)
links.new(rt.outputs[0],ramp.inputs[0]); links.new(ramp.outputs[0],nodes.get('Principled BSDF').inputs['Base Color'])
nodes.get('Principled BSDF').inputs['Roughness'].default_value=.22
nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.28

def move(obj, col):
    for old in list(obj.users_collection): old.objects.unlink(obj)
    COLS[col].objects.link(obj)
    return obj

def active(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True); bpy.context.view_layer.objects.active=obj

def smooth(obj):
    for p in obj.data.polygons: p.use_smooth=True
    return obj

def ellipsoid(name, loc, scale, mat, col, direction=None, segments=40):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=24, location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale
    if direction is not None: o.rotation_euler=Vector(direction).to_track_quat('Z','Y').to_euler()
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    move(o,col)
    if mat: o.data.materials.append(mat)
    return smooth(o)

def rail(name, points, radius, mat, col, cyclic=False):
    c=bpy.data.curves.new(name,'CURVE'); c.dimensions='3D'; c.resolution_u=16
    c.bevel_depth=radius; c.bevel_resolution=4
    s=c.splines.new('BEZIER'); s.bezier_points.add(len(points)-1); s.use_cyclic_u=cyclic
    for b,p in zip(s.bezier_points,points):
        b.co=p; b.handle_left_type=b.handle_right_type='AUTO'
    o=bpy.data.objects.new(name,c); COLS[col].objects.link(o); c.materials.append(mat)
    return o

def tube(name,a,b,r,mat,col):
    a,b=Vector(a),Vector(b)
    return ellipsoid(name,(a+b)/2,(r,r,(b-a).length/2+r*.35),mat,col,b-a,32)

def loft(name, controls, mat, col, axis='Z'):
    """Smooth cross sections give the silhouette a single continuous contour."""
    controls=np.asarray(controls,dtype=float); sections=[]
    for i in range(len(controls)-1):
        a,b,c,d=controls[max(0,i-1)],controls[i],controls[i+1],controls[min(len(controls)-1,i+2)]
        for t in np.linspace(0,1,7,endpoint=False):
            sections.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    sections.append(controls[-1]); vertices=[]; faces=[]; around=64
    for along,cross1,cross2,r1,r2 in sections:
        for a in np.linspace(0,2*math.pi,around,endpoint=False):
            p=(cross1+max(.003,r1)*math.cos(a),cross2+max(.003,r2)*math.sin(a))
            vertices.append((p[0],p[1],along) if axis=='Z' else (p[0],along,p[1]))
    for j in range(len(sections)-1):
        for i in range(around):
            a=j*around+i; b=j*around+(i+1)%around
            faces.append((a,b,b+around,a+around))
    faces.extend([tuple(reversed(range(around))),tuple((len(sections)-1)*around+i for i in range(around))])
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(vertices,[],faces); mesh.update()
    bm=bmesh.new(); bm.from_mesh(mesh); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
    mesh.materials.append(mat); obj=bpy.data.objects.new(name,mesh); COLS[col].objects.link(obj)
    return smooth(obj)

def sweep(name, points, radii, mat, col):
    """A curved taper for antler beams and tines, with rounded small tips."""
    controls=np.array([(*p,r) for p,r in zip(points,radii)],dtype=float); sections=[]
    for i in range(len(controls)-1):
        a,b,c,d=controls[max(0,i-1)],controls[i],controls[i+1],controls[min(len(controls)-1,i+2)]
        for t in np.linspace(0,1,9,endpoint=False):
            sections.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    sections.append(controls[-1]); vertices=[]; faces=[]; around=32
    for i,section in enumerate(sections):
        center=Vector(section[:3]); tangent=Vector(sections[min(i+1,len(sections)-1)][:3])-Vector(sections[max(0,i-1)][:3]); tangent.normalize()
        u=tangent.cross(Vector((0,1,0))).normalized(); v=tangent.cross(u).normalized()
        for angle in np.linspace(0,2*math.pi,around,endpoint=False):
            vertices.append(center+float(max(.004,section[3]))*(u*math.cos(angle)+v*math.sin(angle)))
    for j in range(len(sections)-1):
        for i in range(around):
            a=j*around+i; b=j*around+(i+1)%around; faces.append((a,b,b+around,a+around))
    faces.extend([tuple(reversed(range(around))),tuple((len(sections)-1)*around+i for i in range(around))])
    me=bpy.data.meshes.new(name); me.from_pydata(vertices,[],faces); me.update()
    bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(me); bm.free()
    me.materials.append(mat); obj=bpy.data.objects.new(name,me); COLS[col].objects.link(obj); return smooth(obj)

def join_remesh(name, objects, col, voxel=.025, iterations=5):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects: o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]; bpy.ops.object.join()
    o=objects[0]; o.name=name
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    m=o.modifiers.new('Continuous sculpt surface','REMESH'); m.mode='VOXEL'; m.voxel_size=voxel; m.use_smooth_shade=True
    bpy.ops.object.modifier_apply(modifier=m.name)
    m=o.modifiers.new('Relax anatomical transitions','SMOOTH'); m.factor=1.; m.iterations=iterations
    bpy.ops.object.modifier_apply(modifier=m.name)
    move(o,col); return smooth(o)

def cut(o, cutter, solver='EXACT'):
    active(o); mod=o.modifiers.new('Recessed anatomical opening','BOOLEAN')
    mod.operation='DIFFERENCE'; mod.solver=solver; mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)

# Upright design coordinates. Front faces -Y; anatomical left is +X.
BONES = {
 'root':((0,0,.10),(0,0,.40),None),
 'pelvis':((0,.06,1.01),(0,.07,1.31),'root'),
 'spine.lower':((0,.07,1.31),(0,.09,1.57),'pelvis'),
 'spine.upper':((0,.09,1.57),(0,.14,1.93),'spine.lower'),
 'neck':((0,.14,1.93),(0,.02,2.26),'spine.upper'),
 'head':((0,.02,2.26),(0,-.08,2.73),'neck'),
 'jaw':((0,-.015,2.30),(0,-.80,2.035),'head'),
 'tail':((0,.29,1.12),(0,.55,.94),'pelvis'),
}
for side,s in [('L',1),('R',-1)]:
    BONES.update({
      f'upper_arm.{side}':((s*.375,.04,1.86),(s*.59,.065,1.57),'spine.upper'),
      f'forearm.{side}':((s*.59,.065,1.57),(s*.64,-.18,1.32),f'upper_arm.{side}'),
      f'hand.{side}':((s*.64,-.18,1.32),(s*.64,-.21,1.17),f'forearm.{side}'),
      f'thigh.{side}':((s*.26,.05,1.15),(s*.30,-.10,.75),'pelvis'),
      f'shin.{side}':((s*.30,-.10,.75),(s*.33,.045,.34),f'thigh.{side}'),
      f'foot.{side}':((s*.33,.045,.34),(s*.33,-.13,.135),f'shin.{side}'),
      f'ear.{side}':((s*.34,.025,2.69),(s*.76,.06,2.90),'head'),
    })

data=bpy.data.armatures.new('Moose | anatomical pose skeleton')
rig=bpy.data.objects.new('Buddy | pose rig',data); COLS['Rig'].objects.link(rig)
active(rig); bpy.ops.object.mode_set(mode='EDIT')
joint_locations=set()
for name,(a,b,parent) in BONES.items():
    bone=data.edit_bones.new(name); bone.head=a; bone.tail=b
    if parent: bone.parent=data.edit_bones[parent]
    bone.use_deform=name!='root'
bpy.ops.object.mode_set(mode='OBJECT'); rig.show_in_front=True; data.display_type='OCTAHEDRAL'
rig['anatomy']='Designed biped; ungulate head, cloven hooves, lifted hocks, adapted upright pelvis and shoulders.'
rig['poses']=json.dumps({'standing':1,'explaining':40,'step':80})

def bind_rigid(o, bone):
    bpy.context.view_layer.update(); world=o.matrix_world.copy()
    o.parent=rig; o.parent_type='BONE'; o.parent_bone=bone
    bpy.context.view_layer.update(); o.matrix_world=world
    o['support_bone']=bone
    return o

# Renderable bone anatomy is independent from Blender's control-bone display.
for name,(a,b,parent) in BONES.items():
    if name in ('root','head','jaw','tail') or name.startswith('ear'): continue
    r=.043 if name.startswith(('spine','neck','pelvis')) else .029
    bind_rigid(tube('Bone | '+name,a,b,r,M['bone'],'Skeleton'),name)
    for suffix,p in [('proximal',a),('distal',b)]:
        key=tuple(round(c,5) for c in p)
        if key in joint_locations: continue
        joint_locations.add(key)
        bind_rigid(ellipsoid('Joint | '+name+' '+suffix,p,(r*1.4,)*3,M['bone'],'Skeleton',segments=24),name)

for side,s in [('L',1),('R',-1)]:
    bind_rigid(ellipsoid('Bone | iliac wing '+side,(s*.21,.12,1.15),(.13,.07,.18),M['bone'],'Skeleton'), 'pelvis')
    bind_rigid(ellipsoid('Bone | scapula '+side,(s*.29,.12,1.78),(.115,.065,.18),M['bone'],'Skeleton'), 'spine.upper')
    for j in range(10):
        z=1.38+j*.050; rx=.23+.095*math.sin(j/9*math.pi)
        points=[(s*.035,.18,z+.045),(s*rx,.12,z),(s*(rx+.015),-.10,z-.07),(s*.12,-.27,z-.10),(s*.018,-.285,z-.08)]
        bind_rigid(rail(f'Bone | rib {j+1:02} {side}',points,.013,M['bone'],'Skeleton'), 'spine.upper' if j>3 else 'spine.lower')
    for j in (-1,1):
        bind_rigid(tube(f'Bone | terminal hoof digit {side} {j}',(s*.33+j*.05,-.04,.18),(s*.33+j*.055,-.20,.095),.024,M['bone'],'Skeleton'),f'foot.{side}')
        bind_rigid(tube(f'Bone | hand digit {side} {j}',(s*.64+j*.040,-.18,1.27),(s*.64+j*.042,-.21,1.18),.019,M['bone'],'Skeleton'),f'hand.{side}')
bind_rigid(rail('Bone | sternum',[(0,-.28,1.35),(0,-.29,1.60),(0,-.25,1.77)],.025,M['bone'],'Skeleton'),'spine.upper')

# Long rostrum, shortened nasal roof, open orbits and independently hinged jaw.
skull_parts=[ellipsoid('Cranium',(0,.0,2.53),(.30,.275,.335),M['bone'],'Skeleton')]
for s in (-1,1):
    skull_parts.append(tube('Maxilla',(s*.18,-.09,2.44),(s*.16,-.71,2.23),.105,M['bone'],'Skeleton'))
skull=join_remesh('Bone | cranium and paired maxillae',skull_parts,'Skeleton',.016,3)
for s in (-1,1):
    cut(skull,ellipsoid('Orbit cutter',(s*.268,-.16,2.56),(.145,.17,.15),None,'Skeleton'))
bind_rigid(skull,'head')
for side,s in [('L',1),('R',-1)]:
    bind_rigid(tube('Bone | antler pedicle '+side,(s*.20,.055,2.75),(s*.27,.055,2.94),.051,M['bone'],'Skeleton'),'head')
    points=[(s*.28,-.01,2.49),(s*.31,-.16,2.46),(s*.23,-.40,2.35)]
    bind_rigid(rail('Bone | zygomatic arch '+side,points,.029,M['bone'],'Skeleton'),'head')
    bind_rigid(tube('Bone | short nasal roof '+side,(s*.08,-.20,2.66),(s*.075,-.55,2.43),.055,M['bone'],'Skeleton'),'head')
    points=[(s*.24,-.01,2.31),(s*.255,-.05,2.17),(s*.22,-.35,2.07),dental_arch(s*math.radians(60)),dental_arch(s*math.radians(10))]
    bind_rigid(rail('Bone | mandible '+side,points,.044,M['bone'],'Skeleton'),'jaw')
    for row,z,owner in [('upper',2.235,'head'),('lower',2.14,'jaw')]:
        for i in range(5):
            tooth=ellipsoid(f'Tooth | {row} cheek {side} {i}',(s*.18,-.23-i*.064,z),(.039,.033,.034),M['tooth'],'Skeleton',segments=24)
            bind_rigid(tooth,owner)
bind_rigid(rail('Bone | incisor alveolar arch',[dental_arch(a) for a in np.linspace(math.radians(-65),math.radians(65),25)],.019,M['bone'],'Skeleton'),'jaw')
for i in range(8):
    points,faces,theta=incisor_mesh(i)
    mesh=bpy.data.meshes.new(f'Incisor crown {i+1}'); mesh.from_pydata(points,[],faces); mesh.update()
    bm=bmesh.new(); bm.from_mesh(mesh); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
    tooth=bpy.data.objects.new(f'Tooth | lower incisor {i+1}',mesh); COLS['Skeleton'].objects.link(tooth)
    mesh.materials.append(M['tooth'])
    for face in mesh.polygons: face.use_smooth=len(face.vertices)==4
    tooth['dental_arch_angle']=float(theta); bind_rigid(tooth,'jaw')
bind_rigid(ellipsoid('Dental pad | no upper incisors',(0,-.745,2.16),(.14,.09,.034),M['cartilage'],'Skeleton'),'head')
bind_rigid(ellipsoid('Cartilage | expanded nasal support',(0,-.76,2.275),(.24,.23,.18),M['cartilage'],'Skeleton'),'head')

# Soft tissue volumes: deliberately simplified and adapted to the upright trunk.
organ_specs=[
 ('Brain',(0,.015,2.56),(.23,.22,.24),'organ','head'),
 ('Lung L',(.175,-.01,1.62),(.17,.19,.235),'lung','spine.upper'),
 ('Lung R',(-.175,-.01,1.62),(.17,.19,.235),'lung','spine.upper'),
 ('Heart',(.025,-.155,1.53),(.105,.105,.15),'heart','spine.upper'),
 ('Diaphragm',(0,.035,1.37),(.33,.225,.055),'muscle','spine.lower'),
 ('Rumen | left abdomen',(.13,.045,1.23),(.20,.235,.22),'organ','pelvis'),
 ('Reticulum',(.07,-.105,1.30),(.115,.105,.10),'organ','spine.lower'),
 ('Omasum',(-.17,-.03,1.28),(.10,.11,.11),'organ','spine.lower'),
 ('Abomasum',(-.04,-.16,1.06),(.205,.095,.08),'organ','pelvis'),
 ('Liver | right abdomen',(-.245,.06,1.33),(.105,.18,.16),'liver','spine.lower'),
 ('Kidney L',(.15,.265,1.27),(.065,.045,.10),'kidney','spine.lower'),
 ('Kidney R',(-.15,.265,1.31),(.065,.045,.10),'kidney','spine.lower'),
 ('Intestinal volume',(-.10,.015,1.105),(.16,.17,.105),'organ','pelvis')]
for name,loc,scale,mat,bone in organ_specs:
    o=ellipsoid('Organ guide | '+name,loc,scale,M[mat],'Organs'); bind_rigid(o,bone)
    o['purpose']='Simplified spatial envelope for the mascot; comparative ruminant layout, no clinical claim.'
bind_rigid(rail('Organ guide | trachea',[(0,-.12,2.30),(0,-.11,2.02),(0,-.07,1.74)],.037,M['cartilage'],'Organs'),'neck')

# Muscle masses define the skin's load-bearing and articulation landmarks.
muscles=[]
for side,s in [('L',1),('R',-1)]:
    for name,loc,scale,bone in [
      ('gluteal',(s*.25,.09,1.14),(.145,.18,.19),'pelvis'),
      ('quadriceps',(s*.28,-.045,.97),(.11,.12,.235),f'thigh.{side}'),
      ('calf',(s*.315,.045,.575),(.075,.085,.175),f'shin.{side}'),
      ('deltoid',(s*.385,.025,1.82),(.105,.14,.13),f'upper_arm.{side}'),
      ('upper arm',(s*.455,.05,1.715),(.098,.105,.16),f'upper_arm.{side}'),
      ('forearm',(s*.54,-.06,1.43),(.082,.09,.145),f'forearm.{side}'),
      ('masseter',(s*.26,-.105,2.30),(.125,.155,.17),'head'),
      ('temporalis',(s*.205,.015,2.64),(.13,.15,.20),'head')]:
        o=ellipsoid('Muscle | '+name+' '+side,loc,scale,M['muscle'],'Muscles')
        bind_rigid(o,bone); muscles.append(o)
for name,loc,scale,bone in [
 ('Abdominal wall',(0,-.01,1.28),(.33,.295,.30),'pelvis'),
 ('Thoracic envelope',(0,.04,1.66),(.35,.325,.37),'spine.upper'),
 ('Dorsal neck',(0,.15,2.01),(.255,.22,.34),'neck'),
 ('Nasal soft tissue',(0,-.745,2.26),(.275,.245,.20),'head')]:
    bind_rigid(ellipsoid('Muscle | '+name,loc,scale,M['muscle'],'Muscles'),bone)

# Skin is fused once from the shared masses; armature weights are added below.
def shoulder_weight(points):
    p=np.asarray(points); x=np.abs(p[...,0]); z=p[...,2]
    height_blend=np.clip((z-1.58)/.25,0,1)
    height_blend=height_blend*height_blend*(3-2*height_blend)
    start=.48-.25*height_blend; width=.05+.18*height_blend
    weight=np.clip((x-start)/width,0,1); weight=weight*weight*(3-2*weight)
    collar=np.clip((z-1.95)/.20,0,1); collar=collar*collar*(3-2*collar)
    return weight*(1-collar)

parts=[]
def skin_part(name,loc,scale):
    o=ellipsoid(name,loc,scale,M['skin'],'Skin'); parts.append(o); return o
parts.append(loft('Torso | soft continuous pear',[
 (.91,0,.045,.09,.09),(1.02,0,.035,.29,.29),(1.22,0,.02,.455,.40),
 (1.43,0,.02,.465,.395),(1.68,0,.045,.405,.355),(1.87,0,.08,.34,.30),
 (2.06,0,.095,.275,.265),(2.20,0,.075,.18,.195),(2.29,0,.035,.04,.05)],M['skin'],'Skin'))
for side,s in [('L',1),('R',-1)]:
    parts.append(loft('Leg | smooth taper '+side,[
      (.135,s*.33,.040,.075,.035),(.21,s*.33,-.020,.112,.110),
      (.32,s*.33,.014,.097,.108),(.53,s*.32,-.015,.10,.11),
      (.75,s*.30,-.06,.108,.12),(.96,s*.28,-.02,.15,.18),(1.16,s*.26,.035,.195,.22),
      (1.30,s*.24,.05,.11,.13)],M['skin'],'Skin'))
body=join_remesh('Skin | continuous torso and limbs',parts,'Skin',.015,12)
bm=bmesh.new(); bm.from_mesh(body.data)
original=[v.co.copy() for v in bm.verts]
for _ in range(32):
    bmesh.ops.smooth_vert(bm,verts=list(bm.verts),factor=.5,use_axis_x=True,use_axis_y=True,use_axis_z=True)
for vertex,position in zip(bm.verts,original):
    blend=math.exp(-((abs(position.x)-.30)/.20)**2-((position.z-1.16)/.22)**2)
    blend*=float(np.clip((.12-position.y)/.18,0,1))
    vertex.co=position.lerp(vertex.co,blend)
bm.to_mesh(body.data); bm.free()
for vertex in body.data.vertices:
    p=vertex.co
    # Lift the shallow central droop into a rounded arch between the thighs.
    p.z+=.045*math.exp(-(p.x/.145)**2-((p.z-.99)/.14)**2)
body.data.update()
body.data.materials.clear(); body.data.materials.append(M['skin'])
arm_surfaces=[]
for side,s in [('L',1),('R',-1)]:
    obj=loft('Skin | continuous arm.'+side,[
      (1.22,s*.64,-.20,.075,.080),(1.30,s*.64,-.18,.101,.098),
      (1.38,s*.635,-.14,.098,.098),
      (1.48,s*.615,-.015,.105,.107),(1.60,s*.575,.06,.112,.113),
      (1.75,s*.465,.045,.126,.13),(1.85,s*.365,.035,.132,.14),
      (1.95,s*.275,.025,.084,.085),(2.025,s*.205,.025,.025,.035)],M['skin'],'Skin')
    shoulder_volume=ellipsoid('Skin | rounded shoulder '+side,
      (s*.35,.04,1.83),(.155,.145,.170),M['skin'],'Skin')
    obj=join_remesh('Skin | continuous arm.'+side,[obj,shoulder_volume],'Skin',.007,6)
    arm_surfaces.append(obj)
    tissue=join_remesh('Muscle | shoulder tissue '+side,[
      ellipsoid('Deltoid guide',(s*.36,.04,1.83),(.130,.120,.145),M['muscle'],'Muscles'),
      ellipsoid('Pectoral guide',(s*.27,-.09,1.80),(.20,.10,.12),M['muscle'],'Muscles'),
      ellipsoid('Scapular guide',(s*.28,.15,1.84),(.20,.10,.13),M['muscle'],'Muscles')],'Muscles',.012,5)
    upper=tissue.vertex_groups.new(name='upper_arm.'+side); trunk=tissue.vertex_groups.new(name='spine.upper')
    for v in tissue.data.vertices:
        weight=float(shoulder_weight(v.co))
        upper.add([v.index],weight,'REPLACE'); trunk.add([v.index],1-weight,'REPLACE')
    mod=tissue.modifiers.new('Shoulder tissue follows chest and arm','ARMATURE'); mod.object=rig; mod.use_deform_preserve_volume=True

# One continuous skin surface removes the separate cap/torso intersection.
# The forearms have clearance from the belly so only the shoulders fuse.
body=join_remesh('Skin | continuous torso and limbs',[body,*arm_surfaces],'Skin',.010,7)
arm_surfaces=[]
body.data.materials.clear(); body.data.materials.append(M['skin'])
bm=bmesh.new(); bm.from_mesh(body.data); original=[v.co.copy() for v in bm.verts]
for _ in range(16):
    bmesh.ops.smooth_vert(bm,verts=list(bm.verts),factor=.45,use_axis_x=True,use_axis_y=True,use_axis_z=True)
for v,p0 in zip(bm.verts,original):
    blend=math.exp(-((abs(p0.x)-.36)/.19)**2-((p0.z-1.85)/.22)**2)
    v.co=p0.lerp(v.co,blend)
bm.to_mesh(body.data); bm.free(); body.data.update()

head=loft('Skin | long moose head and integrated muzzle',[
 (.33,0,2.58,.055,.075),(.26,0,2.55,.265,.32),(.035,0,2.53,.425,.43),
 (-.20,0,2.45,.35,.39),(-.43,0,2.32,.287,.29),(-.67,0,2.25,.31,.25),
 (-.88,0,2.205,.32,.235),(-1.025,0,2.19,.24,.185),(-1.085,0,2.19,.035,.05)
 ],M['skin'],'Skin',axis='Y')
active(head)
subdivision=head.modifiers.new('Muzzle tissue resolution','SUBSURF'); subdivision.levels=2
bpy.ops.object.modifier_apply(modifier=subdivision.name)
# Two softly joined terminal pads give the front a shallow central cleft.
for vertex in head.data.vertices:
    position=vertex.co.copy(); front=float(np.clip((-position.y-.87)/.20,0,1))
    vertex.co.y-=.028*front*math.exp(-((abs(position.x)-.14)/.12)**2)
    vertex.co.z+=.018*front*math.exp(-(position.x/.070)**2)*float(np.clip((2.19-position.z)/.10,0,1))
head.data.update()
# Bound the cut to individual triangles so later fur tessellation cannot span
# across a concave nostril opening with an invalid shared diagonal.
bm=bmesh.new(); bm.from_mesh(head.data)
bmesh.ops.triangulate(bm,faces=list(bm.faces),ngon_method='EAR_CLIP')
bm.to_mesh(head.data); bm.free()
# A single curved pocket sits below the alar fold. Its broad front end
# narrows into the upper rear crease, without a second pointed slit.
nostril_outline=np.array([(-.790,2.270),(-.800,2.190),(-.850,2.110),
    (-.920,2.080),(-.974,2.110),(-.966,2.160),(-.900,2.190),
    (-.840,2.205)],dtype=float)
contour=[]
for i,point in enumerate(nostril_outline):
    fraction=.08 if i==0 else .24
    start=point+(nostril_outline[(i-1)%len(nostril_outline)]-point)*fraction
    end=point+(nostril_outline[(i+1)%len(nostril_outline)]-point)*fraction
    for t in np.linspace(0,1,7): contour.append((1-t)**2*start+2*(1-t)*t*point+t*t*end)
contour=np.asarray(contour)
# Raise the existing skin slightly around the opening, preserving one continuous
# fleshy rim instead of attaching a torus or drawing a black oval on the surface.
original_positions=[vertex.co.copy() for vertex in head.data.vertices]
original_normals=[vertex.normal.copy() for vertex in head.data.vertices]
for vertex,position,normal in zip(head.data.vertices,original_positions,original_normals):
    if position.y>-.67: continue
    yz=np.array([position.y,position.z])
    a=contour; d=np.roll(contour,-1,axis=0)-a
    t=np.clip(np.sum((yz-a)*d,axis=1)/np.maximum(np.sum(d*d,axis=1),1e-12),0,1)
    distance=float(np.min(np.linalg.norm(yz-a-d*t[:,None],axis=1)))
    lateral=float(np.clip((abs(normal.x)-.35)/.45,0,1)); lateral=lateral*lateral*(3-2*lateral)
    rim_elevation=.018*math.exp(-((distance-.010)/.026)**2)
    upper_fold=.032*math.exp(-((position.y+.875)/.085)**2-((position.z-2.245)/.067)**2)
    elevation=(rim_elevation+upper_fold)*lateral
    vertex.co=position+normal*elevation
head.data.update()
head.data.materials.clear(); head.data.materials.append(M['skin']); head.data.materials.append(M['nostril'])
surface_bvh=BVHTree.FromPolygons([v.co for v in head.data.vertices],[tuple(p.vertices) for p in head.data.polygons])
for side,s in [('L',1),('R',-1)]:
    vertices=[]; faces=[]; around=len(contour); rings=26
    center=np.array([-.880,2.155])
    for angle in np.linspace(.025,math.pi-.025,rings):
        for y,z in center+(contour-center)*math.sin(angle):
            hit,_,_,_=surface_bvh.ray_cast(Vector((s*.65,y,z)),Vector((-s,0,0)))
            if hit is None: raise RuntimeError('Nostril pocket leaves the muzzle surface')
            vertices.append((hit.x+s*(-.014+.080*math.cos(angle)),y,z))
    for j in range(rings-1):
        for i in range(around):
            a=j*around+i; b=j*around+(i+1)%around; faces.append((a,b,b+around,a+around))
    faces.extend([tuple(reversed(range(around))),tuple((rings-1)*around+i for i in range(around))])
    mesh=bpy.data.meshes.new('Curved nostril recess'); mesh.from_pydata(vertices,[],faces); mesh.update()
    bm=bmesh.new(); bm.from_mesh(mesh); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
    cutter=bpy.data.objects.new('Nostril | hooked lateral recess '+side,mesh); COLS['Features'].objects.link(cutter)
    cutter=join_remesh(cutter.name,[cutter],'Features',.0018,4)
    bm=bmesh.new(); bm.from_mesh(cutter.data); bmesh.ops.triangulate(bm,faces=list(bm.faces)); bm.to_mesh(cutter.data); bm.free()
    bpy.context.view_layer.update()
    cutter_bvh=BVHTree.FromPolygons([cutter.matrix_world@v.co for v in cutter.data.vertices],[tuple(p.vertices) for p in cutter.data.polygons])
    cut(head,cutter,solver='MANIFOLD')
    # Darken the actual cut faces; no black ball or flat nostril decal.
    for face in head.data.polygons:
        hit,normal,index,distance=cutter_bvh.find_nearest(head.matrix_world@face.center)
        if distance is not None and distance<.00001: face.material_index=1
# Relax the lip transition while preserving the closed Boolean topology.
bm=bmesh.new(); bm.from_mesh(head.data)
bmesh.ops.triangulate(bm,faces=list(bm.faces),ngon_method='EAR_CLIP')
rim=set()
for edge in bm.edges:
    if len(edge.link_faces)==2 and edge.link_faces[0].material_index!=edge.link_faces[1].material_index: rim.update(edge.verts)
for _ in range(2): rim.update(neighbor for vertex in list(rim) for edge in vertex.link_edges for neighbor in edge.verts)
interior=[vertex for vertex in rim if all(face.material_index==1 for face in vertex.link_faces)]
for _ in range(3): bmesh.ops.smooth_vert(bm,verts=interior,factor=.20,use_axis_x=True,use_axis_y=True,use_axis_z=True)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(head.data); bm.free()
smooth(head)
bind_rigid(head,'head')
jaw=loft('Skin | lower jaw and closing lip',[
 (.07,0,2.14,.025,.035),(-.01,0,2.13,.16,.12),(-.18,0,2.075,.245,.125),
 (-.36,0,2.025,.235,.105),(-.57,0,1.995,.22,.072),(-.75,0,1.998,.18,.048),
 (-.875,0,2.023,.11,.025),(-.90,0,2.030,.008,.008)],M['skin'],'Skin',axis='Y')
for vertex in jaw.data.vertices:
    tuck=float(np.clip((-vertex.co.y+.02)/.40,0,1))
    vertex.co.z+=.045*tuck; vertex.co.x*=1-.15*tuck
bind_rigid(jaw,'jaw')
bind_rigid(ellipsoid('Mouth | interior',(0,-.53,2.14),(.16,.23,.045),M['mouth'],'Features'),'jaw')
tail=ellipsoid('Skin | short moose tail',(0,.38,1.12),(.075,.105,.13),M['skin'],'Skin',direction=(0,.4,-1)); bind_rigid(tail,'tail')
beard=loft('Skin | throat bell',[
 (1.60,0,-.37,.008,.01),(1.70,0,-.375,.065,.07),(1.85,0,-.35,.145,.12),
 (2.00,0,-.27,.14,.13),(2.12,0,-.17,.08,.09)],M['skin'],'Skin')
bind_rigid(beard,'jaw')

def front_patch(points):
    p=np.asarray(points); z=p[...,2]; x=np.abs(p[...,0]); y=p[...,1]
    width=.275+.075*np.exp(-((z-1.35)/.38)**2)
    oval=np.sqrt((x/width)**2+((z-1.60)/.68)**2)
    edge=np.clip((1.12-oval)/.32,0,1); edge=edge*edge*(3-2*edge)
    return edge*np.clip((-y-.025)/.12,0,1)

def coat_color(o):
    warmth=face_warmth([o.matrix_world@v.co for v in o.data.vertices]) if o==head else np.zeros(len(o.data.vertices))
    for name,base,muzzle_color,patch_color,beard_color,warm_color in [
      ('coat_color','#20344e','#101b29','#849aa8','#192a3b','#523b2c'),
      ('coat_color_brown','#594132','#281c17','#b29879','#493022','#65412b')]:
        attr=o.data.color_attributes.new(name=name,type='FLOAT_COLOR',domain='POINT'); vals=[]
        c0=np.array(color(base)); c1=np.array(color(muzzle_color)); c2=np.array(color(patch_color))
        c3=np.array(color(warm_color))
        for v in o.data.vertices:
            p=o.matrix_world@v.co
            muzzle=np.clip((-p.y-.43)/.48,0,1)**1.4 if o in (head,jaw) else 0
            c=c0*(1-muzzle)+c1*muzzle
            c=c*(1-warmth[v.index])+c3*warmth[v.index]
            if o==body:
                patch=front_patch(p); c=c*(1-patch)+c2*patch
            if o==beard: c=np.array(color(beard_color))
            vals.extend(c)
        attr.data.foreach_set('color',vals)
for o in [body,head,jaw,tail,beard,*arm_surfaces]: coat_color(o)
install_muzzle_detail(head,M['nostril'])

# Leaf-shaped cupped ears, not bear ears. Local X runs from root to tip.
def ear(side,s):
    verts=[]; faces=[]; interior=[]; ring_positions=[]; rings=40; around=64
    root=Vector((s*.31,.025,2.695)); direction=Vector((s*.45,.020,.20))
    for j in range(rings+1):
        t=j/rings; center=root+direction*t
        width=.145*math.sin(math.pi*t)**.70+.005
        envelope=.025+.975*math.sin(math.pi*t)
        for i in range(around):
            a=2*math.pi*i/around; u=math.cos(a); front=math.sin(a)<0
            # The rim curls forward; the inner basin recedes toward the back.
            rim=-.085*u*u
            basin=-.006*math.sqrt(max(0,1-u*u))+.018*math.exp(-((t-.32)/.20)**2)*(1-u*u)
            back=.04*math.sqrt(max(0,1-u*u))
            v=center+Vector((-s*.38,0,.92))*width*u+Vector((0,envelope*(rim+(basin if front else back)),0))
            verts.append(v); ring_positions.append(t)
            edge=float(np.clip((.96-abs(u))/.18,0,1)); edge=edge*edge*(3-2*edge)
            ends=float(np.clip((t-.055)/.14,0,1)*np.clip((.96-t)/.12,0,1))
            interior.append(edge*ends if front else 0.)
    for j in range(rings):
        for i in range(around):
            a=j*around+i; b=j*around+(i+1)%around
            faces.append((a,b,b+around,a+around))
    faces += [tuple(reversed(range(around))),tuple(rings*around+i for i in range(around))]
    me=bpy.data.meshes.new('Ear shell '+side); me.from_pydata(verts,[],faces); me.update()
    bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(me); bm.free()
    o=bpy.data.objects.new('Skin | cupped leaf ear '+side,me); COLS['Skin'].objects.link(o)
    me.materials.append(M['skin']); smooth(o); coat_color(o)
    me.attributes.new('ear_interior','FLOAT','POINT').data.foreach_set('value',interior)
    for name,base,deep,light in [('coat_color','#20344e','#354958','#7f909b'),('coat_color_brown','#594132','#715240','#b09077')]:
        vals=[]; c0=np.array(color(base)); c1=np.array(color(deep)); c2=np.array(color(light))
        for mask,t in zip(interior,ring_positions):
            fade=float(np.clip((t-.14)/.52,0,1)); warm=c1*(1-fade)+c2*fade
            vals.extend(c0*(1-mask)+warm*mask)
        me.color_attributes[name].data.foreach_set('color',vals)
    o['ear_side']=s; bind_rigid(o,'ear.'+side)
    return o
ears=[ear(side,s) for side,s in [('L',1),('R',-1)]]

# Curved palmate antlers: cupped webs, swept beams and unequal tapered tines.
for side,s in [('L',1),('R',-1)]:
    antlerparts=[sweep('Swept antler beam',[(s*.265,.06,2.80),(s*.34,.10,2.96),(s*.52,.19,3.13),(s*.76,.23,3.22),(s*1.02,.07,3.18),(s*1.27,-.10,3.28),(s*1.51,-.16,3.46)],[.069,.079,.080,.075,.054,.032,.004],M['antler'],'Antlers')]
    # The web and its outer points share one perimeter and surface. There are
    # no cone bases pasted onto the palm face or collars around those points.
    outline=np.array([
      (.63,3.12),(.65,3.42),(.67,3.72),(.69,3.95),
      (.71,4.01),(.73,4.075),(.76,4.022),(.81,4.03),(.84,4.11),(.87,4.038),
      (.93,4.04),(.96,4.095),(.99,4.036),(1.04,4.018),(1.075,4.067),(1.11,3.97),
      (1.18,3.90),(1.31,4.035),(1.29,3.89),(1.24,3.79),(1.30,3.68),
      (1.47,3.855),(1.41,3.66),(1.28,3.56),(1.29,3.46),(1.56,3.64),
      (1.42,3.43),(1.20,3.34),(1.06,3.22),(.81,3.15)],dtype=float)
    tips={5,8,11,14,17,21,25}; contour=[]
    for i,p in enumerate(outline):
        previous=outline[(i-1)%len(outline)]; following=outline[(i+1)%len(outline)]
        fraction=.075 if i in tips else .27
        start=p+(previous-p)*fraction; end=p+(following-p)*fraction
        for t in np.linspace(0,1,5): contour.append((1-t)**2*start+2*(1-t)*t*p+t*t*end)
    me=bpy.data.meshes.new('Palm with continuous edge points')
    me.from_pydata([(s*x,0,z) for x,z in contour],[],[tuple(range(len(contour)))]); me.update()
    bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=4,use_grid_fill=True)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(me); bm.free()
    palm=bpy.data.objects.new('Continuous palmate blade',me); COLS['Antlers'].objects.link(palm); me.materials.append(M['antler'])
    thickness=palm.vertex_groups.new(name='Palm edge taper')
    boundary=np.asarray(contour)
    for vertex in me.vertices:
        x=s*vertex.co.x; z=vertex.co.z
        root_blend=.07*(1-float(np.clip((z-3.12)/.30,0,1)))
        vertex.co.y=.27+.32*float(np.clip((z-3.1)/.95,0,1))+.23*(x-.9)-.065*((x-.98)/.32)**2+root_blend
        a=boundary; b=np.roll(boundary,-1,axis=0); d=b-a
        t=np.clip(np.sum((np.array([x,z])-a)*d,axis=1)/np.maximum(np.sum(d*d,axis=1),1e-12),0,1)
        distance=float(np.min(np.linalg.norm(np.array([x,z])-a-d*t[:,None],axis=1)))
        thickness.add([vertex.index],min(1,distance/.065),'REPLACE')
    active(palm); solid=palm.modifiers.new('Tapered bone plate','SOLIDIFY'); solid.thickness=.075; solid.offset=0.
    solid.vertex_group=thickness.name; solid.thickness_vertex_group=.24; solid.use_even_offset=True
    bpy.ops.object.modifier_apply(modifier=solid.name); smooth(palm); antlerparts.append(palm)
    for points,radii in [
      ([(s*.50,.19,3.12),(s*.55,.14,3.17),(s*.60,.03,3.27),(s*.62,-.065,3.39)],[.060,.050,.027,.004]),
      ([(s*.81,.20,3.20),(s*.875,.12,3.235),(s*.92,.005,3.30),(s*.99,-.06,3.43)],[.060,.050,.025,.004])]:
        antlerparts.append(sweep('Forward brow tine',points,radii,M['antler'],'Antlers'))
    antler=join_remesh('Antler | cupped palmate '+side,antlerparts,'Antlers',.0055,6)
    for vertex in antler.data.vertices:
        vertex.co.x=s*(.265+(s*vertex.co.x-.265)*.91)
        vertex.co.z=2.80+(vertex.co.z-2.80)*.88
    antler.data.materials.clear(); antler.data.materials.append(M['antler']); bind_rigid(antler,'head')
    antler['design_note']='Broad palmate antlers are a mascot stylization, not the anatomy of a newborn calf.'

# Eyes sit on the sides of the face and look slightly forward.
for side,s in [('L',1),('R',-1)]:
    center=Vector((s*.285,-.195,2.60))
    eye=ellipsoid('Eye | globe '+side,center,(.111,.070,.124),M['eye'],'Features')
    eye.rotation_euler[2]=s*math.radians(32)
    bind_rigid(eye,'head')
    # Partial eyelid arcs, open corners and a soft upper rim.
    rot=Matrix.Rotation(s*math.radians(32),3,'Z')
    points=[center+rot@Vector((.107*math.cos(a),-.018,.12*math.sin(a))) for a in np.linspace(.03,math.pi-.03,9)]
    bind_rigid(rail('Eye | upper lid '+side,points,.012,M['lid'],'Features'),'head')
    points=[center+rot@Vector((.105*math.cos(a),-.018,.12*math.sin(a))) for a in np.linspace(math.pi+.07,2*math.pi-.07,9)]
    bind_rigid(rail('Eye | lower lid '+side,points,.007,M['lid'],'Features'),'head')

# Hooves remain cloven, with a flattened weight-bearing sole.
def hoof_shape(name,loc,halfwidth,depth,height,bone,coronet_x=None):
    x,y,z=loc; w=halfwidth; d=depth/2
    inward=0 if coronet_x is None else coronet_x-x
    top_width=.53 if coronet_x is None else .66
    top_depth=.46 if coronet_x is None else .56
    o=loft(name,[(z,x,y,w*.82,d*.84),(z+height*.07,x,y,w*.95,d*.97),
      (z+height*.27,x,y+d*.035,w,d),(z+height*.60,x+inward*.12,y+d*.20,w*.90,d*.85),
      (z+height*.88,x+inward*.32,y+d*.36,w*.76,d*.70),
      (z+height,x+inward*.42,y+d*.40,w*top_width,d*top_depth)],M['hoof'],'Features')
    # Each toe narrows forward into a softly pointed wedge. Preserve the
    # buried crown and broad heel while drawing the outer wall toward the cleft.
    for start in range(0,len(o.data.vertices),64):
        ring=list(o.data.vertices)[start:start+64]
        middle=sum((v.co for v in ring),Vector())/64
        radius_y=max(abs(v.co.y-middle.y) for v in ring)
        lower=float(np.clip((z+height*.92-middle.z)/(height*.44),0,1))
        lower=lower*lower*(3-2*lower)
        for vertex in ring:
            toe=float(np.clip((1+(middle.y-vertex.co.y)/radius_y)*.5,0,1))
            toe=toe*toe*lower
            vertex.co.x=middle.x+(vertex.co.x-middle.x)*(1-.55*toe)+inward*.18*toe
            vertex.co.y-=depth*.05*toe
    # A genuinely flat sole supports the stance; the wall above stays rounded.
    for vertex in o.data.vertices: vertex.co.z=max(z,vertex.co.z)
    for face in o.data.polygons:
        if all(abs(o.data.vertices[i].co.z-z)<1e-6 for i in face.vertices): face.use_smooth=False
    return bind_rigid(o,bone)

def hand_hoof(side,s,digit,d):
    """A tapered half-hoof, with an angled toe, flat inner wall and buried crown."""
    center=s*.64
    o=loft(f'Hoof | hand {side} digit {digit}',[
      (1.12,center+d*.046,-.247,.009,.016),
      (1.135,center+d*.047,-.240,.021,.035),
      (1.16,center+d*.050,-.223,.034,.059),
      (1.205,center+d*.053,-.207,.048,.080),
      (1.28,center+d*.049,-.189,.052,.083),
      (1.33,center+d*.043,-.179,.047,.072),
      (1.355,center+d*.040,-.174,.039,.059)],M['hoof'],'Features')
    # Narrow rounded sections lead into the pointed toe. The facing walls
    # stay close together and the cleft narrows into the common wrist.
    for start in range(0,len(o.data.vertices),64):
        ring=list(o.data.vertices)[start:start+64]
        middle=sum((v.co for v in ring),Vector())/64
        rx=max(abs(v.co.x-middle.x) for v in ring)
        ry=max(abs(v.co.y-middle.y) for v in ring)
        gap=.006*float(np.clip((1.34-middle.z)/.13,0,1))
        for v in ring:
            x=(v.co.x-middle.x)/rx; y=(v.co.y-middle.y)/ry
            v.co.x=middle.x+rx*math.copysign(abs(x)**.95,x)
            v.co.y=middle.y+ry*math.copysign(abs(y)**.95,y)
            if d*(v.co.x-center)<gap: v.co.x=center+d*gap
    o.data.update()
    o.data.materials.append(M['hoof_sole'])
    for face in o.data.polygons:
        if face.center.z<1.145: face.material_index=1
    return bind_rigid(o,'hand.'+side)

for side,s in [('L',1),('R',-1)]:
    for digit,d in enumerate((-1,1),1):
        hoof_shape(f'Hoof | foot {side} digit {digit}',(s*.33+d*.080,-.095,.006),.076,.34,.24,'foot.'+side,coronet_x=s*.33)
        hand_hoof(side,s,digit,d)
        bind_rigid(ellipsoid(f'Hoof | rear dewclaw {side} {digit}',(s*.33+d*.055,.115,.26),(.020,.032,.037),M['hoof'],'Features',direction=(0,.3,-1),segments=24),'foot.'+side)

# Smooth regional weights avoid pulling the abdomen into the adjacent arms.
groups={n:body.vertex_groups.new(name=n) for n in BONES if n not in ('root','head','jaw','tail') and not n.startswith('ear')}
arm_attribute=body.data.attributes.new('arm_influence','FLOAT','POINT')
def soft(t):
    t=max(0,min(1,t)); return t*t*(3-2*t)
def segment_distance(p,n):
    a,b,_=BONES[n]; a,b=Vector(a),Vector(b); d=b-a
    t=max(0,min(1,(p-a).dot(d)/d.length_squared))
    return (p-a-d*t).length
def normalized(raw):
    total=sum(raw.values()); return {n:w/total for n,w in raw.items()}
for v in body.data.vertices:
    p=v.co; ax=abs(p.x); side='L' if p.x>=0 else 'R'
    trunk=normalized({n:math.exp(-((p.z-z)/width)**2) for n,z,width in [('pelvis',1.11,.28),('spine.lower',1.45,.24),('spine.upper',1.76,.25),('neck',2.12,.22)]})
    arms=[f'upper_arm.{side}',f'forearm.{side}',f'hand.{side}']
    arm_d={n:segment_distance(p,n) for n in arms}
    # Localized shoulder tissue blends across the chest and back; the lower
    # belly remains outside the arm's influence despite the nearby forearm.
    arm=float(shoulder_weight(p)); arm_attribute.data[v.index].value=arm
    legs=[f'thigh.{side}',f'shin.{side}',f'foot.{side}']
    leg_d={n:segment_distance(p,n) for n in legs}
    leg=soft((1.28-p.z)/.22)*soft((ax-.07)/.17)
    if arm>leg:
        elbow=soft((p.z-1.49)/.17); wrist=1-soft((p.z-1.32)/.16)
        limb_weights={arms[0]:elbow,arms[1]:(1-elbow)*(1-wrist),arms[2]:(1-elbow)*wrist}
    else:
        limb_weights=normalized({n:math.exp(-(d/.15)**2) for n,d in leg_d.items()})
    influence=max(arm,leg)
    weights={n:w*(1-influence) for n,w in trunk.items()}
    for n,w in limb_weights.items(): weights[n]=weights.get(n,0)+w*influence
    for n,w in weights.items():
        if w>1e-7: groups[n].add([v.index],w,'REPLACE')
mod=body.modifiers.new('Deform from anatomical skeleton','ARMATURE'); mod.object=rig; mod.use_deform_preserve_volume=True
body['construction']='Unified skin over shared skeletal landmarks and muscle envelopes; normalized regional weights.'

# A smaller trunk beneath the head captures the youthful reference proportions.
# The same continuous map changes bone landmarks AND every tissue surface.
COMPRESSION=BODY_RATIO; PROPORTION_JOIN=BODY_JOIN
def compact(p):
    p=Vector(p); p.z=float(compact_height(p.z))
    return p
world_matrices={}
for obj in list(scene.objects):
    if obj.type not in ('MESH','CURVE'): continue
    old=obj.matrix_world.copy(); new=old.copy(); new.translation=compact(old.translation)
    inverse=new.inverted(); world_matrices[obj.name]=new
    if obj.type=='MESH':
        for vertex in obj.data.vertices: vertex.co=inverse@compact(old@vertex.co)
        obj.data.update()
    else:
        for spline in obj.data.splines:
            for point in spline.bezier_points:
                co=point.co.copy(); left=point.handle_left.copy(); right=point.handle_right.copy()
                point.co=inverse@compact(old@co); point.handle_left=inverse@compact(old@left); point.handle_right=inverse@compact(old@right)
active(rig); bpy.ops.object.mode_set(mode='EDIT')
for bone in rig.data.edit_bones: bone.head=compact(bone.head); bone.tail=compact(bone.tail)
bpy.ops.object.mode_set(mode='OBJECT'); bpy.context.view_layer.update()
for name,matrix in world_matrices.items(): bpy.data.objects[name].matrix_world=matrix
BONES={name:(tuple(compact(a)),tuple(compact(b)),parent) for name,(a,b,parent) in BONES.items()}
scene['body_compression']=COMPRESSION; scene['proportion_join']=PROPORTION_JOIN
scene['leg_ratio']=LEG_RATIO; scene['leg_height_drop']=LEG_DROP; scene['head_height_offset']=HEAD_OFFSET
bpy.context.view_layer.update()

# Make UV-attached, editable native curves with deterministic surface sampling.
def groom(surface, count, length, seed):
    uv_values=np.asarray(attachment_atlas(surface)).reshape(-1,2)
    mesh=surface.data; mesh.calc_loop_triangles(); tris=list(mesh.loop_triangles)
    coords=np.array([v.co[:] for v in mesh.vertices],dtype=np.float32)
    normals=np.array([v.normal[:] for v in mesh.vertices],dtype=np.float32)
    ids=np.array([t.vertices[:] for t in tris]); ps=coords[ids]
    areas=np.linalg.norm(np.cross(ps[:,1]-ps[:,0],ps[:,2]-ps[:,0]),axis=1)*.5
    rng=np.random.default_rng(seed); chosen=rng.choice(len(tris),count,p=areas/areas.sum())
    a=np.sqrt(rng.random(count)); b=rng.random(count); w=np.stack([1-a,a*(1-b),a*b],axis=1)
    roots=np.sum(ps[chosen]*w[:,:,None],axis=1)
    ns=np.sum(normals[ids[chosen]]*w[:,:,None],axis=1); ns/=np.maximum(np.linalg.norm(ns,axis=1)[:,None],1e-9)
    mat=np.array(surface.matrix_world); world=roots@mat[:3,:3].T+mat[:3,3]
    # Sampling masks are expressed in the original shared design coordinates.
    world[:,2]=design_height(world[:,2])
    # Clear the actual eye spheres and hollow nostrils, retaining muzzle fuzz.
    valid=np.ones(count,dtype=bool)
    if surface==head:
        # Preserve clean cavity walls and lips: no hair roots on cut surfaces.
        valid &= np.array([t.material_index for t in tris])[chosen]==0
        for s in (-1,1):
            p=(world-np.array([s*.285,-.195,2.60]))/np.array([.121,.085,.135])
            valid &= np.sum(p*p,axis=1)>1.15
        valid &= ~((normals[ids[chosen]].mean(axis=1)[:,2]<-.5)&(np.abs(world[:,0])<.17)&(world[:,1]>-.84)&(world[:,1]<-.10))
    if surface==jaw:
        # The mouth floor has a separate mucosal surface, with a furry outer lip.
        valid &= ~((ns[:,2]>.35)&(np.abs(world[:,0])<.18)&(world[:,1]>-.84)&(world[:,1]<-.05))
    if surface==body:
        # The rounded pastern seats inside the horn; keep its buried tip clean.
        valid &= world[:,2]>.19
        valid &= (shoulder_weight(world)<.5)|(world[:,2]>1.29)
    if surface in arm_surfaces:
        valid &= world[:,2]>1.29
    is_brow='brow_side' in surface
    if is_brow:
        # The hidden rear of the brow must not grow hair back through the head.
        valid &= ns[:,1]<.08
    chosen=chosen[valid]; roots=roots[valid]; ns=ns[valid]; w=w[valid]; world=world[valid]; count=len(roots)
    is_head=surface in (head,jaw)
    ear_mask=None
    if 'ear_side' in surface:
        values=np.array([v.value for v in surface.data.attributes['ear_interior'].data])
        ear_mask=np.sum(values[ids[chosen]]*w,axis=1)
    flow=np.tile([0,.15,-1.],(count,1))
    belly_tuft=np.zeros(count)
    shoulder_coat=np.zeros(count)
    if surface==body:
        lower=np.clip((1.30-world[:,2])/.40,0,1)
        flow[:,0]=world[:,0]*.8*lower
        flow[:,1]+=.45*lower
        arm_coat=shoulder_weight(world)
        arm_flow=np.stack([np.sign(world[:,0])*.40,np.full(count,.15),np.full(count,-.95)],axis=1)
        flow=flow*(1-arm_coat[:,None])+arm_flow*arm_coat[:,None]
        # A soft shoulder mantle continues the back coat onto the upper arm.
        # Keep this grooming mask independent of the joint's skin weights.
        shoulder_coat=np.exp(-((np.abs(world[:,0])-.35)/.23)**2-((world[:,2]-1.86)/.24)**2)
        shoulder_coat*=.70+.30*np.clip((world[:,1]+.13)/.30,0,1)
        shoulder_flow=np.stack([np.sign(world[:,0])*.45,np.full(count,.32),np.full(count,-.85)],axis=1)
        flow=flow*(1-shoulder_coat[:,None])+shoulder_flow*shoulder_coat[:,None]
        belly_tuft=np.clip(1-(world[:,0]/.085)**2,0,1)**1.6
        belly_tuft*=np.exp(-((world[:,2]-1.04)/.10)**2)*np.clip((-world[:,1]-.01)/.12,0,1)
        tuft_flow=np.stack([-world[:,0]*2.8,np.full(count,-.10),np.full(count,-1.)],axis=1)
        flow=flow*(1-belly_tuft[:,None])+tuft_flow*belly_tuft[:,None]
    if is_head: flow=np.stack([world[:,0]*.65,np.full(count,.25),np.full(count,-.65)],axis=1)
    if surface==beard: flow=np.stack([world[:,0]*-.45,np.full(count,-.10),np.full(count,-1.)],axis=1)
    if ear_mask is not None: flow=np.tile([surface['ear_side']*.8,-.04,.36],(count,1))
    if is_brow:
        brow_t=np.clip((np.abs(world[:,0])-.140)/.225,0,1)
        flow=np.stack([np.full(count,surface['brow_side']*.95),
                       np.full(count,-.12),.95-.90*brow_t],axis=1)
    # Transform world grooming direction into each surface's local coordinates.
    flow=flow@np.linalg.inv(mat[:3,:3]).T
    flow-=ns*np.sum(flow*ns,axis=1)[:,None]; flow/=np.maximum(np.linalg.norm(flow,axis=1)[:,None],1e-8)
    lateral=np.cross(ns,flow)
    local_length=length*rng.uniform(.80,1.17,count)
    if surface==body:
        # Blend the longer dorsal coat and shoulders without stacking their lengths.
        mane=np.exp(-((world[:,2]-2.02)/.22)**2)*np.clip((world[:,1]+.01)/.22,0,1)
        mantle=1-(1-mane)*(1-shoulder_coat)
        local_length*=1+1.45*mantle
        ankle=np.clip((.45-world[:,2])/.25,0,1)
        local_length*=1-.78*ankle
        underside=np.exp(-(world[:,0]/.21)**4-((world[:,2]-1.0)/.17)**2)
        underside*=np.clip((-ns[:,2]-.05)/.55,0,1)
        local_length*=1-.80*underside
        local_length*=1-.24*arm_coat*(1-shoulder_coat)
        local_length*=1-.70*arm_coat*np.clip((1.42-world[:,2])/.13,0,1)
    muzzle=np.clip((-world[:,1]-.43)/.50,0,1) if is_head else np.zeros(count)
    local_length*=1-.55*muzzle
    if ear_mask is not None: local_length*=1-.66*ear_mask
    if surface in arm_surfaces:
        local_length*=1-.70*np.clip((1.42-world[:,2])/.13,0,1)
    brow_clearance=np.zeros(count)
    if surface==head:
        # A broad short forehead coat leaves room for the long brow feathers.
        # Avoid a nearly shaved band tracing the moving eyebrow's outline.
        brow_clearance=np.clip((world[:,2]-2.50)/.15,0,1)
        brow_clearance*=np.clip((3.05-world[:,2])/.24,0,1)
        brow_clearance*=np.clip((-ns[:,1]+.05)/.65,0,1)
        brow_clearance=brow_clearance*brow_clearance*(3-2*brow_clearance)
        local_length*=1-.40*brow_clearance
    # Dense undercoat plus a minority of soft longer guard hairs.
    guard=rng.random(count)<.10; local_length*=np.where(guard,1.9-.55*brow_clearance-.40*shoulder_coat,1.)
    if surface==body:
        # A small tapered fan of hair, grown from the existing belly surface.
        tuft_length=.115*(.92+.08*np.sin(world[:,0]*91+world[:,2]*57))
        local_length=local_length*(1-belly_tuft)+tuft_length*belly_tuft
    variation=.09*np.sin(world[:,0]*70+world[:,2]*46)+rng.uniform(-.04,.04,count)
    if is_brow:
        # Slightly uneven feathery tips, with most length toward the inner arch.
        local_length*=.85+.25*np.sin(np.pi*brow_t)
        variation=.18*np.sin(brow_t*19)+rng.uniform(-.10,.10,count)
    points=np.empty((count,5,3),np.float32)
    for j in range(5):
        t=j/4
        loft=(.82*t-.30*t*t) if is_brow else (.48*t-.22*t*t)
        loft=loft+.20*belly_tuft*t*t
        loft=loft+shoulder_coat*(.19*t-.05*t*t)
        points[:,j]=roots+local_length[:,None]*(ns*loft[:,None]+flow*(.92*t*t)+lateral*(variation*t*t)[:,None])
    radii=(rng.uniform(.00019,.00034,count)*(1-.35*muzzle))[:,None]*np.power(1-np.linspace(0,1,5),.8)[None,:]+.000006
    radii*=1-.10*brow_clearance[:,None]
    radii*=1-.10*shoulder_coat[:,None]
    loops=np.array([t.loops[:] for t in tris])[chosen]
    uv=np.sum(uv_values[loops]*w[:,:,None],axis=1)
    curves=bpy.data.hair_curves.new('Groom | '+surface.name); curves.add_curves([5]*count)
    curves.attributes['position'].data.foreach_set('vector',points.reshape(-1))
    curves.attributes.new('radius','FLOAT','POINT').data.foreach_set('value',radii.astype(np.float32).reshape(-1))
    curves.attributes.new('surface_uv_coordinate','FLOAT2','CURVE').data.foreach_set('vector',uv.astype(np.float32).reshape(-1))
    indices=(rng.random(count)<muzzle).astype(np.int32)
    if surface==head: indices=np.where(rng.random(count)<face_warmth(world),6,indices).astype(np.int32)
    if surface==body: indices=np.where(rng.random(count)<front_patch(world),2,0).astype(np.int32)
    if surface==beard: indices[:]=3
    if ear_mask is not None: indices=np.where(rng.random(count)<ear_mask,4,0).astype(np.int32)
    if is_brow: indices[:]=5
    curves.attributes.new('material_index','INT','CURVE').data.foreach_set('value',indices)
    for mat in HAIR: curves.materials.append(mat)
    o=bpy.data.objects.new('Fur | '+surface.name,curves); COLS['Fur'].objects.link(o)
    o.parent=surface; o.matrix_basis=Matrix.Identity(4); curves.surface=surface; curves.surface_uv_map=UV_NAME
    mod=o.modifiers.new('Follow skin poses','NODES'); mod.node_group=GROOM_NODE
    o['strand_count']=count; o['root_seed']=seed; o['editable_native_curves']=True
    return count

HAIR=[hair_material('Moose | soft navy fibers','#233a57',.42),
      hair_material('Moose | dark muzzle fibers','#142233',.46),
      hair_material('Moose | light front fibers','#9badb9',.44),
      hair_material('Moose | throat beard fibers','#1d3249',.45),
      hair_material('Moose | inner ear velvet','#8b9ea9',.50),
      hair_material('Moose | feathered eyebrow fibers','#192a40',.48),
      hair_material('Moose | chestnut facial fibers','#806048',.46)]
for mat,navy,brown in zip(HAIR,['#233a57','#142233','#9badb9','#1d3249','#8b9ea9','#192a40','#806048'],['#71503a','#3c291e','#ccb08b','#543a27','#b59376','#4b3021','#91633e']):
    mat.node_tree.nodes['Fur | controlled fiber sheen'].inputs[0].default_value=.22
    ramp=mat.node_tree.nodes['Fur | individual strand variation'].color_ramp
    for element,factor in zip(ramp.elements,[.92,1.09]):
        for i,(a,b) in enumerate(zip(color(navy)[:3],color(brown)[:3])):
            palette_driver(element,'color',i,min(1,a*factor),min(1,b*factor))
# Warm guard hairs retain brown tips rather than inheriting the blue coat tint.
for element,tint in zip(HAIR[6].node_tree.nodes['Fur | dark root to luminous tip'].color_ramp.elements,
                        [(.50,.43,.35,1),(.90,.83,.73,1),(1.12,1.08,1.,1)]):
    element.color=tint
GROOM_NODE=bpy.data.node_groups.new('Moose | curves follow skin','GeometryNodeTree')
GROOM_NODE.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
GROOM_NODE.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
ni=GROOM_NODE.nodes.new('NodeGroupInput'); de=GROOM_NODE.nodes.new('GeometryNodeDeformCurvesOnSurface'); no=GROOM_NODE.nodes.new('NodeGroupOutput')
GROOM_NODE.links.new(ni.outputs['Geometry'],de.inputs['Curves']); GROOM_NODE.links.new(de.outputs['Curves'],no.inputs['Geometry'])
strands=0
for surface,count,length,seed in [(body,266000,.055,89),(head,130000,.034,90),(jaw,16000,.025,91),(tail,6000,.055,92),(beard,24000,.14,99),*( (o,22000,.035,93+i) for i,o in enumerate(ears))]:
    strands+=groom(surface,count,length,seed)
scene['fur_strands']=strands

# Transparent skin envelope makes the relationship between layers inspectable.
ghost=bpy.data.materials.new('Anatomy | translucent skin envelope'); ghost.use_nodes=True
n=ghost.node_tree.nodes; l=ghost.node_tree.links; n.clear()
out=n.new('ShaderNodeOutputMaterial'); tr=n.new('ShaderNodeBsdfTransparent'); diff=n.new('ShaderNodeBsdfDiffuse')
diff.inputs['Color'].default_value=color('#557b98'); mix=n.new('ShaderNodeMixShader'); mix.inputs[0].default_value=.055
l.new(tr.outputs[0],mix.inputs[1]); l.new(diff.outputs[0],mix.inputs[2]); l.new(mix.outputs[0],out.inputs['Surface'])
for src in list(COLS['Skin'].objects):
    shell=src.copy(); shell.data=src.data.copy(); shell.name='Envelope | '+src.name
    shell.data.materials.clear(); shell.data.materials.append(ghost)
    for p in shell.data.polygons: p.material_index=0
    COLS['Shell'].objects.link(shell)

# Stored pose tests, with foot placement driven by targets for the step pose.
for b in rig.pose.bones: b.rotation_mode='XYZ'
for frame in [1,40,80]:
    scene.frame_set(frame)
    for b in rig.pose.bones: b.rotation_euler=(0,0,0); b.location=(0,0,0)
    if frame==40:
        def point_bone(name,direction):
            bpy.context.view_layer.update(); bone=rig.pose.bones[name]; old=bone.matrix.copy()
            current=(old.to_quaternion()@Vector((0,1,0))).normalized()
            rotation=current.rotation_difference(Vector(direction).normalized()).to_matrix().to_4x4()
            matrix=rotation@old; matrix.translation=old.translation; bone.matrix=matrix
            bpy.context.view_layer.update()
        point_bone('upper_arm.L',(.85,-.15,-.35))
        point_bone('forearm.L',(.42,-.35,.84))
        point_bone('hand.L',(.30,-.04,.95))
        rig.pose.bones['head'].rotation_euler[2]=math.radians(-6)
        rig.pose.bones['ear.R'].rotation_euler[1]=math.radians(-10)
    if frame==80:
        rig.pose.bones['thigh.L'].rotation_euler[0]=math.radians(-17)
        rig.pose.bones['shin.L'].rotation_euler[0]=math.radians(18)
        rig.pose.bones['foot.L'].rotation_euler[0]=math.radians(-8)
        rig.pose.bones['thigh.R'].rotation_euler[0]=math.radians(9)
        rig.pose.bones['shin.R'].rotation_euler[0]=math.radians(-6)
        rig.pose.bones['upper_arm.L'].rotation_euler[0]=math.radians(13)
        rig.pose.bones['upper_arm.R'].rotation_euler[0]=math.radians(-13)
        rig.pose.bones['head'].rotation_euler[0]=math.radians(3)
        bpy.context.view_layer.update()
        floor=min((o.matrix_world@v.co).z for o in scene.objects if o.name.startswith('Hoof | foot') for v in o.data.vertices)
        root=rig.pose.bones['root']; matrix=root.matrix.copy(); matrix.translation.z+=.005-floor; root.matrix=matrix
        bpy.context.view_layer.update()
    for b in rig.pose.bones:
        b.keyframe_insert(data_path='rotation_euler',frame=frame)
        b.keyframe_insert(data_path='location',frame=frame)
    scene.timeline_markers.new({1:'Standing',40:'Explaining',80:'Step study'}[frame],frame=frame)
scene.frame_start=1; scene.frame_end=80; scene.frame_set(1)

sys.path.insert(0,str(Path(__file__).resolve().parent))
from facial import install as install_facial_controls
strands+=install_facial_controls(scene,rig,head,jaw,COLS,M,groom,bind_rigid,coat_color,ellipsoid)
scene['fur_strands']=strands

# Neutral studio shared by every anatomical and finished view.
world=bpy.data.worlds.new('Studio | soft neutral'); world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.72,.78,.86,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.15; scene.world=world
def light(name,loc,power,size,tint):
    d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.shape='DISK'; d.size=size; d.color=tint
    o=bpy.data.objects.new(name,d); COLS['Studio'].objects.link(o); o.location=loc
    o.rotation_euler=(Vector((0,0,1.8))-o.location).to_track_quat('-Z','Y').to_euler()
light('Key',(-3.5,-4.5,5),740,4,(1,.90,.80))
light('Fill',(3,-3.2,3),300,3.4,(.80,.88,1))
light('Rim',(1.5,3,4.5),650,3,(.84,.92,1))
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,0))
floor=bpy.context.object; floor.name='Studio | seamless floor'; move(floor,'Studio')
floor.data.materials.append(material('Studio | warm white','#e9e7e2',.9))
camdata=bpy.data.cameras.new('Review camera'); cam=bpy.data.objects.new('Review camera',camdata); COLS['Studio'].objects.link(cam)
cam.location=(4.3,-8,2.94-LEG_DROP*.5); target=Vector((0,-.08,1.84-LEG_DROP*.5)); cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
camdata.type='ORTHO'; camdata.ortho_scale=4.50; scene.camera=cam
scene.render.engine='CYCLES'; scene.cycles.samples=64; scene.cycles.use_denoising=True
scene.render.resolution_x=1200; scene.render.resolution_y=1400; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'
scene.view_settings.exposure=-.55

LAYERS={
 '01 Skeleton':{'Skeleton','Antlers','Shell','Rig','Studio'},
 '02 Organs':{'Skeleton','Organs','Antlers','Shell','Rig','Studio'},
 '03 Muscles':{'Skeleton','Muscles','Antlers','Shell','Rig','Studio'},
 '04 Skin':{'Skin','Features','Antlers','Rig','Studio'},
 '05 Fur':{'Skin','Features','Antlers','Fur','Rig','Studio'},
}
scene.view_layers[0].name='05 Fur'
for name,visible in LAYERS.items():
    layer=scene.view_layers.get(name) or scene.view_layers.new(name)
    layer.use=name=='05 Fur'
    for child in layer.layer_collection.children: child.exclude=child.name not in visible
bpy.context.window.view_layer=scene.view_layers['05 Fur']
scene['character']='Buddy, the Origin89 moose: broad antlers, dark muzzle, short sturdy legs, soft shoulders and a hanging throat bell.'
scene['species']='moose'
scene['rebuild']='pnpm brand:model then pnpm brand:rebuild'
scene['source_registry']='buddy-source.json'
scene['anatomy_status']='Stylized construction guides; adapted biped pelvis, spine and organ volumes. Antlers are an intentional age stylization.'
scene['references']=json.dumps([
 'https://www.digimorph.org/specimens/Alces_alces/',
 'https://courses.ecampus.oregonstate.edu/wildlife/species.php?id=335',
 'https://pressbooks.umn.edu/largeanimalanatomy/chapter/abdomen-2/',
 'https://www.disneyanimation.com/publications/flesh-flab-and-fascia-simulation-on-zootopia/'])
scene['landmarks']=json.dumps(BONES)
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA'
        area.spaces.active.clip_end=300
active(rig)
from finish import apply as apply_finish
apply_finish(scene)
ROOT.joinpath('blender').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/buddy.blend'))
print('MOOSE_BUILT',json.dumps({'bones':len(BONES),'fur_strands':strands,'objects':len(scene.objects)}),flush=True)
