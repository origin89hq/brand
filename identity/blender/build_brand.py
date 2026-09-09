"""Create a portable, editable brand studio. Blender 5.2; no add-ons needed.
Run: blender -b --python-exit-code 1 --python build_brand.py -- --output FILE
Existing files are protected unless --overwrite is explicit.
"""
import argparse, json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[1]
args=argparse.ArgumentParser()
args.add_argument('--output',type=Path,default=ROOT/'blender/origin89-brand.blend')
args.add_argument('--overwrite',action='store_true')
a=args.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
if a.output.exists() and not a.overwrite: raise SystemExit('File exists: save manual edits as a variant, or use --overwrite.')
G=json.loads((ROOT/'source/geometry.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)

def linear(v): return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
def mat(name,hex,rough=.4,metal=0,noise=False):
    m=bpy.data.materials.new(name); m.use_nodes=True
    rgb=[linear(int(hex[i:i+2],16)/255) for i in (1,3,5)]
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*rgb,1)
    p.inputs['Roughness'].default_value=rough; p.inputs['Metallic'].default_value=metal
    m.diffuse_color=(*rgb,1)
    if noise:
        n=m.node_tree.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value=175
        b=m.node_tree.nodes.new('ShaderNodeBump'); b.inputs['Strength'].default_value=.13; b.inputs['Distance'].default_value=.009
        m.node_tree.links.new(n.outputs['Fac'],b.inputs['Height']); m.node_tree.links.new(b.outputs['Normal'],p.inputs['Normal'])
    return m
blue=mat('01 | Deep navy - studio finish','#172c50',.48,noise=True)
ivory=mat('02 | Warm ivory - ceramic inlay','#eadfcf',.36)
ink=mat('03 | Graphite','#07090c',.35)
paper=mat('04 | Warm studio paper','#f4f3ef',.7)

def collection(name):
    c=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c); return c
def link(obj,col):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    col.objects.link(obj); return obj
def empty(name,col):
    o=bpy.data.objects.new(name,None); col.objects.link(o); o.empty_display_type='PLAIN_AXES'; return o
def contours(commands):
    result=[]; pts=[]; current=None
    for op,ps in commands:
        if op=='moveTo': pts=[tuple(ps[0])]; current=pts[0]
        elif op=='lineTo': pts.append(tuple(ps[0])); current=pts[-1]
        elif op=='curveTo':
            p0=current; p1,p2,p3=ps
            for i in range(1,17):
                t=i/16; q=1-t
                pts.append(tuple(q**3*p0[j]+3*q*q*t*p1[j]+3*q*t*t*p2[j]+t**3*p3[j] for j in (0,1)))
            current=tuple(p3)
        elif op=='closePath':
            if pts[-1]==pts[0]: pts.pop()
            result.append(pts); pts=[]
    return result
def inside(p,poly):
    x,y=p; hit=False
    for (x1,y1),(x2,y2) in zip(poly,poly[1:]+poly[:1]):
        if (y1>y)!=(y2>y) and x<(x2-x1)*(y-y1)/(y2-y1)+x1: hit=not hit
    return hit
def shape(name,commands,col,material,scale=.02,center=(100,55),depth=.035,bevel=.006,z=0):
    curve=bpy.data.curves.new(name,'CURVE'); curve.dimensions='2D'; curve.fill_mode='BOTH'
    curve.extrude=depth/2; curve.bevel_depth=bevel; curve.bevel_resolution=4; curve.resolution_u=12
    polys=contours(commands)
    for poly in polys:
        level=sum(inside(poly[0],p) for p in polys if p is not poly)
        area=sum(x1*y2-x2*y1 for (x1,y1),(x2,y2) in zip(poly,poly[1:]+poly[:1]))
        if (area>0)!=(level%2==0): poly=list(reversed(poly))
        s=curve.splines.new('POLY'); s.points.add(len(poly)-1)
        for p,(x,y) in zip(s.points,poly): p.co=((x-center[0])*scale,(center[1]-y)*scale,0,1)
        s.use_cyclic_u=True
    o=bpy.data.objects.new(name,curve); col.objects.link(o); o.location.z=z; o.data.materials.append(material)
    return o
def cube(name,loc,dim,material,col,bevel=.1):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=link(bpy.context.object,col); o.name=name
    o.dimensions=dim; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    m=o.modifiers.new('Editable soft edge','BEVEL'); m.width=bevel; m.segments=6
    o.modifiers.new('Face normals','WEIGHTED_NORMAL'); o.data.materials.append(material)
    for p in o.data.polygons:p.use_smooth=True
    return o
def sphere(name,loc,scale,material,col):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=32,location=loc)
    o=link(bpy.context.object,col); o.name=name; o.scale=scale; o.data.materials.append(material)
    for p in o.data.polygons:p.use_smooth=True
    return o
def camera(name,loc,target,ortho,col):
    data=bpy.data.cameras.new(name); data.type='ORTHO'; data.ortho_scale=ortho
    o=bpy.data.objects.new(name,data); col.objects.link(o); o.location=loc; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    if not name.startswith('Buddy'):
        forward=(Vector(target)-o.location).normalized(); right=forward.cross(Vector((0,1,0))).normalized(); up=right.cross(forward)
        o.rotation_euler=Matrix((right,up,-forward)).transposed().to_euler()
    return o
