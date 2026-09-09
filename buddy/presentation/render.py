"""Approved Buddy presentation renderer; the shared character source is read-only."""
import argparse, hashlib, json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'buddy/blender'))
from studio import configure, expression, avatar, device
from finish import render_quality
p=argparse.ArgumentParser();p.add_argument('--look',choices=['studio','portrait'],default='portrait');p.add_argument('--size',type=int,default=1920);p.add_argument('--samples',type=int,default=256);p.add_argument('--save',action='store_true');p.add_argument('--expression',choices=['welcoming','explaining','thinking','delighted','concerned','surprised','playful'],default='welcoming')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
source=ROOT/'buddy/blender/buddy.blend';base_hash=hashlib.sha256(source.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene
layer=configure(s,False,'brown','fur');expression(s,a.expression);avatar(s,a.expression,isolated=False)
rig=bpy.data.objects['Buddy | pose rig']
if rig.animation_data:rig.animation_data.action=None
# A slight head inclination and asymmetric ears soften the neutral presentation.
rig.pose.bones['head'].rotation_euler[2]=math.radians(-3)
rig.pose.bones['ear.R'].rotation_euler[1]=math.radians(-7)
if a.expression=='welcoming':
    rig['face_tongue_out']=0.;rig['face_jaw_open']=.025;rig['face_smile']=.42
    rig['face_upper_lid_L']=.04;rig['face_upper_lid_R']=.02
rig.update_tag();bpy.context.view_layer.update()

def linear(h):
    rgb=[int(h[i:i+2],16)/255 for i in (1,3,5)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb)+(1,)

def material(name,h,roughness=.8):
    m=bpy.data.materials.new(name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=linear(h);bs.inputs['Roughness'].default_value=roughness
    return m

# Focused hazel eyes with restrained reflections on the existing corneal mesh.
m=bpy.data.materials['Eye | deep warm brown'];n=m.node_tree.nodes;l=m.node_tree.links
r=next(x for x in n if x.type=='VALTORGB').color_ramp
while len(r.elements)>1:r.elements.remove(r.elements[-1])
r.elements[0].position=0.;r.elements[0].color=linear('#100d0b')
for pos,h in [(.205,'#100d0b'),(.235,'#55351f'),(.32,'#765336'),(.41,'#503c2a'),(.465,'#231b15'),(.50,'#231b15')]:r.elements.new(pos).color=linear(h)
bs=n.get('Principled BSDF');bs.inputs['Roughness'].default_value=.18;bs.inputs['Specular IOR Level'].default_value=.22
# Very fine iris variation remains inside the same smooth eye surface.
noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=115;noise.inputs['Detail'].default_value=2
mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.16
ramp=next(x for x in n if x.type=='VALTORGB');l.new(ramp.outputs['Color'],mix.inputs[1]);l.new(noise.outputs['Fac'],mix.inputs[2]);l.new(mix.outputs[0],bs.inputs['Base Color'])

for side,sign in [('L',1),('R',-1)]:
    eye=bpy.data.objects['Eye | globe '+side];mat=m.copy();mat.name='Presentation | focused hazel '+side
    for node in mat.node_tree.nodes:
        if node.type=='MATH' and node.operation=='SUBTRACT' and node.inputs[0].is_linked and node.inputs[0].links[0].from_socket.name=='X':node.inputs[1].default_value=.5-sign*.14
    eye.data.materials.clear();eye.data.materials.append(mat)

for o in list(s.objects):
    if o.type=='LIGHT':bpy.data.objects.remove(o,do_unlink=True)
col=bpy.data.collections['Studio']
def relink(o):
    for c in list(o.users_collection):c.objects.unlink(o)
    col.objects.link(o);return o

def area(name,loc,energy,size,color,target=(0,-.2,1.8),ratio=1):
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='RECTANGLE';d.size=size;d.size_y=size*ratio;d.color=color
    if hasattr(d,'specular_factor'):d.specular_factor=0.0 if name.startswith(('Bounce','Edge','Backdrop')) else .65
    o=bpy.data.objects.new(name,d);col.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()

s.world.node_tree.nodes['Background'].inputs[0].default_value=(.7,.78,.85,1)
s.world.node_tree.nodes['Background'].inputs[1].default_value=.035
area('Window | warm key',(-3.3,-4.0,5.0),800,2.0,(1,.96,.89),ratio=1.4)
area('Bounce | face',(3,-4,2.9),125,3.0,(.84,.91,1))
area('Edge | shoulder',(1.3,2.4,4.4),450,2.0,(1,.95,.86),ratio=1.6)
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=-.1
floor=bpy.data.objects['Studio | seamless floor'];floor.hide_render=True
cyc_mat=material('Presentation | cyclorama','#c7bcaa' if a.look=='studio' else '#344c42')
profile=[(-15,0),(3,0)]
profile += [(3+3*math.sin(t),3-3*math.cos(t)) for t in [i*math.pi/2/32 for i in range(1,33)]]
profile += [(6,20)]
verts=[(x,y,z) for x in (-30,30) for y,z in profile];count=len(profile)
faces=[(i,i+1,i+1+count,i+count) for i in range(count-1)]
mesh=bpy.data.meshes.new('Presentation | sweep');mesh.from_pydata(verts,[],faces);mesh.update()
o=bpy.data.objects.new('Presentation | seamless sweep',mesh);col.objects.link(o);o.data.materials.append(cyc_mat)
for poly in mesh.polygons:poly.use_smooth=True

# Frame the visible character using a real perspective camera, rather than the
# orthographic review camera. The paper scene includes the feet and contact shadow.
cam=s.camera;cam.data.type='PERSP';cam.data.lens=70;cam.data.sensor_width=36
s.render.resolution_x=a.size;s.render.resolution_y=round(a.size*(1.12 if a.look=='studio' else 1.08));s.render.resolution_percentage=100
names=['Skin | long moose head and integrated muzzle','Skin | lower jaw and closing lip','Skin | throat bell','Skin | cupped leaf ear L','Skin | cupped leaf ear R','Antler | cupped palmate L','Antler | cupped palmate R']
if a.look=='studio':names+=['Skin | continuous torso and limbs']+[o.name for o in s.objects if o.name.startswith('Hoof | foot')]
graph=bpy.context.evaluated_depsgraph_get();points=[]
for name in names:
    o=bpy.data.objects[name].evaluated_get(graph);points += [o.matrix_world@Vector(v) for v in o.bound_box]
low=Vector(tuple(min(v[i] for v in points) for i in range(3)));high=Vector(tuple(max(v[i] for v in points) for i in range(3)))
target=(low+high)*.5
if a.look!='studio':target.z-=.16
angle=Vector((2.4,-9,.75) if a.look=='studio' else (1.5,-9,.05)).normalized()
distance=5
for _ in range(60):
    cam.location=target+angle*distance;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    coords=[world_to_camera_view(s,cam,v) for v in points]
    if all(.075<v.x<.925 and .065<v.y<.94 for v in coords):break
    distance*=1.04

if a.look!='studio':
    target=Vector((0,-.34,1.97));cam.data.lens=85;cam.location=target+Vector((2.8,-9,.2)).normalized()*4.8
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    s.render.resolution_y=a.size
if a.look=='portrait':
    # An actual colored backdrop gives the fur a soft, continuous environment.
    area('Backdrop | soft pool',(-2,1.5,4),180,4,(.90,1,.90),target=(0,6,3))
render_quality(s,a.samples,True)
s.cycles.adaptive_min_samples=64;s.cycles.adaptive_threshold=.006;device(s)
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
suffix='' if a.expression=='welcoming' else '-'+a.expression
out=Path(__file__).resolve().parent/f'{a.look}{suffix}.png';s.render.filepath=str(out)
if a.save:bpy.ops.wm.save_as_mainfile(filepath=str(out.with_suffix('.blend')),compress=True)
bpy.ops.render.render(write_still=True,layer=layer.name)
meta={'base':str(source.relative_to(ROOT)),'source_sha256':base_hash,'recipe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'look':a.look,'expression':a.expression,'frame':s.frame_current,'samples':a.samples,'size':[s.render.resolution_x,s.render.resolution_y],'camera':{'type':cam.data.type,'lens':cam.data.lens,'position':list(cam.location),'target':list(target)},'tongue_out':rig['face_tongue_out'],'changes':['lighting','perspective framing','eye shader','calm facial pose'],'preserved':['native body geometry','smooth directional coat','rig']}
assert hashlib.sha256(source.read_bytes()).hexdigest()==base_hash, 'Shared Buddy source changed during render'
meta['render_sha256']=hashlib.sha256(out.read_bytes()).hexdigest()
if a.save:meta['scene_sha256']=hashlib.sha256(out.with_suffix('.blend').read_bytes()).hexdigest()
meta['denoising']=s.cycles.use_denoising;meta['depth_of_field']=False
out.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n');print('PRESENTATION_RENDERED',out,flush=True)
