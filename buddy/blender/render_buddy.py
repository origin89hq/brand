"""Render the saved Buddy source without rebuilding or saving over the model."""
import argparse,hashlib,json,os,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
from studio import configure,expression,avatar,camera,device
from finish import render_quality
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--file',type=Path,default=ROOT/'blender/buddy.blend')
p.add_argument('--view',choices=['front','side','hero','face','face-front','face-side','face-muzzle','hooves','hands','antlers','avatar','avatar-compact','portrait','feet-side'],default='hero')
p.add_argument('--layer',choices=['skeleton','organs','muscles','skin','fur'],default='fur')
p.add_argument('--palette',choices=['brown','navy'],default='brown')
p.add_argument('--frame',type=int,default=1);p.add_argument('--expression');p.add_argument('--pose',choices=['standing','explaining','step'])
p.add_argument('--size',type=int,default=1200);p.add_argument('--samples',type=int,default=192);p.add_argument('--padding',type=float,default=1.)
p.add_argument('--transparent',action='store_true');p.add_argument('--output',type=Path)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
if a.size<128 or a.samples<1 or a.padding<1:p.error('Use size >= 128, samples >= 1 and padding >= 1.')
source=a.file.resolve();bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene
layer=configure(s,a.transparent,a.palette,a.layer);s.frame_set(a.frame)
native=None;pose=a.pose
if a.expression:native,pose=expression(s,a.expression,a.pose)
elif a.pose:s.frame_set({'standing':1,'explaining':40,'step':80}[a.pose])
overrides=avatar(s,a.expression,isolated=a.view=='avatar') if a.view.startswith('avatar') else {}
if a.layer=='skin':
    for name in ('Skin','Features','Antlers'):
        for o in bpy.data.collections[name].objects:
            if o.type in ('MESH','CURVE'):o.data.materials.clear();o.data.materials.append(bpy.data.materials['Clay | cool porcelain'])
    for o in s.objects:
        if o.name.startswith(('Eye | globe','Nostril | recessed','Mouth |')):
            o.data.materials.clear();o.data.materials.append(bpy.data.materials['Mouth and nasal cavity | deep slate'])
target=camera(s,a.view,a.size,a.padding);render_quality(s,a.samples,a.layer=='fur');device(s)
dest=a.output or ROOT/'renders'/f'{a.palette}-{a.view}.png';dest=dest.resolve();dest.parent.mkdir(parents=True,exist_ok=True)
s.render.filepath=str(dest);bpy.ops.render.render(write_still=True,layer=layer.name)
meta={'source':os.path.relpath(source,dest.parent),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'native_blender_render':True,'scene':s.name,'layer':layer.name,'palette':a.palette,'frame':s.frame_current,'expression':a.expression or next((k for k,v in json.loads(s['expression_presets']).items() if v==s.frame_current),None),'native_expression':native,'pose':pose,'camera':list(s.camera.location),'target':list(target),'ortho_scale':s.camera.data.ortho_scale,'resolution':[s.render.resolution_x,s.render.resolution_y],'size':[s.render.resolution_x,s.render.resolution_y],'transparent':a.transparent,'samples':a.samples,'blender':bpy.app.version_string}
meta['view']=a.view;meta['facial_overrides']=overrides
meta['denoising']=s.cycles.use_denoising;meta['adaptive_threshold']=s.cycles.adaptive_threshold;meta['finish']=s.get('finish')
dest.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n');print('BUDDY_RENDERED',dest,flush=True)