def area(name,loc,target,power,size,col):
    d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.shape='DISK'; d.size=size
    o=bpy.data.objects.new(name,d); col.objects.link(o); o.location=loc; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def scene(name):
    s=bpy.data.scenes.new(name); bpy.context.window.scene=s
    s.render.engine='CYCLES'; s.cycles.samples=64; s.cycles.use_denoising=True
    s.render.resolution_x=1600; s.render.resolution_y=1200; s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG'; s.render.image_settings.color_mode='RGBA'
    s.view_settings.view_transform='AgX'; s.view_settings.look='AgX - Medium High Contrast'; s.view_settings.exposure=-.65
    s.world=bpy.data.worlds.new(name+' world'); s.world.use_nodes=True
    s.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.7,.8,1)
    s.world.node_tree.nodes['Background'].inputs[1].default_value=.2
    studio=collection('90 | Studio - hide for transparent cutout'); lights=collection('91 | Light rig'); cams=collection('92 | Cameras')
    cube('Backdrop', (0,0,-.3),(200,200,.2),paper,studio,.01)
    area('Key - broad softbox',(-3,-4,7),(0,0,0),500,5,lights)
    area('Fill - cool bounce',(4,1,5),(0,0,0),220,4,lights)
    area('Rim - long highlight',(0,5,4),(0,0,0),340,3,lights)
    return s,cams

# Each product owns its objects; scenes can be edited independently.
s,cams=scene('01 | Plate studio'); col=collection('01 | Plate - shared vector geometry')
shape('Plate | chamfered foundation',G['plate'],col,blue,depth=.22,bevel=.026,z=.05)
shape('89 | raised ceramic inlay',G['eight']+G['nine'],col,ivory,depth=.045,bevel=.012,z=.194)
s.camera=camera('Hero | badge perspective',(2,-3.0,10),(0,0,.05),5.8,cams)
camera('Front | orthographic master',(0,0,10),(0,0,0),5.5,cams)
s['description']='Raised ceramic numerals; plate and counters derive from source/geometry.json.'

# Rounded app tile, with an inverse plate cut from the same paths.
sys.path.insert(0,str(ROOT/'source'))
# rr defined locally so rebuilding .blend needs only standard Python and JSON.
def rounded(w,h,r):
    pts=[]
    for cx,cy,start in [(w/2-r,-h/2+r,-90),(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180)]:
        for i in range(17):
            t=math.radians(start+i*90/16); pts.append((cx+r*math.cos(t),cy+r*math.sin(t)))
    return [('moveTo',[pts[0]])]+[('lineTo',[p]) for p in pts[1:]]+[('closePath',[])]
s,cams=scene('02 | Offgrid tile'); col=collection('01 | Tile and recessed plate')
shape('Tile | molded blue shell',rounded(4,4,.76),col,blue,scale=1,center=(0,0),depth=.32,bevel=.11,z=.04)
shape('Plate | ceramic face with recessed 89',G['plate']+G['eight']+G['nine'],col,ivory,scale=.015,depth=.10,bevel=.028,z=.35)
s.camera=camera('Hero | app tile',(.65,-1.1,12),(0,0,.1),5.8,cams)
camera('Front | app tile',(0,0,12),(0,0,.1),5.4,cams)
s['description']='Presentation object. Full-bleed app artwork is provided in the next scene.'

s,cams=scene('03 | Offgrid icon master'); col=collection('01 | Full bleed icon')
cube('Unmasked blue field',(0,0,0),(20,20,.18),blue,col,.01)
shape('Plate | inverse relief',G['plate']+G['eight']+G['nine'],col,ivory,scale=.0124,depth=.065,bevel=.019,z=.16)
s.camera=camera('App export | front',(0,0,12),(0,0,0),4,cams)
s.render.resolution_x=s.render.resolution_y=1024
s['description']='Opaque square master. Plate occupies 62% width; masks applied by the host platform.'

s,cams=scene('05 | Origin89 signature'); col=collection('01 | Signature - editable outline curves')
w=G['words']['Origin89']; total=244+w['width']*1.05
badge=shape('Signature | blue plate',G['plate'],col,blue,scale=.01,center=(0,55),depth=.15,bevel=.015,z=.02);badge.location.x=-total*.005
digits=shape('Signature | 89',G['eight']+G['nine'],col,ivory,scale=.01,center=(0,55),depth=.025,bevel=.005,z=.119);digits.location.x=-total*.005
word=shape('Signature | Origin89 outlined',w['commands'],col,ink,scale=.0105,center=(0,w['height']/2),depth=.10,bevel=.005,z=.005);word.location.x=-total*.005+2.44
s.camera=camera('Signature | hero',(1,-3,12),(0,0,0),8.0,cams)
s['description']='Three-dimensional horizontal signature using the same optically weighted wordmark as SVG delivery.'

notes='ORIGIN89 / PLATE 89 / BRAND SOURCE v1.0\n\nFour editable scenes: plate, tile, icon and signature.\nBuddy is stored separately in docs/brand/buddy/blender/buddy.blend.\nAll character renderers resolve docs/brand/buddy-source.json.\n\nThe plate, numerals and outlined wordmark use source/geometry.json.\nThe build script requires --overwrite to replace a saved studio.\nrender_brand.py renders the saved files without changing them.\n'
bpy.data.texts.new('START HERE | Origin89 brand').write(notes)
bpy.data.texts.new('geometry.json | vector source snapshot').write(json.dumps(G,indent=2))
for dead in list(bpy.data.scenes):
    if dead.name=='Scene': bpy.data.scenes.remove(dead)
bpy.context.window.scene=bpy.data.scenes['02 | Offgrid tile']
for screen in bpy.data.screens:
    for area_ in screen.areas:
        if area_.type=='VIEW_3D':
            area_.spaces.active.region_3d.view_perspective='CAMERA'
            area_.spaces.active.shading.type='MATERIAL'
bpy.ops.file.pack_all()
a.output.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(a.output.resolve()))
print('BRAND_SOURCE_SAVED',a.output)
