"""Compact app vignette built afresh from the registered Buddy, with native props.
The generated umbrella concept remains archived; no raster art is used here.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];BRAND=ROOT.parent
sys.path.insert(0,str(BRAND/'identity/source'))
from buddy_source import master,modules,digest
sys.path.insert(0,str(modules()))
from studio import configure,expression,device
from finish import render_quality
def material(name,hex,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True
    rgb=[int(hex[i:i+2],16)/255 for i in (1,3,5)]
    rgb=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(*rgb,1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value=rough
    return m
p=argparse.ArgumentParser();p.add_argument('--size',type=int,default=1400);p.add_argument('--samples',type=int,default=192)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.open_mainfile(filepath=str(master()))
s=bpy.context.scene;configure(s,transparent=True);expression(s,'concerned');bpy.context.view_layer.update()
for scene in list(bpy.data.scenes):
    if scene!=s:bpy.data.scenes.remove(scene)
s.name='Buddy | Reserve mode app scene'
r=bpy.data.objects['Buddy | pose rig'];r.animation_data_clear()
# Relaxed hand on the storage enclosure. Scene gestures do not edit the master.
# The relaxed right hoof sits beside the storage enclosure.
bpy.context.view_layer.update()
col=bpy.data.collections.new('Situation | editable reserve props');s.collection.children.link(col)
def link(obj):
    for c in list(obj.users_collection):c.objects.unlink(obj)
    col.objects.link(obj);return obj
navy=material('Reserve | powder coated navy','#243d57',.55)
ivory=material('Reserve | warm storage enclosure','#e4dbc9',.51)
amber=material('Reserve | woven amber canopy','#d9952c',.76)
seam=material('Reserve | canopy stitching','#e7ae56',.79)
rubber=material('Reserve | deep blue rubber','#142a3c',.70)
cloudmat=material('Reserve | soft grey cloud','#afbbc5',.88)
blue=material('Reserve | rain','#5688a1',.38)
for mat,scale,strength,depth in ((amber,290,.17,.0012),(cloudmat,85,.12,.001)):
    n=mat.node_tree.nodes.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=scale
    b=mat.node_tree.nodes.new('ShaderNodeBump');b.inputs['Strength'].default_value=strength;b.inputs['Distance'].default_value=depth
    mat.node_tree.links.new(n.outputs['Fac'],b.inputs['Height']);mat.node_tree.links.new(b.outputs['Normal'],mat.node_tree.nodes.get('Principled BSDF').inputs['Normal'])
def box(name,loc,dim,mat,bevel=.04):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=link(bpy.context.object);o.name=name;o.dimensions=dim
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    b=o.modifiers.new('Soft manufactured edges','BEVEL');b.width=bevel;b.segments=5
    o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL');o.data.materials.append(mat);return o

def stroke(name,points,width,mat,cyclic=False):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.bevel_depth=width;c.bevel_resolution=4
    q=c.splines.new('POLY');q.points.add(len(points)-1)
    for p,co in zip(q.points,points):p.co=(*co,1)
    q.use_cyclic_u=cyclic;o=bpy.data.objects.new(name,c);col.objects.link(o);c.materials.append(mat);return o

def sphere(name,loc,scale,mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=32,location=loc);o=link(bpy.context.object);o.name=name;o.scale=scale;o.data.materials.append(mat)
    for f in o.data.polygons:f.use_smooth=True
    return o

# The stationary enclosure sits beside the relaxed hoof; no booster cables.
hand=r.pose.bones['hand.R'];rest=r.data.bones[hand.name]
forward=(hand.tail-hand.head).normalized();hp=r.matrix_world@(hand.head+forward*.13)
x=-1.45;y=.04;top=max(.65,hp.z-.045)
case=box('Storage | freestanding enclosure',(x,y,top/2),(.86,.69,top),ivory,.08)
box('Storage | recessed front',(x,y-.354,top*.51),(.69,.032,top-.22),navy,.045)
for dx in (-.30,.30):box('Storage | grounded foot',(x+dx,y,.032),(.13,.48,.06),rubber,.018)
# A readable low-charge silhouette is recessed into the physical enclosure.
cy=top*.52;w=.46;h=.235;rad=.027;points=[]
for cx,cz,begin in [(x+w/2-rad,cy+h/2-rad,0),(x-w/2+rad,cy+h/2-rad,90),(x-w/2+rad,cy-h/2+rad,180),(x+w/2-rad,cy-h/2+rad,270)]:
    for i in range(10):
        angle=math.radians(begin+i*90/9);points.append((cx+rad*math.cos(angle),y-.381,cz+rad*math.sin(angle)))
stroke('Storage | battery outline',points,.012,ivory,True)
box('Storage | battery terminal',(x+w/2+.029,y-.383,cy),(.047,.025,.095),ivory,.01)
box('Storage | low amber reserve',(x-w/2+.07,y-.386,cy),(.065,.026,.17),amber,.012)
for dx in (-.27,.27):
    sphere('Storage | captive panel screw',(x+dx,y-.377,.17),(.017,.009,.017),rubber)

# Continuous eight-panel canopy with a scalloped hem and shallow sewn ribs.
ux=-1.75;uy=.20;apex=4.42;radius=1.12;drop=.56
verts=[(ux,uy,apex)];faces=[];rings=26;sectors=192
for j in range(1,rings+1):
    t=j/rings
    for i in range(sectors):
        ang=2*math.pi*i/sectors;scallop=.043*(.5-.5*math.cos(8*ang))*t**7
        rr=radius*t*(1-.026*(.5-.5*math.cos(8*ang))*t**6)
        verts.append((ux+rr*math.cos(ang),uy+rr*math.sin(ang),apex-drop*t**1.5+scallop))
for i in range(sectors):faces.append((0,1+i,1+(i+1)%sectors))
for j in range(rings-1):
    for i in range(sectors):
        n=(i+1)%sectors;v=1+j*sectors;faces.append((v+i,v+sectors+i,v+sectors+n,v+n))
mesh=bpy.data.meshes.new('Umbrella | continuous sewn canopy');mesh.from_pydata(verts,[],faces);mesh.update()
o=bpy.data.objects.new('Umbrella | amber canopy',mesh);col.objects.link(o);mesh.materials.append(amber)
for f in mesh.polygons:f.use_smooth=True
mod=o.modifiers.new('Thin cloth thickness','SOLIDIFY');mod.thickness=.007
for i in range(8):
    ang=2*math.pi*i/8;points=[]
    for j in range(1,40):
        t=j/39;points.append((ux+radius*t*math.cos(ang),uy+radius*t*math.sin(ang),apex-drop*t**1.5+.004))
    stroke('Umbrella | sewn rib '+str(i),points,.0027,seam)
    sphere('Umbrella | rounded rib tip '+str(i),points[-1],(.021,.021,.028),rubber)
stroke('Umbrella | mast',[(ux,uy,.14),(ux,uy,apex+.055)],.022,navy)
box('Storage | umbrella mounting collar',(ux,uy,top+.045),(.080,.080,.085),navy,.014)
sphere('Umbrella | finial',(ux,uy,apex+.058),(.031,.031,.055),rubber)
# One small cloud, separate from live forecast copy in the app.
clouds=[]
for dx,dz,sx,sz in [(-.28,0,.27,.22),(-.02,.13,.34,.30),(.29,.03,.28,.23),(0,-.09,.40,.17)]:
    clouds.append(sphere('Forecast | cloud',(1.33+dx,.44,4.08+dz),(sx,.22,sz),cloudmat))
bpy.ops.object.select_all(action='DESELECT')
for o in clouds:o.select_set(True)
bpy.context.view_layer.objects.active=clouds[0];bpy.ops.object.convert(target='MESH');bpy.ops.object.join();o=bpy.context.object
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
rem=o.modifiers.new('One smooth cloud volume','REMESH');rem.mode='VOXEL';rem.voxel_size=.018;bpy.ops.object.modifier_apply(modifier=rem.name)
sm=o.modifiers.new('Soft cloud silhouette','SMOOTH');sm.factor=1;sm.iterations=5
for f in o.data.polygons:f.use_smooth=True
for i,(dx,z) in enumerate([(-.20,2.95),(.06,2.86),(.30,3.0)]):
    o=sphere('Forecast | drop '+str(i),(1.33+dx,.36,z+.65),(.036,.036,.070),blue)
    for v in o.data.vertices:
        if v.co.z>0:v.co.x*=1-.62*v.co.z;v.co.y*=1-.62*v.co.z;v.co.z*=1.22

configure(s,transparent=True)
s.camera.location=(3.1,-11,3.6);target=Vector((-.42,.08,2.25));s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.type='ORTHO';s.camera.data.ortho_scale=5.50
s.render.resolution_x=s.render.resolution_y=a.size;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';render_quality(s,a.samples)
try:
    pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='METAL';pref.get_devices()
    for d in pref.devices:d.use=d.type=='METAL'
    s.cycles.device='GPU'
except Exception:s.cycles.device='CPU'
s['buddy_master']=str(master().relative_to(BRAND));s['buddy_source_sha256']=digest()
s['usage']='Compact illustrative Reserve-mode vignette. Forecast, telemetry and actual controller state belong to application text.'
s['rebuild']='blender --background --python situations/source/build_reserve_scene.py'
notes=bpy.data.texts.new('READ ME | Shared Buddy');notes.write('This scene is a generated editable derivative of '+s['buddy_master']+'. Edit Buddy in that master, and props in source/build_reserve_scene.py. Rebuild using '+s['rebuild']+'. The old generated umbrella concept is archived. This image is not telemetry or a connection diagram.\n')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
s.frame_end=1;s.frame_set(1);bpy.context.view_layer.update();bpy.ops.file.pack_all()
dest=ROOT/'buddy-reserve.blend';bpy.ops.wm.save_as_mainfile(filepath=str(dest))
output=ROOT/'app-scenes/buddy-reserve.png';s.render.filepath=str(output);bpy.ops.render.render(write_still=True,layer="05 Fur")
output.with_suffix('.json').write_text(json.dumps({'buddy_source_sha256':digest(),'scene_source_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'source':str(master().relative_to(BRAND)),'native_blender_render':True,'transparent':True,'size':[a.size,a.size],'samples':a.samples,'state':'reserve-suggested','illustrative':True},indent=2)+'\n')
print('RESERVE_SCENE_SAVED',output,flush=True)
