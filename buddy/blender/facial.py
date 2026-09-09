"""Native moose facial controls, attached fur and keyed expression studies."""
import json
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from dental import gum_mesh
from fur import UV_NAME

PRESETS = {
    'neutral': {'frame': 1},
    'smile': {'frame': 110, 'smile': .85, 'jaw_open': .28, 'lip_raise': .40,
              'lip_lower': .40, 'brow_raise_L': .15, 'brow_raise_R': .15,
              'lower_lid_L': .15, 'lower_lid_R': .15},
    'delighted': {'frame': 140, 'smile': 1., 'jaw_open': .75, 'lip_raise': .65,
                  'lip_lower': .65, 'brow_raise_L': .35, 'brow_raise_R': .35,
                  'upper_lid_L': .20, 'upper_lid_R': .20,
                  'lower_lid_L': .40, 'lower_lid_R': .40},
    'surprised': {'frame': 170, 'jaw_open': .70, 'lip_raise': .35,
                  'brow_raise_L': .85, 'brow_raise_R': .85},
    'concerned': {'frame': 200, 'smile': -.55, 'brow_tilt_L': .75,
                  'brow_tilt_R': .75, 'upper_lid_L': .12, 'upper_lid_R': .12},
    'wink': {'frame': 230, 'smile': .60, 'jaw_open': .12, 'blink_L': 1.,
             'brow_raise_R': .35, 'brow_tilt_R': -.25},
    'blink': {'frame': 260, 'blink_L': 1., 'blink_R': 1.},
    'playful': {'frame': 290, 'smile': .65, 'smile_L': .25, 'jaw_open': .55,
                'lip_raise': .25, 'lip_lower': .35, 'tongue_out': 1.,
                'tongue_curl': .75, 'tongue_side': -.15, 'tongue_twist': -.10,
                'lower_lid_L': .25, 'lower_lid_R': .20, 'brow_raise_R': .25,
                'cheek_raise_L': .4, 'muzzle_scrunch': .25},
    'tongue-peek': {'frame': 350, 'smile': .25, 'jaw_open': .48,
                    'tongue_out': .85, 'tongue_curl': -.25, 'tongue_widen': .15,
                    'lip_press': .65,
                    'lower_lid_L': .14, 'lower_lid_R': .18,
                    'brow_raise_L': .12, 'brow_raise_R': .20},
    'skeptical': {'frame': 320, 'smile_L': .65, 'smile_R': -.3,
                  'brow_raise_L': .55, 'brow_tilt_R': -.5,
                  'upper_lid_R': .42, 'cheek_raise_L': .35},
}
CONTROLS = {'jaw_open': (0, 1), 'smile': (-1, 1), 'lip_raise': (0, 1), 'lip_lower': (0, 1)}
CONTROLS.update({'smile_L': (-1,1), 'smile_R': (-1,1), 'cheek_raise_L': (0,1),
                 'cheek_raise_R': (0,1), 'muzzle_scrunch': (0,1), 'tongue_out': (0,1),
                 'tongue_curl': (-1,1), 'tongue_side': (-1,1),
                 'tongue_twist': (-1,1), 'tongue_widen': (-1,1)})
CONTROLS.update({'lip_press': (0,1), 'lip_pucker': (-1,1)})
for side in ('L', 'R'):
    CONTROLS.update({f'blink_{side}': (0, 1), f'upper_lid_{side}': (0, 1),
                     f'lower_lid_{side}': (0, 1), f'brow_raise_{side}': (-1, 1),
                     f'brow_tilt_{side}': (-1, 1)})


def key_expression(scene, rig, name, neutral_pose):
    """Store a preset on the existing rig without rebuilding its geometry."""
    preset = PRESETS[name]
    frame = preset['frame']; scene.frame_set(frame)
    if frame > 80:
        for bone in rig.pose.bones:
            if bone.name == 'jaw': continue
            bone.matrix_basis = neutral_pose[bone.name]
            bone.keyframe_insert(data_path='location', frame=frame)
            bone.keyframe_insert(data_path='rotation_euler', frame=frame)
    for control in CONTROLS:
        rig['face_' + control] = float(preset.get(control, 0))
        rig.keyframe_insert(data_path=f'["face_{control}"]', frame=frame)
    if frame > 80:
        marker = scene.timeline_markers.get('Face | ' + name)
        if marker: marker.frame = frame
        else: scene.timeline_markers.new('Face | ' + name, frame=frame)


