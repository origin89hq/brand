"""Render the canonical Buddy in a cedar canoe over the approved KM43 lake plate.

The character, canoe, paddle, vest, lights and reflection surface are native 3D.
The cottage-inspired environment is a generated, packed 2D background plate.
Neither canonical Buddy input is modified. Run with Blender; see the scene README.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT / 'situations/scenes/km43-canoe'
sys.path.insert(0,str(Path(__file__).resolve().parent))
from km43_craft import craft
sys.path.insert(0, str(ROOT / 'buddy/blender'))
from studio import configure, expression, avatar, device
from finish import render_quality


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgba(hex):
    v = [int(hex[i:i+2], 16)/255 for i in (1, 3, 5)]
    return tuple(x/12.92 if x <= .04045 else ((x+.055)/1.055)**2.4 for x in v)+(1,)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--width', type=int, default=2560)
    parser.add_argument('--samples', type=int, default=192)
    parser.add_argument('--draft', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    out = ROOT / '.build/km43-canoe' if args.draft else SCENE
    out.mkdir(parents=True, exist_ok=True)
    master = ROOT / 'buddy/blender/buddy.blend'
    presentation = ROOT / 'buddy/presentation/face-front.blend'
    input_hashes = {str(p.relative_to(ROOT)): sha(p) for p in (master, presentation)}
    assert json.loads((presentation.parent/'face-front-source.json').read_text())['base_sha256'] == sha(master)
    bpy.ops.wm.open_mainfile(filepath=str(master))
    configure(bpy.context.scene, True)
    expression(bpy.context.scene, 'welcoming', pose='standing')
    avatar(bpy.context.scene, 'welcoming', isolated=False)
    rig = bpy.data.objects['Buddy | pose rig']
    rig.animation_data.action = None
    body_pose = {b.name:b.matrix_basis.copy() for b in rig.pose.bones}
    bpy.ops.wm.open_mainfile(filepath=str(presentation))
    scene = bpy.context.scene
    scene.name = 'KM43 | Buddy canoe render'
    layer = configure(scene, True)
    rig = bpy.data.objects['Buddy | pose rig']
    rig.animation_data.action = None
    for name, mat in body_pose.items():
        rig.pose.bones[name].matrix_basis = mat
    for k,v in {'jaw_open':.035,'smile':.48,'tongue_out':0,'brow_raise_L':.16,'brow_raise_R':.10,'lower_lid_L':.09,'lower_lid_R':.12}.items():
        rig['face_'+k] = v
    rig.update_tag()
    bpy.context.view_layer.update()

    def point(name, direction):
        bone = rig.pose.bones[name]
        old = bone.matrix.copy()
        axis = (old.to_quaternion()@Vector((0,1,0))).normalized()
        mat = axis.rotation_difference(Vector(direction).normalized()).to_matrix().to_4x4()@old
        mat.translation = old.translation
        bone.matrix = mat
        bpy.context.view_layer.update()

    # Forward paddling: left hoof on the top grip, right hoof beside the seat.
    # Coordinates are character-local; the placement control faces Buddy to bow.
    wrists = {'L':Vector((.10,-.44,1.50)), 'R':Vector((-.76,-.34,.99))}
    for side, wrist in wrists.items():
        upper = rig.pose.bones['upper_arm.'+side]
        lower = rig.pose.bones['forearm.'+side]
        shoulder = upper.head.copy()
        delta = wrist-shoulder
        distance, axis = delta.length, delta.normalized()
        assert abs(upper.length-lower.length) < distance < upper.length+lower.length
        along = (upper.length**2-lower.length**2+distance**2)/(2*distance)
        bend = Vector((1 if side=='L' else -1,0,-.3))
        bend = (bend-axis*bend.dot(axis)).normalized()
        elbow = shoulder+axis*along+bend*math.sqrt(upper.length**2-along**2)
        point(upper.name, elbow-shoulder)
        point(lower.name, wrist-elbow)
        point('hand.'+side, (0,-1,-.35))
    for side in ('L','R'):
        point('thigh.'+side, (.15 if side=='L' else -.15,-1,-.1))
        point('shin.'+side, (0,.1,-1))
        point('foot.'+side, (0,-1,-.25))
    root = rig.pose.bones['root']
    mat = root.matrix.copy()
    mat.translation.z -= .22
    root.matrix = mat
    head=rig.pose.bones['head']
    head_matrix=head.matrix.copy()
    turned=Matrix.Rotation(math.radians(-15),4,'Z')@head_matrix
    turned.translation=head_matrix.translation
    head.matrix=turned
    head.rotation_euler[2] += math.radians(-5)
    rig.update_tag()
    bpy.context.view_layer.update()
    scene.frame_start = scene.frame_end = 1
    scene.frame_set(1)
    scene.timeline_markers.clear()
    scene.timeline_markers.new('Static canoe pose',frame=1)
    bpy.data.objects['Presentation | seamless sweep'].hide_render = True
    for o in scene.objects:
        if o.type=='LIGHT':
            o.hide_render = True
    placement=bpy.data.objects.new('Buddy | middle seat placement',None)
    scene.collection.objects.link(placement)
    placement.empty_display_type='PLAIN_AXES'
    placement.empty_display_size=.4
    character_roots=[o for o in scene.objects if not o.parent and o.type in ('MESH','CURVES','CURVE','ARMATURE') and not o.name.startswith(('Studio |','Presentation |'))]
    for o in character_roots:
        o.parent=placement
    placement.rotation_euler.z=math.pi/2
    placement.location=(0,0,0)
    bpy.context.view_layer.update()

    props = bpy.data.collections.new('KM43 | editable canoe and paddle')
    scene.collection.children.link(props)
    palette_path = ROOT/'identity/tokens/brand-tokens.json'
    palette = json.loads(palette_path.read_text())

    def material(name, color, roughness=.5, metallic=0):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bs = m.node_tree.nodes.get('Principled BSDF')
        bs.inputs['Base Color'].default_value = rgba(color)
        bs.inputs['Roughness'].default_value = roughness
        bs.inputs['Metallic'].default_value = metallic
        return m

    cedar = material('Canoe | varnished cedar grain','#a85c27',.28)
    nodes, links = cedar.node_tree.nodes, cedar.node_tree.links
    tex = nodes.new('ShaderNodeTexCoord')
    mapping = nodes.new('ShaderNodeVectorMath'); mapping.operation='MULTIPLY'
    mapping.inputs[1].default_value=(1.4,95,95)
    links.new(tex.outputs['Generated'],mapping.inputs[0])
    noise=nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=4
    noise.inputs['Detail'].default_value=3
    links.new(mapping.outputs[0],noise.inputs['Vector'])
    ramp=nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position=.18; ramp.color_ramp.elements[0].color=rgba('#3d1708')
    ramp.color_ramp.elements[1].position=.82; ramp.color_ramp.elements[1].color=rgba('#a56529')
    links.new(noise.outputs['Fac'],ramp.inputs[0])
    links.new(ramp.outputs[0],nodes['Principled BSDF'].inputs['Base Color'])
    bump=nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.13; bump.inputs['Distance'].default_value=.004
    links.new(noise.outputs['Fac'],bump.inputs['Height']); links.new(bump.outputs[0],nodes['Principled BSDF'].inputs['Normal'])
    nodes['Principled BSDF'].inputs['Coat Weight'].default_value=.32
    ash=material('Canoe | pale ash ribs and paddle','#c49760',.36)
    darkwood=material('Canoe | dark walnut gunwales','#39271e',.29)
    blue=material('Vest | Origin89 bridge blue',palette['brand']['blue'],.82)
    navy=material('Vest | binding and webbing',palette['materials_3d']['shell'],.9)
    buckle=material('Vest | charcoal buckles',palette['themes']['dark']['line-strong'],.6)
    metal=material('Canoe | brass fasteners','#9e8558',.3,.8)
    for m in (blue,navy):
        n=m.node_tree.nodes; l=m.node_tree.links
        noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=230
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.15;bump.inputs['Distance'].default_value=.001
        l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],n['Principled BSDF'].inputs['Normal'])

    def finish(obj,name,mat,bevel=0):
        for c in list(obj.users_collection):c.objects.unlink(obj)
        props.objects.link(obj);obj.name=name
        obj.data.materials.append(mat)
        if bevel:
            mod=obj.modifiers.new('Soft edges','BEVEL');mod.width=bevel;mod.segments=4
        if obj.type=='MESH':
            for p in obj.data.polygons:p.use_smooth=True
        return obj

    def mesh(name,verts,faces,mat):
        data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
        obj=bpy.data.objects.new(name,data);props.objects.link(obj);data.materials.append(mat)
        for p in data.polygons:p.use_smooth=True
        return obj

    def box(name,pos,dim,mat,bevel=.02):
        bpy.ops.mesh.primitive_cube_add(size=1,location=pos)
        obj=bpy.context.object;obj.dimensions=dim
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        return finish(obj,name,mat,bevel)

    def rail(name,points,radius,mat):
        data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.bevel_depth=radius;data.bevel_resolution=4
        s=data.splines.new('POLY');s.points.add(len(points)-1)
        for p,v in zip(s.points,points):p.co=(*v,1)
        obj=bpy.data.objects.new(name,data);props.objects.link(obj);data.materials.append(mat)
        return obj

    def hull(t,a):
        # The stern retains width and a level rim; only the bow tapers to a point.
        shape=t if t>=0 else t*.75
        w=.69*max(0,1-shape*shape)**.72+.008
        top=.60+.17*max(t,0)**4
        depth=.80-.08*max(t,0)**4
        return (2.22*t,w*math.cos(a),top-depth*math.sin(a)**.8)

    N,M=100,36
    verts=[hull(-1+2*i/N,math.pi*j/M) for i in range(N+1) for j in range(M+1)]
    faces=[(i*(M+1)+j,(i+1)*(M+1)+j,(i+1)*(M+1)+j+1,i*(M+1)+j+1) for i in range(N) for j in range(M)]
    obj=mesh('Canoe | cedar hull',verts,faces,cedar)
    mod=obj.modifiers.new('Real cedar shell thickness','SOLIDIFY');mod.thickness=.026
    mod=obj.modifiers.new('Varnished edges','BEVEL');mod.width=.008;mod.segments=3
    stern_points=[hull(-1,math.pi*j/M) for j in range(M+1)]
    transom=mesh('Canoe | flat stern transom',stern_points,[tuple(range(M,-1,-1))],cedar)
    mod=transom.modifiers.new('Solid transom board','SOLIDIFY');mod.thickness=.045
    mod=transom.modifiers.new('Transom edges','BEVEL');mod.width=.009;mod.segments=3
    rail('Canoe | straight stern cap',[hull(-1,0),hull(-1,math.pi)],.029,darkwood)
    for a in (0,math.pi):
        rail('Canoe | walnut gunwale', [hull(-1+2*i/160,a) for i in range(161)],.026,darkwood)
    for i in range(1,21):
        t=-1+2*i/21
        points=[Vector(hull(t,math.pi*j/48)) for j in range(49)]
        for p in points:p.y*=.97;p.z+=.018
        rail('Canoe | ash rib %02d'%i,points,.011,ash)
    for j in range(1,12):
        rail('Canoe | cedar strip seam %02d'%j,[hull(-.985+1.97*i/100,math.pi*j/12) for i in range(101)],.002,darkwood)
    for x in (0,):
        box('Canoe | bench seat',(x,0,.25),(.30,1.10,.045),ash,.012)
    for x in (-1.90,1.90):
        box('Canoe | end thwart',(x,0,.43 if x<0 else .63),(.16,.82 if x<0 else .32,.025),ash,.01)

    # Fitted foam panels wrap around the existing torso; the character is unchanged.
    for sign in (-1,1):
        obj=box('Vest | front foam panel', (sign*.215,-.295,.81),(.36,.21,.59),blue,.105)
        obj.rotation_euler[1]=sign*math.radians(-7)
        rail('Vest | shoulder binding',[(sign*.29,-.30,.83),(sign*.28,-.25,1.10),(sign*.29,-.09,1.18),(sign*.30,.20,1.07),(sign*.30,.26,.70)],.065,navy)
        rail('Vest | panel piping',[(sign*.08,-.412,.55),(sign*.08,-.413,.95),(sign*.15,-.36,1.10)],.009,navy)
    box('Vest | back foam',(0,.26,.80),(.66,.16,.51),blue,.09)
    for z in (.62,.83):
        box('Vest | front strap',(0,-.417,z),(.74,.023,.045),navy,.008)
        box('Vest | buckle',(0,-.440,z),(.115,.038,.074),buckle,.012)
        box('Vest | buckle slot',(0,-.463,z),(.066,.01,.025),navy,.003)

    for o in props.objects:
        if o.name.startswith('Vest |'):o.parent=placement
    high=placement.matrix_world@(wrists['L']+Vector((0,-.105,-.265)))
    low=placement.matrix_world@(wrists['R']+Vector((0,-.105,-.265)))
    direction=(low-high).normalized()
    shaft_start,shaft_end=high-direction*.06,low+direction*1.0
    rail('Paddle | ash shaft',[shaft_start,shaft_end],.022,ash)
    grip=high-direction*.06
    rail('Paddle | T grip',[grip+Vector((-.072,0,0)),grip+Vector((.072,0,0))],.028,ash)
    center=low+direction*1.08
    # Flat elongated ottertail blade, with a rounded end and proper thickness.
    profile=[(-.024,-.28),(.024,-.28),(.11,-.12),(.135,.15),(.095,.37),(0,.43),(-.095,.37),(-.135,.15),(-.11,-.12)]
    tangent=direction.cross(Vector((0,0,1))).normalized()
    blade_normal=direction.cross(tangent).normalized()
    v=[tuple(center+tangent*u+direction*t+blade_normal*d) for d in (-.012,.012) for u,t in profile]
    count=len(profile)
    f=[tuple(range(count-1,-1,-1)),tuple(range(count,2*count))]+[(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
    blade=mesh('Paddle | shaped ottertail blade',v,f,ash)
    mod=blade.modifiers.new('Rounded paddle edge','BEVEL');mod.width=.026;mod.segments=4

    # A Cycles reflection catcher integrates the real canoe with the lake plate.
    water=material('Lake | reflection catcher','#bac7ce',.045,1.0)
    bs=water.node_tree.nodes['Principled BSDF']
    bs.inputs['IOR'].default_value=1.333
    bs.inputs['Coat Weight'].default_value=.8
    n=water.node_tree.nodes;l=water.node_tree.links
    tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=9;tex.inputs['Detail'].default_value=2
    mapping=n.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(.7,3,1)
    coords=n.new('ShaderNodeTexCoord');l.new(coords.outputs['Object'],mapping.inputs[0]);l.new(mapping.outputs[0],tex.inputs['Vector'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.018
    l.new(tex.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,0))
    surface=finish(bpy.context.object,'Lake | editable reflection surface',water)
    surface.is_shadow_catcher=True

    def area(name,loc,power,color,size):
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.color=color;data.shape='DISK';data.size=size
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=loc
        obj.rotation_euler=(Vector((0,0,1))-obj.location).to_track_quat('-Z','Y').to_euler()
    area('Morning | soft sky rim',(-4,1,6),900,(.82,.90,1),5)
    area('Lake | broad sky fill',(1,-5,5),850,(.76,.86,1),6)
    area('Morning | shore bounce',(-4,-3,2.8),350,(.88,.92,1),4)
    scene.world.use_nodes=True
    world=scene.world.node_tree.nodes.get('Background')
    world.inputs['Color'].default_value=(.40,.48,.60,1)
    world.inputs['Strength'].default_value=.35
    camera=scene.camera
    camera.data.type='ORTHO';camera.data.ortho_scale=10.4
    target=Vector((-2.12,0,1.08))
    camera.location=target+Vector((3.8,-12,2.9))
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.resolution_x=args.width;scene.render.resolution_y=args.width//2;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='8'
    plate_path=SCENE/'assets/lake-cottage-shore-plate.png'
    plate_image=bpy.data.images.load(str(plate_path),check_existing=True);plate_image.pack()
    heading=math.radians(-40)
    boat_scale=.54
    boat_offset=Vector((-.35,1.1,0))
    shaft_start,shaft_end,v,paddle_contact=craft(scene,props,hull,high,low,plate_image,heading,boat_scale,boat_offset)
    render_quality(scene,args.samples)
    scene.cycles.adaptive_min_samples=min(32,args.samples)
    scene.cycles.adaptive_threshold=.035 if args.draft else .009
    scene.cycles.transparent_max_bounces=16
    device(scene)
    bpy.context.view_layer.update()
    graph=bpy.context.evaluated_depsgraph_get()
    hull_trees=[BVHTree.FromObject(bpy.data.objects[name],graph) for name in ('Canoe | cedar hull','Canoe | flat stern transom')]
    def hull_distance(p):
        return min(tree.find_nearest(p)[3] for tree in hull_trees)
    shaft_samples=[shaft_start.lerp(shaft_end,i/300) for i in range(301)]
    shaft_clearance=min(hull_distance(p) for p in shaft_samples)-.022
    blade_clearance=min(hull_distance(Vector(p)) for p in v)-.026
    rim_points=[Vector(hull(-1+2*i/500,a)) for a in (0,math.pi) for i in range(501)]
    rim_clearance=min((p-r).length for p in shaft_samples for r in rim_points)-.022-.026
    assert shaft_clearance>.015, 'Paddle shaft intersects the canoe hull'
    assert blade_clearance>.015, 'Paddle blade intersects the canoe hull'
    assert rim_clearance>.015, 'Paddle shaft intersects the gunwale'
    clearances={'shaft_to_hull':shaft_clearance,'blade_to_hull':blade_clearance,'shaft_to_gunwale':rim_clearance}
    # One heading control keeps the middle-seat pose, boat and paddle together.
    boat=bpy.data.objects.new('Canoe | heading and placement',None)
    scene.collection.objects.link(boat)
    placement.parent=boat
    for obj in props.objects:
        if not obj.parent and obj.name not in ('Lake | physical water and paddle ripples','Lake | editable reflection surface'):
            obj.parent=boat
    boat.rotation_euler.z=heading
    boat.scale=(boat_scale,)*3
    boat.location=boat_offset
    clearances={name:value*boat_scale for name,value in clearances.items()}
    bpy.context.view_layer.update()
    graph=bpy.context.evaluated_depsgraph_get()
    bounds={}
    for name in ('Antler | cupped palmate L','Antler | cupped palmate R','Canoe | cedar hull','Paddle | shaped ottertail blade'):
        obj=bpy.data.objects[name].evaluated_get(graph)
        pts=[world_to_camera_view(scene,camera,obj.matrix_world@Vector(c)) for c in obj.bound_box]
        bounds[name]={'x':[min(p.x for p in pts),max(p.x for p in pts)],'y':[min(p.y for p in pts),max(p.y for p in pts)]}
        assert all(.03 < v < .97 for axis in bounds[name].values() for v in axis), name+' is clipped'
    assert all(abs(v-1)<.001 for b in rig.pose.bones for v in b.matrix.to_scale()), 'Pose must not scale the character bones'
    scene['km43_source']='Canonical Buddy with native canoe, vest, paddle and lake reflection; generated 2D environment plate.'
    scene['km43_rebuild']='blender -b --python-exit-code 1 --python situations/source/build_km43_canoe.py -- --width 2560 --samples 192'
    for path,expected in input_hashes.items():assert sha(ROOT/path)==expected
    native=out/'buddy-canoe-transparent.png'
    linear_render=ROOT/'.build/km43-canoe-linear.exr'
    scene.render.image_settings.file_format='OPEN_EXR';scene.render.image_settings.color_depth='16'
    scene.render.filepath=str(linear_render)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'),compress=True)
    print('KM43_CHECKS',json.dumps({'bounds':bounds,'paddle_clearance_m':clearances,'device':scene.cycles.device}),flush=True)
    bpy.ops.render.render(write_still=True,layer=layer.name)
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_depth='8'
    bpy.data.images['Render Result'].save_render(str(native),scene=scene)

    # A live Render Layers input keeps F12 editable, with one shared color grade.
    group=bpy.data.node_groups.new('KM43 | lake plus actual Buddy','CompositorNodeTree')
    group.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
    scene.compositing_node_group=group
    n,l=group.nodes,group.links
    bg=n.new('CompositorNodeImage');bg.image=plate_image;bg.label='Soft stylized environment (2D)'
    scale=n.new('CompositorNodeScale');scale.inputs['Type'].default_value='Render Size';scale.inputs['Frame Type'].default_value='Stretch';l.new(bg.outputs['Image'],scale.inputs['Image'])
    fg=n.new('CompositorNodeRLayers');fg.scene=scene;fg.layer=layer.name;fg.label='Live native character, props and water'
    over=n.new('CompositorNodeAlphaOver');over.inputs['Factor'].default_value=1;l.new(scale.outputs['Image'],over.inputs['Background']);l.new(fg.outputs['Image'],over.inputs['Foreground'])
    output=n.new('NodeGroupOutput');l.new(over.outputs[0],output.inputs[0])
    for node,pos in ((bg,(-600,100)),(scale,(-350,100)),(fg,(-350,-180)),(over,(-80,80)),(output,(180,80))):node.location=pos
    scene.render.filepath=str(out/'km43-social.png')
    bpy.ops.render.render(write_still=True,layer=layer.name)
    camera.data.show_background_images=True
    plate=camera.data.background_images.new();plate.image=bg.image;plate.alpha=1;plate.display_depth='BACK'
    bpy.context.window.scene=scene
    bpy.context.window.view_layer=layer
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA'
                area.spaces.active.overlay.show_overlays=False
    note=bpy.data.texts.new('READ ME | KM43 canoe')
    note.write('Actual Buddy geometry, fur, face and rig derive from the canonical brand sources.\n'
               'Canoe, paddle, vest, lighting and reflection surface are native editable 3D.\n'
               'The lake and km marker are the packed generated environment plate.\n'
               'F12 renders the live character, props and water over the packed lake plate.\n'
               'Persistent, reproducible edits belong in situations/source/build_km43_canoe.py and its helpers.\n'
               'See situations/scenes/km43-canoe/README.md for rebuilding and provenance.\n')
    scene.render.filepath='//km43-social.png'
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'),compress=True)
    for path,expected in input_hashes.items():assert sha(ROOT/path)==expected
    recipes=[Path(__file__),Path(__file__).with_name('km43_craft.py'),Path(__file__).with_name('km43_vest.py')]
    provenance={
        'base':'buddy/blender/buddy.blend','base_sha256':sha(master),'inputs':input_hashes,
        'recipe':'situations/source/build_km43_canoe.py','recipe_sha256':sha(Path(__file__)),
        'source_files':{str(p.relative_to(ROOT)):sha(p) for p in recipes},
        'palette_sha256':sha(palette_path),
        'environment':str(plate_path.relative_to(SCENE)),'environment_sha256':sha(plate_path),
        'environment_type':'generated raster plate based on user-provided cottage shore reference',
        'native_character':True,'native_props':True,'live_compositor':True,'static_pose':True,
        'composition':'KM43 marker and lake first, Buddy canoeing as a secondary detail',
        'canoe_heading_degrees':math.degrees(heading),'canoe_uniform_scale':boat_scale,
        'canoe_offset':list(boat_offset),
        'width':args.width,'height':args.width//2,'samples':args.samples,
        'framing':bounds,'paddle_clearance_m':clearances,
        'files':{p.name:sha(p) for p in (native,out/'km43-social.png',out/'scene.blend')},
    }
    (out/'scene.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print('KM43_COMPLETE',out/'km43-social.png',flush=True)


if __name__=='__main__':
    main()
