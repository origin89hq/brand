"""Render saved identity scenes or forward Buddy exports to the shared renderer."""
import argparse,hashlib,json,runpy,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from buddy_source import master,modules,recipe_digest
VIEWS={'buddy-ready':'hero','buddy-explaining':'hero','buddy-thinking':'hero','buddy-front':'front','buddy-side':'side','buddy-portrait':'portrait','buddy-avatar':'avatar','buddy-feet':'hooves','buddy-feet-side':'feet-side','buddy-hands':'hands','buddy-antlers':'antlers'}
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--view',choices=['plate','tile','icon','signature',*VIEWS],required=True)
p.add_argument('--file',type=Path);p.add_argument('--output',type=Path);p.add_argument('--size',type=int,default=1400);p.add_argument('--samples',type=int,default=192)
p.add_argument('--expression');p.add_argument('--padding',type=float,default=1.);p.add_argument('--transparent',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
if a.size<128 or a.samples<1 or a.padding<1:p.error('Invalid size, samples or camera padding')
dest=a.output or ROOT/'renders'/f'{a.view}{"-transparent" if a.transparent else ""}.png'
if a.view in VIEWS:
    script=modules()/'render_buddy.py'
    state=a.expression or {'buddy-ready':'welcoming','buddy-explaining':'explaining','buddy-thinking':'thinking','buddy-portrait':'welcoming','buddy-avatar':'welcoming'}.get(a.view)
    sys.argv=[str(script),'--','--file',str(a.file or master()),'--view',VIEWS[a.view],'--size',str(a.size),'--samples',str(a.samples),'--padding',str(a.padding),'--output',str(dest)]
    if state:sys.argv+=['--expression',state]
    if a.view=='buddy-hands':sys.argv+=['--frame','40']
    if a.transparent:sys.argv+=['--transparent']
    runpy.run_path(str(script),run_name='__main__')
else:
    file=a.file or ROOT/'blender/origin89-brand.blend';bpy.ops.wm.open_mainfile(filepath=str(file))
    name={'plate':'01 | Plate studio','tile':'02 | Offgrid tile','icon':'03 | Offgrid icon master','signature':'05 | Origin89 signature'}[a.view]
    s=bpy.data.scenes[name];bpy.context.window.scene=s;s.cycles.samples=a.samples
    s.render.resolution_x=a.size;s.render.resolution_y=a.size if a.view in ('tile','icon') else round(a.size*.75)
    s.render.film_transparent=a.transparent
    for col in s.collection.children:
        if col.name.startswith('90 |'):col.hide_render=a.transparent
    sys.path.insert(0,str(modules()));from studio import device
    device(s);dest.parent.mkdir(parents=True,exist_ok=True);s.render.filepath=str(dest.resolve());bpy.ops.render.render(write_still=True)
    meta={'recipe_sha256':recipe_digest(),'source_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'scene':name,'camera':s.camera.name,'frame':1,'samples':a.samples,'transparent':a.transparent,'size':[s.render.resolution_x,s.render.resolution_y],'blender':bpy.app.version_string}
    dest.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n')
    print('BRAND_RENDER_SAVED',dest,flush=True)