def drive(target, path, rig, expression, properties, index=None):
    fc = target.driver_add(path) if index is None else target.driver_add(path, index)
    d = fc.driver; d.type = 'SCRIPTED'; d.expression = expression
    for name, prop in properties.items():
        v = d.variables.new(); v.name = name; v.type = 'SINGLE_PROP'
        v.targets[0].id = rig; v.targets[0].data_path = f'["face_{prop}"]'


def mesh_object(name, vertices, faces, collection, mat):
    mesh = bpy.data.meshes.new(name); mesh.from_pydata(vertices, [], faces); mesh.update()
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new(name, mesh); collection.objects.link(obj)
    mesh.materials.append(mat)
    for face in mesh.polygons: face.use_smooth = True
    return obj


def morph(obj, name, positions, rig, prop=None, expression='v', properties=None, minimum=0):
    if obj.data.shape_keys is None: obj.shape_key_add(name='Basis')
    key = obj.shape_key_add(name=name); key.slider_min = minimum
    key.data.foreach_set('co', np.asarray(positions, dtype=np.float32).reshape(-1))
    drive(key, 'value', rig, expression, properties or {'v': prop})
    return key


def current_world(obj):
    return [obj.matrix_world @ v.co for v in obj.data.vertices]


def upper_eyelashes(lid, side, sign, rotation, collection, mat):
    """Four tapered lashes attached to the actual deforming upper-lid surface."""
    mesh=lid.data; mesh.calc_loop_triangles()
    uv_layer=mesh.uv_layers[UV_NAME]
    points=[]; radii=[]; attachment=[]; stride=9
    inverse=lid.matrix_world.inverted().to_3x3()
    for u,length in zip((.36,.53,.68,.80),(.023,.031,.037,.030)):
        vertex=round((sign*u+.9999)/1.9998*64)*13
        triangle=next(t for t in mesh.loop_triangles if vertex in t.vertices)
        index=list(triangle.vertices).index(vertex)
        # Move just inside the atlas triangle to keep the root binding stable.
        root=mesh.vertices[vertex].co*.998+sum((mesh.vertices[i].co for i in triangle.vertices),Vector())*(.002/3)
        root_uv=uv_layer.data[triangle.loops[index]].uv*.998
        root_uv+=sum((uv_layer.data[i].uv for i in triangle.loops),Vector((0,0)))*(.002/3)
        attachment.extend(root_uv)
        for t in np.linspace(0,1,stride):
            direction=inverse@(rotation@Vector((sign*.45*t,-.82*t,.18*t+.55*t*t)))
            points.extend(root+length*direction)
            radii.append(.00125*(1-t)**.85+.000025)
    data=bpy.data.hair_curves.new('Groom | upper eyelashes '+side)
    data.add_curves([stride]*4)
    data.attributes['position'].data.foreach_set('vector',points)
    data.attributes.new('radius','FLOAT','POINT').data.foreach_set('value',radii)
    data.attributes.new('surface_uv_coordinate','FLOAT2','CURVE').data.foreach_set('vector',attachment)
    data.materials.append(mat); data.surface=lid; data.surface_uv_map=UV_NAME
    obj=bpy.data.objects.new('Fur | upper eyelashes '+side,data); collection.objects.link(obj)
    obj.parent=lid; obj.matrix_basis=Matrix.Identity(4)
    mod=obj.modifiers.new('Follow eyelid blink and squint','NODES')
    mod.node_group=bpy.data.node_groups['Moose | curves follow skin']
    obj['strand_count']=4; obj['point_stride']=stride; obj['editable_native_curves']=True
    return 4


