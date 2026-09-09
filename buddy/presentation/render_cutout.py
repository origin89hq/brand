"""Render native alpha cutouts using the approved editable presentation scene."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[2]
FOLDER=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'buddy/blender'))
from studio import configure,expression,avatar,device
p=argparse.ArgumentParser()
p.add_argument('--look',choices=['portrait','studio'],default='portrait')
p.add_argument('--expression',choices=['welcoming','explaining','thinking','delighted','concerned','surprised','playful'],default='welcoming')
p.add_argument('--size',type=int,default=1920)
p.add_argument('--samples',type=int,default=256)
p.add_argument('--save',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
master=ROOT/'buddy/blender/buddy.blend';source_sha=sha(master)
scene_source=FOLDER/f'{a.look}.blend'
base_meta=json.loads(scene_source.with_suffix('.json').read_text())
assert base_meta['source_sha256']==source_sha
assert base_meta['recipe_sha256']==sha(FOLDER/'render.py')
assert base_meta['scene_sha256']==sha(scene_source)
# Evaluate the canonical keyed pose first. Saved presentation scenes hold a
# static pose, so reusing frame numbers in those files alone would lose expressions.
bpy.ops.wm.open_mainfile(filepath=str(master));s=bpy.context.scene
configure(s,False,'brown','fur');expression(s,a.expression);avatar(s,a.expression,isolated=False)
rig=bpy.data.objects['Buddy | pose rig']
if rig.animation_data:rig.animation_data.action=None
rig.pose.bones['head'].rotation_euler[2]=math.radians(-3)
rig.pose.bones['ear.R'].rotation_euler[1]=math.radians(-7)
if a.expression=='welcoming':
    for key,value in {'tongue_out':0.,'jaw_open':.025,'smile':.42,'upper_lid_L':.04,'upper_lid_R':.02}.items():rig['face_'+key]=value
rig.update_tag();bpy.context.view_layer.update()
pose={b.name:b.matrix_basis.copy() for b in rig.pose.bones}
controls={k:float(rig[k]) for k in rig.keys() if k.startswith('face_') and isinstance(rig[k],(int,float))}
frame=s.frame_current
# Keep the approved materials, hair, lights and camera. Only camera rays stop
# seeing the sweep; it remains present for the same soft indirect illumination.
bpy.ops.wm.open_mainfile(filepath=str(scene_source));s=bpy.context.scene
rig=bpy.data.objects['Buddy | pose rig'];s.frame_set(frame)
if rig.animation_data:rig.animation_data.action=None
for key,value in controls.items():rig[key]=value
for name,matrix in pose.items():rig.pose.bones[name].matrix_basis=Matrix(matrix)
rig.update_tag();bpy.context.view_layer.update()
layer=configure(s,True,'brown','fur')
bpy.data.objects['Presentation | seamless sweep'].visible_camera=False
s.render.resolution_x=a.size;s.render.resolution_y=round(a.size*(1.12 if a.look=='studio' else 1))
s.render.resolution_percentage=100;s.cycles.samples=a.samples;device(s)
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
stem=a.look+('' if a.expression=='welcoming' else '-'+a.expression)+'-transparent'
out=FOLDER/f'{stem}.png';s.render.filepath=str(out)
if a.save:bpy.ops.wm.save_as_mainfile(filepath=str(out.with_suffix('.blend')),compress=True)
bpy.ops.render.render(write_still=True,layer=layer.name)
assert sha(master)==source_sha and sha(scene_source)==base_meta['scene_sha256']
meta={
 'base':str(master.relative_to(ROOT)),'source_sha256':source_sha,
 'recipe_sha256':sha(Path(__file__)),
 'scene_source':str(scene_source.relative_to(ROOT)),'scene_source_sha256':sha(scene_source),
 'look':a.look,'expression':a.expression,'frame':frame,'samples':a.samples,
 'size':[s.render.resolution_x,s.render.resolution_y],
 'camera':base_meta['camera'],'tongue_out':rig['face_tongue_out'],
 'transparent':True,'alpha':'Native Cycles coverage; sweep hidden only from camera rays',
 'preserved':['approved lighting','focused hazel eyes','smooth directional coat','native geometry','rig'],
 'render_sha256':sha(out),'denoising':s.cycles.use_denoising,'depth_of_field':s.camera.data.dof.use_dof,
}
if a.save:meta['scene_sha256']=sha(out.with_suffix('.blend'))
out.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n')
print('TRANSPARENT_RENDERED',out,flush=True)