def install(scene, rig, head, jaw, cols, materials, groom, bind_rigid, coat_color, ellipsoid):
    scene.frame_set(1); bpy.context.view_layer.update()
    if 'face_jaw_open' in rig: raise RuntimeError('Facial controls already installed')
    z_offset = scene['head_height_offset']
    def p(x, y, z): return Vector((x, y, z-z_offset))
    neutral_pose = {b.name: b.matrix_basis.copy() for b in rig.pose.bones}
    for name, (minimum, maximum) in CONTROLS.items():
        prop = 'face_' + name; rig[prop] = 0.
        rig.id_properties_ui(prop).update(min=minimum, max=maximum,
                                         description=name.replace('_', ' '))
    drive(rig.pose.bones['jaw'], 'rotation_euler', rig, 'v*0.48', {'v': 'jaw_open'}, 0)

    # Teeth are real rigid geometry attached to the mandible, also visible in
    # the finished character layer. Lips conceal the crowns in the neutral face.
    teeth = [o for o in scene.objects if o.name.startswith('Tooth |')]
    for obj in teeth:
        cols['Features'].objects.link(obj)
        if 'cheek' in obj.name:
            # Keep the tooth row within the narrower finished mandible.
            points=current_world(obj); inverse=obj.matrix_world.inverted()
            center=sum(points,Vector())/len(points)
            for vertex,point in zip(obj.data.vertices,points):
                point.x=center.x*.70+(point.x-center.x)*.72
                if 'lower' in obj.name: point.z-=.020
                vertex.co=inverse@point
    old = bpy.data.objects.get('Mouth | interior')
    if old: bpy.data.objects.remove(old, do_unlink=True)

    # An open-front oral chamber has a skull-bound roof and a mandible-bound
    # floor. It stretches across the gape instead of floating with either lip.
    vertices = []; weights = []; faces = []; around = 80; rings = 15
    for row in range(rings):
        r = max(.015, row/(rings-1))
        for j in range(around):
            angle = 2*math.pi*j/around
            front_y=-.77+.40*math.cos(angle)**2
            jaw_weight=float(np.clip(.5-1.25*math.sin(angle), 0, 1))
            # Recess the chamber below the fitted mouth floor so its front
            # edge cannot cut through the lining when the soft lip rolls down.
            vertices.append(p(.180*r*math.cos(angle), -.06+(front_y+.06)*r,
                              2.115+.034*r*math.sin(angle)-.045*jaw_weight))
            weights.append(jaw_weight)
    for row in range(rings-1):
        for j in range(around):
            a = row*around+j; b = row*around+(j+1)%around
            faces.append((a, b, b+around, a+around))
    faces.append(tuple(reversed(range(around))))
    cavity_mat=simple_material('Moose | soft oral lining', '#291b1b', .95)
    cavity = mesh_object('Face | oral chamber', vertices, faces, cols['Features'], cavity_mat)
    bind_weighted(cavity, rig, weights)
    cavity['construction'] = 'Open-front oral chamber with head roof and jaw floor weights.'

    tongue_mat = simple_material('Moose | tongue and gum', '#9f6766', .68)
    gums_mat = simple_material('Moose | muted gums', '#76524a', .76)
    tongue = flexible_tongue(p,rig,cols['Features'],tongue_mat,bind_rigid,jaw)
    gum_points,gum_faces=gum_mesh()
    gum=mesh_object('Face | lower gum',[p(*point) for point in gum_points],gum_faces,cols['Features'],gums_mat)
    bind_rigid(gum, 'jaw')
    pad = ellipsoid('Face | upper dental pad', p(0,-.72,2.147), (.145,.065,.025), gums_mat, 'Features', segments=40)
    bind_rigid(pad, 'head')

    # Fit a hairless mouth floor to the actual mandible. Its lip keys match the
    # supporting jaw, so it cannot float above the lip when the lip rolls down.
    lining_mat=simple_material('Moose | inner cheek and mouth floor', '#583b37', .88)
    jaw_surface=BVHTree.FromPolygons(current_world(jaw),[tuple(f.vertices) for f in jaw.data.polygons])
    vertices=[]; faces=[]; across=33; along=49
    for i in range(along):
        t=i/(along-1); y=-.798+.748*t
        width=float(np.interp(y,[-.798,-.75,-.57,-.36,-.18,-.05],[.119,.132,.167,.180,.17,.10]))
        for j in range(across):
            u=-1+2*j/(across-1)
            edge_y=y+.043*u*u*(1-t)**5
            hit=jaw_surface.ray_cast(p(width*u,edge_y,2.50),Vector((0,0,-1)),1)[0]
            if hit is None: raise RuntimeError('Mouth floor leaves the mandible')
            hit.z+=.0015-.016*(1-t)**14; vertices.append(hit)
    for i in range(along-1):
        for j in range(across-1):
            a=i*across+j; faces.append((a,a+1,a+across+1,a+across))
    floor=mesh_object('Face | mouth floor',vertices,faces,cols['Features'],lining_mat)
    bind_rigid(floor,'jaw')
    # Mucosa blends into the rounded inner lip over a narrow boundary band.
    # A hard rectangular material edge would otherwise expose the lining patch.
    transition=lining_mat.copy(); transition.name='Moose | mouth lining to lip transition'
    floor.data.materials.clear(); floor.data.materials.append(transition)
    for attr_name,base,muzzle in [('lining_brown','#594132','#281c17'),('lining_navy','#20344e','#101b29')]:
        attr=floor.data.color_attributes.new(name=attr_name,type='FLOAT_COLOR',domain='POINT'); values=[]
        for i,point in enumerate(vertices):
            t=(i//across)/(along-1); u=-1+2*(i%across)/(across-1)
            edge=max(float(np.clip((abs(u)-.70)/.30,0,1)),float(np.clip(1-t/.11,0,1)))
            edge=edge*edge*(3-2*edge)
            muzzle_mix=float(np.clip((-point.y-.43)/.48,0,1))**1.4
            skin=np.array(rgba(base))*(1-muzzle_mix)+np.array(rgba(muzzle))*muzzle_mix
            values.extend(np.array(rgba('#583b37'))*(1-edge)+skin*edge)
        attr.data.foreach_set('color',values)
    nodes=transition.node_tree.nodes; links=transition.node_tree.links
    brown=nodes.new('ShaderNodeAttribute'); brown.attribute_name='lining_brown'
    navy=nodes.new('ShaderNodeAttribute'); navy.attribute_name='lining_navy'
    mix=nodes.new('ShaderNodeMixRGB'); links.new(navy.outputs['Color'],mix.inputs[1]); links.new(brown.outputs['Color'],mix.inputs[2])
    driver=mix.inputs[0].driver_add('default_value').driver; driver.expression='v'
    variable=driver.variables.new(); variable.name='v'; variable.type='SINGLE_PROP'
    variable.targets[0].id_type='SCENE'; variable.targets[0].id=scene; variable.targets[0].data_path='["coat_brown"]'
    links.new(mix.outputs[0],nodes['Principled BSDF'].inputs['Base Color'])

    # Shape keys move existing skin and its UV-attached hair. Tooth crowns keep
    # their actual shape and only follow their anatomical owner bone.
    for obj in (head, jaw, floor):
        points = np.asarray(current_world(obj)); design = points.copy(); design[:,2] += z_offset
        x,y,z = design.T; ax = np.abs(x)
        inverse = obj.matrix_world.inverted()
        corner = np.clip(ax/.24, 0, 1)**1.6
        band = np.exp(-((z-2.10)/.115)**2)*np.exp(-((y+.59)/.30)**2)
        values = points.copy(); values[:,0] += np.sign(x)*.028*corner*band
        values[:,2] += .064*corner*band
        for side,sign in [('L',1),('R',-1)]:
            mask=np.clip(.5+sign*x/.06,0,1)
            side_values=points+(values-points)*mask[:,None]
            morph(obj, 'Smile corner '+side, [inverse @ Vector(v) for v in side_values], rig,
                  expression='max(-1,min(1,m+v))',properties={'m':'smile','v':'smile_'+side},minimum=-1)
        if obj == head:
            band = np.exp(-((z-2.04)/.12)**2)*np.exp(-((y+.80)/.24)**2)
            values = points.copy(); values[:,2] += .085*band
            morph(obj, 'Upper lip lift', [inverse @ Vector(v) for v in values], rig, 'lip_raise')
            for side,sign in [('L',1),('R',-1)]:
                band=np.exp(-((x-sign*.29)/.115)**2-((y+.20)/.25)**2-((z-2.47)/.11)**2)
                values=points.copy(); values[:,2]+=.045*band; values[:,1]-=.016*band
                morph(obj,'Cheek lift '+side,[inverse@Vector(v) for v in values],rig,'cheek_raise_'+side)
            band=np.clip((-y-.36)/.65,0,1)**1.5
            values=points.copy(); values[:,1]+=.075*band; values[:,2]+=.035*band
            morph(obj,'Muzzle scrunch',[inverse@Vector(v) for v in values],rig,'muzzle_scrunch')
        else:
            # Translate each front lip cross-section together. Scaling its
            # upper vertices down would collapse it into a thin plate in profile.
            band = np.clip((-y-.51)/.30,0,1)
            values = points.copy(); values[:,2] -= .035*band
            morph(obj, 'Lower lip roll', [inverse @ Vector(v) for v in values], rig, 'lip_lower')
        band=np.exp(-((z-2.075)/.105)**2)*np.clip((-y-.32)/.43,0,1)
        values=points.copy(); values[:,2]+=(-.025 if obj==head else .045)*band
        morph(obj,'Lip press',[inverse@Vector(v) for v in values],rig,'lip_press')
        values=points.copy(); values[:,0]-=x*.20*band; values[:,1]-=.035*band
        morph(obj,'Lip pucker',[inverse@Vector(v) for v in values],rig,'lip_pucker',minimum=-1)

    # A continuous skin bridge seals the side of the mouth while the mandible
    # moves. The bridge is concealed by the resting head and cheek.
    added = 0
    for side, sign in [('L',1),('R',-1)]:
        vertices = []; weights = []; faces = []
        for row in range(13):
            t = row/12
            for j in range(17):
                u = j/16; y = -.62+.20*math.sin(math.pi*t)+.68*u
                width=(.185+.020*math.sin(math.pi*u))*(1-.8*u**4)
                top=2.24+.13*u; bottom=2.020+.13*u
                vertices.append(p(sign*width, y, top*(1-t)+bottom*t))
                weights.append(t)
        for row in range(12):
            for j in range(16):
                a=row*17+j; faces.append((a,a+1,a+18,a+17))
        cheek = mesh_object('Face | mouth corner tissue '+side, vertices, faces, cols['Skin'], materials['skin'])
        # Orient the open side sheet outward before sampling its hair.
        bm=bmesh.new(); bm.from_mesh(cheek.data)
        if sum(f.normal.x*sign for f in bm.faces)<0:
            bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
        bm.to_mesh(cheek.data); bm.free()
        coat_color(cheek); bind_weighted(cheek, rig, weights)
        added += groom(cheek,4200,.013,280+sign)
        # The new anatomy guides also track the side of the opening.
        cheek['construction'] = 'Head-to-jaw skin bridge at the mouth corner.'
        inner_points=[Vector((point[0]-sign*.004,point[1],point[2])) for point in vertices]
        lining=mesh_object('Face | inner cheek '+side,inner_points,faces,cols['Features'],lining_mat)
        bind_weighted(lining,rig,weights)
        for obj in (cheek,lining):
            points=np.asarray(current_world(obj)); x,y,z=points.T; z=z+z_offset
            corner=np.clip(np.abs(x)/.24,0,1)**1.6
            band=np.exp(-((z-2.10)/.115)**2)*np.exp(-((y+.59)/.30)**2)
            values=points.copy(); values[:,0]+=np.sign(x)*.028*corner*band; values[:,2]+=.064*corner*band
            inverse=obj.matrix_world.inverted()
            morph(obj,'Smile side tissue',[inverse@Vector(v) for v in values],rig,
                  expression='max(-1,min(1,m+v))',properties={'m':'smile','v':'smile_'+side},minimum=-1)
            band=np.exp(-((z-2.075)/.105)**2)*np.clip((-y-.32)/.43,0,1)
            values=points.copy(); values[:,2]+=.045*band*np.asarray(weights)
            morph(obj,'Lip press',[inverse@Vector(v) for v in values],rig,'lip_press')
            values=points.copy(); values[:,0]-=x*.20*band; values[:,1]-=.035*band
            morph(obj,'Lip pucker',[inverse@Vector(v) for v in values],rig,'lip_pucker',minimum=-1)

    # Fitted lids wrap the visible globe, with independent blink and squint.
    lid_mat = simple_material('Moose | eyelid skin', '#594132', .77)
    palette(lid_mat, scene, '#20344e', '#594132')
    crease_mat=simple_material('Moose | eyelid edge', '#3c2b21', .92)
    palette(crease_mat, scene, '#142639', '#3c2b21')
    lash_mat=simple_material('Moose | soft dark eyelashes','#2d1c13',.72)
    palette(lash_mat,scene,'#0e1825','#2d1c13')
    for side, sign in [('L',1),('R',-1)]:
        for old_name in ('Eye | upper lid '+side, 'Eye | lower lid '+side):
            old = bpy.data.objects.get(old_name)
            if old: bpy.data.objects.remove(old, do_unlink=True)
        eye = bpy.data.objects['Eye | globe '+side]
        center = eye.matrix_world.translation.copy(); rotation = eye.matrix_world.to_quaternion()
        radius = Vector((.111,.070,.124))
        for upper in (True,False):
            def lid_points(closed):
                result=[]
                for i in range(65):
                    u=-.9999+1.9998*i/64; cap=math.sqrt(max(0,1-u*u))
                    edge=(.88-.90*closed) if upper else (-.88+.86*closed)
                    start=math.asin(edge)
                    for j in range(13):
                        angle=start+((math.pi/2+.45)*(1 if upper else -1)-start)*j/12
                        local=Vector(((radius.x+.002)*u,
                                      -(radius.y+.002)*cap*math.cos(angle),
                                      (radius.z+.002)*cap*math.sin(angle)))
                        result.append(center+rotation@local)
                return result
            points=lid_points(0); faces=[]
            for i in range(64):
                for j in range(12):
                    a=i*13+j; faces.append((a,a+1,a+14,a+13))
            name='upper' if upper else 'lower'
            lid=mesh_object(f'Face | {name} eyelid {side}',points,faces,cols['Features'],lid_mat)
            bm=bmesh.new(); bm.from_mesh(lid.data)
            if sum(f.normal.dot(f.calc_center_median()-center) for f in bm.faces)<0:
                bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
            bm.to_mesh(lid.data); bm.free()
            bind_rigid(lid,'head')
            # Triangulate and establish the fur UV atlas before adding keys.
            added += groom(lid, 2600 if upper else 1800, .006, 320+sign+(0 if upper else 10))
            # The UV helper retains vertex order while triangulating faces.
            inverse=lid.matrix_world.inverted()
            morph(lid,'Close lid',[inverse@q for q in lid_points(1)],rig,
                  expression='max(b,s)',properties={'b':f'blink_{side}','s':f'{name}_lid_{side}'})
            dense=lid.modifiers.new('Continuous eyelid surface','SUBSURF'); dense.subdivision_type='SIMPLE'; dense.levels=1
            wrap=lid.modifiers.new('Fitted to cornea','SHRINKWRAP'); wrap.target=eye
            wrap.wrap_method='NEAREST_SURFACEPOINT'; wrap.wrap_mode='ABOVE_SURFACE'; wrap.offset=.0018
            lid['control']=f'face_blink_{side}, face_{name}_lid_{side}'
            if upper:
                # A fine lid margin keeps a readable closed-eye crease without
                # leaving a hole between the two fitted surfaces.
                def crease_points(closed):
                    result=[]
                    for i,point in enumerate(lid_points(closed)[::13]):
                        u=-.9999+1.9998*i/64
                        thickness=.0009*max(0,1-u*u)**.5
                        for j in range(8):
                            a=j*math.pi/4
                            result.append(point+rotation@Vector((0,-.0004+thickness*math.cos(a),thickness*math.sin(a))))
                    return result
                seam_faces=[]
                for i in range(64):
                    for j in range(8):
                        a=i*8+j; b=i*8+(j+1)%8; seam_faces.append((a,b,b+8,a+8))
                seam=mesh_object('Face | eyelid margin '+side,crease_points(0),seam_faces,cols['Features'],crease_mat)
                bind_rigid(seam,'head'); inverse=seam.matrix_world.inverted()
                morph(seam,'Close margin',[inverse@q for q in crease_points(1)],rig,
                      expression='max(b,s)',properties={'b':f'blink_{side}','s':f'upper_lid_{side}'})
                added+=upper_eyelashes(lid,side,sign,rotation,cols['Fur'],lash_mat)

    # Full, feathered brows stay fitted to the head while rising or tilting.
    # Their separate groom sweeps up and out, clear of the close forehead coat.
    surface=BVHTree.FromPolygons(current_world(head),[tuple(f.vertices) for f in head.data.polygons])
    def surface_y(x,z):
        hit=surface.ray_cast(Vector((x,-2,z)),Vector((0,1,0)),4)[0]
        if hit is None: raise RuntimeError('Eyebrow moved outside the head surface')
        return hit.y
    brow_material=simple_material('Moose | soft dark eyebrow roots','#483326',.86)
    palette(brow_material,scene,'#192a40','#483326')
    for side,sign in [('L',1),('R',-1)]:
        points=[]; faces=[]; around=12; rings=33
        for i in range(rings):
            t=i/(rings-1); x=sign*(.140+.225*t)
            z=2.744-z_offset-.064*t+.032*math.sin(math.pi*t)
            radius=.005+.020*math.sin(math.pi*t)**.55
            y=surface_y(x,z)-.015
            for j in range(around):
                a=j*2*math.pi/around; points.append(Vector((x,y+radius*.42*math.cos(a),z+radius*math.sin(a))))
        for i in range(rings-1):
            for j in range(around):
                a=i*around+j; b=i*around+(j+1)%around; faces.append((a,b,b+around,a+around))
        faces += [tuple(reversed(range(around))),tuple((rings-1)*around+i for i in range(around))]
        brow=mesh_object('Face | eyebrow '+side,points,faces,cols['Features'],brow_material)
        brow['brow_side']=sign
        bind_rigid(brow,'head'); added += groom(brow,5600,.052,400+sign)
        inverse=brow.matrix_world.inverted()
        for name,prop,tilt in [('Raise brow','brow_raise_'+side,False),('Inner brow tilt','brow_tilt_'+side,True)]:
            values=[]
            for point in points:
                q=point.copy(); t=float(np.clip((abs(q.x)-.140)/.225,0,1))
                q.z+=(.055*(1-2*t)) if tilt else .065*(1-.5*t)
                q.y+=surface_y(q.x,q.z)-surface_y(point.x,point.z)
                values.append(inverse@q)
            morph(brow,name,values,rig,prop,minimum=-1)

    # Neutral body poses are preserved; the later frames are expression studies.
    for frame in (1,40,80):
        scene.frame_set(frame)
        for name in CONTROLS:
            rig['face_'+name]=0.; rig.keyframe_insert(data_path=f'["face_{name}"]',frame=frame)
    for name in PRESETS:
        key_expression(scene, rig, name, neutral_pose)
    scene['expression_presets']=json.dumps({name:preset['frame'] for name,preset in PRESETS.items()})
    scene.frame_end=max(preset['frame'] for preset in PRESETS.values()); scene.frame_set(1); bpy.context.view_layer.update()
    rig['face_controls']='Keyframeable face_ properties: jaw, asymmetric smile, lips, cheeks, muzzle, independent lids and brows; tongue extension, curl, sideways bend, twist and width.'
    text=bpy.data.texts.new('MOOSE | Facial controls')
    text.write('Select Buddy | pose rig, Object Properties > Custom Properties.\n'
               'Use face_ sliders for jaw, asymmetric smile, lips, cheeks, muzzle, blink, eyelid and eyebrow control.\n'
               'Tongue controls: out, curl (up/down), side, twist and widen. Open the jaw before extending the tongue.\n'
               'L and R refer to the character sides. All controls are keyframeable.\n\n'
               'Expression frames: '+scene['expression_presets']+'\n'
               'Teeth stay attached to their jaw; the lips reveal or conceal them.\n'
               'The neutral frame has a closed mouth. This is a facial rig study, not a speech or walk animation.\n')
    return added


def flexible_tongue(p,rig,collection,material,bind_rigid,jaw):
    """Continuous tapered tongue with additive deformation along its length."""
    points=[]; faces=[]; centers=[]; rings=65; around=32
    surface=BVHTree.FromPolygons(current_world(jaw),[tuple(f.vertices) for f in jaw.data.polygons])
    for i in range(rings):
        t=i/(rings-1); width=.002+.090*math.sin(math.pi*t)**.35
        thickness=.002+.018*math.sin(math.pi*t)**.4
        center=surface.ray_cast(p(0,-.23-.48*t,2.50),Vector((0,0,-1)),1)[0]
        if center is None: raise RuntimeError('Tongue root leaves the mouth floor')
        center.z+=.004; centers.append(center)
        for j in range(around):
            angle=2*math.pi*j/around
            points.append(center+Vector((width*math.cos(angle),0,thickness*math.sin(angle))))
    for i in range(rings-1):
        for j in range(around):
            a=i*around+j; b=i*around+(j+1)%around; faces.append((a,b,b+around,a+around))
    faces.extend([tuple(reversed(range(around))),tuple((rings-1)*around+i for i in range(around))])
    tongue=mesh_object('Face | tongue',points,faces,collection,material); bind_rigid(tongue,'jaw')
    inverse=tongue.matrix_world.inverted()
    for name,control in [('Extend','out'),('Curl tip','curl'),('Bend sideways','side'),('Twist','twist'),('Width','widen')]:
        values=[]
        for i,point in enumerate(points):
            q=point.copy(); t=(i//around)/(rings-1)
            if control=='out':
                q.y-=.65*t**1.35; q.z+=.055*t**1.6; q.x*=1-.17*t
            elif control=='curl':
                curl=max(0,(t-.35)/.65)**2
                q.y+=.12*curl; q.z+=.28*curl
            elif control=='side': q.x+=.16*t*t
            elif control=='twist':
                center=centers[i//around]
                angle=.85*t*t; x=q.x; z=q.z-center.z
                q.x=x*math.cos(angle)+z*math.sin(angle)
                q.z=center.z-x*math.sin(angle)+z*math.cos(angle)
            elif control=='widen': q.x*=1+.35*t
            values.append(inverse@q)
        morph(tongue,name,values,rig,'tongue_'+control,minimum=0 if control=='out' else -1)
    tongue['construction']='Continuous tapered tongue: extension, tip curl, sideways bend, twist and width. Rigid root follows the mandible.'
    shader=material.node_tree.nodes['Principled BSDF']
    shader.inputs['Roughness'].default_value=.62
    noise=material.node_tree.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=180
    bump=material.node_tree.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.14; bump.inputs['Distance'].default_value=.0004
    material.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']); material.node_tree.links.new(bump.outputs['Normal'],shader.inputs['Normal'])
    return tongue


def bind_weighted(obj, rig, jaw_weights):
    groups={name:obj.vertex_groups.new(name=name) for name in ('head','jaw')}
    for vertex,weight in zip(obj.data.vertices,jaw_weights):
        groups['jaw'].add([vertex.index],float(weight),'REPLACE')
        groups['head'].add([vertex.index],float(1-weight),'REPLACE')
    arm=obj.modifiers.new('Jaw and skull attachment','ARMATURE'); arm.object=rig; arm.use_deform_preserve_volume=True


def rgba(hex_value):
    rgb=[int(hex_value[i:i+2],16)/255 for i in (1,3,5)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb)+(1,)


def simple_material(name,hex_value,roughness):
    m=bpy.data.materials.new(name); m.use_nodes=True
    p=m.node_tree.nodes['Principled BSDF']; p.inputs['Base Color'].default_value=rgba(hex_value)
    p.inputs['Roughness'].default_value=roughness; m.diffuse_color=rgba(hex_value)
    return m


def palette(mat,scene,navy,brown):
    socket=mat.node_tree.nodes['Principled BSDF'].inputs['Base Color']
    for i,(a,b) in enumerate(zip(rgba(navy)[:3],rgba(brown)[:3])):
        driver=socket.driver_add('default_value',i).driver; driver.expression=f'{a}+v*{b-a}'
        variable=driver.variables.new(); variable.name='v'; variable.type='SINGLE_PROP'
        variable.targets[0].id_type='SCENE'; variable.targets[0].id=scene; variable.targets[0].data_path='["coat_brown"]'
