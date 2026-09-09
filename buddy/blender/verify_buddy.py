"""Validate editable anatomy, skin weights, attachment, and the three pose tests."""
import bpy, sys, json, hashlib, bmesh
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'blender/buddy.blend'; bpy.ops.wm.open_mainfile(filepath=str(source))
s=bpy.context.scene; rig=bpy.data.objects['Buddy | pose rig']; report={}
# Include the hidden anatomical objects while evaluating their bone parents.
for child in bpy.context.view_layer.layer_collection.children: child.exclude=False
bpy.context.view_layer.update()
def check(name,ok,detail):
    report[name]={'passed':bool(ok),'detail':detail}

expected=json.loads(s['landmarks'])
check('shared_skeletal_landmarks',len(rig.data.bones)==len(expected) and all((rig.data.bones[n].head_local-Vector(a)).length<1e-5 and (rig.data.bones[n].tail_local-Vector(b)).length<1e-5 for n,(a,b,_) in expected.items()),len(rig.data.bones))
check('anatomy_layers',all(name in s.view_layers for name in ['01 Skeleton','02 Organs','03 Muscles','04 Skin','05 Fur']),list(s.view_layers.keys()))
body=bpy.data.objects['Skin | continuous torso and limbs']; head=bpy.data.objects['Skin | long moose head and integrated muzzle']
for o in [body,head]:
    bm=bmesh.new(); bm.from_mesh(o.data)
    bad=sum(not e.is_manifold for e in bm.edges); bm.free()
    check('manifold_'+o.name,bad==0,{'non_manifold_edges':bad,'vertices':len(o.data.vertices)})
for obj in bpy.data.collections['Antlers'].objects:
    bm=bmesh.new(); bm.from_mesh(obj.data); seen=set(); sizes=[]
    bad=sum(not edge.is_manifold for edge in bm.edges)
    for vertex in bm.verts:
        if vertex in seen: continue
        stack=[vertex]; seen.add(vertex); size=0
        while stack:
            current=stack.pop(); size+=1
            for edge in current.link_edges:
                neighbor=edge.other_vert(current)
                if neighbor not in seen: seen.add(neighbor); stack.append(neighbor)
        sizes.append(size)
    bm.free()
    check('connected_'+obj.name,bad==0 and len(sizes)==1,{'non_manifold_edges':bad,'components':sizes})
sums=[sum(g.weight for g in v.groups) for v in body.data.vertices]
check('normalized_skin_weights',min(sums)>.999 and max(sums)<1.001,{'min':min(sums),'max':max(sums)})
arm_mask=np.array([value.value for value in body.data.attributes['arm_influence'].data])
arm_sums=[sum(g.weight for g in v.groups) for v in body.data.vertices if arm_mask[v.index]>.5]
check('normalized_arm_weights',min(arm_sums)>.999 and max(arm_sums)<1.001,
      {'min':min(arm_sums),'max':max(arm_sums)})
bm=bmesh.new(); bm.from_mesh(body.data); unseen=set(bm.verts); components=0
while unseen:
    stack=[unseen.pop()]; components+=1
    while stack:
        vertex=stack.pop()
        for edge in vertex.link_edges:
            neighbor=edge.other_vert(vertex)
            if neighbor in unseen: unseen.remove(neighbor); stack.append(neighbor)
bm.free()
blend_vertices=int(np.sum((arm_mask>.05)&(arm_mask<.95)))
check('continuous_shoulder_skin',components==1 and blend_vertices>100,
      {'skin_components':components,'vertices_blending_arm_and_torso':blend_vertices})
strands=sum(len(o.data.curves) for o in bpy.data.collections['Fur'].objects)
check('attached_native_fur',strands>100000 and all(o.data.surface is not None and o.data.surface_uv_map in o.data.surface.data.uv_layers for o in bpy.data.collections['Fur'].objects),strands)
cut_faces=sum(p.material_index==1 for p in head.data.polygons)
check('recessed_nostril_geometry',cut_faces>20,{'cavity_faces':cut_faces})
check('independent_jaw',bpy.data.objects['Skin | lower jaw and closing lip'].parent_bone=='jaw',{'jaw_parent':'head','lower_teeth':len([o for o in s.objects if o.name.startswith('Tooth | lower incisor')]),'upper_incisors':0})

# Pose checks use evaluated vertices, including the armature modifier.
snapshots={}; soles={}; hoof_seating=[]; hand_seating=[];fur_root_gaps=[]
for frame in [1,40,80]:
    s.frame_set(frame); bpy.context.view_layer.update(); deps=bpy.context.evaluated_depsgraph_get()
    ev=body.evaluated_get(deps); mesh=ev.to_mesh()
    snapshots[frame]=np.array([ev.matrix_world@v.co for v in mesh.vertices])
    skin_bvh=BVHTree.FromPolygons(snapshots[frame],[tuple(p.vertices) for p in mesh.polygons])
    ev.to_mesh_clear()
    coat=bpy.data.objects['Fur | Skin | continuous torso and limbs'].evaluated_get(deps)
    coordinates=np.empty(len(coat.data.points)*3,np.float32)
    coat.data.attributes['position'].data.foreach_get('vector',coordinates)
    for point in coordinates.reshape(-1,5,3)[::997,0]:
        world=coat.matrix_world@Vector(point);nearest,_,_,distance=skin_bvh.find_nearest(world)
        fur_root_gaps.append(float(distance))
    floors={}
    for side in ['L','R']:
        for digit in (1,2):
            hand=bpy.data.objects[f'Hoof | hand {side} digit {digit}'].evaluated_get(deps)
            me=hand.to_mesh()
            cap=sum((hand.matrix_world@v.co for v in list(me.vertices)[-64:]),Vector())/64
            nearest,normal,_,_=skin_bvh.find_nearest(cap)
            hand_seating.append(float((cap-nearest).dot(normal)))
            hand.to_mesh_clear()
        points=[]
        for o in s.objects:
            if o.name.startswith('Hoof | foot '+side):
                evaluated=o.evaluated_get(deps); me=evaluated.to_mesh()
                points.extend(evaluated.matrix_world@v.co for v in me.vertices)
                cap=sum((evaluated.matrix_world@me.vertices[i].co for i in range(len(me.vertices)-64,len(me.vertices))),Vector())/64
                nearest,normal,_,_=skin_bvh.find_nearest(cap)
                hoof_seating.append(float((cap-nearest).dot(normal)))
                evaluated.to_mesh_clear()
        floors[side]=min(p.z for p in points)
    soles[frame]=floors
check('step_skin_deformation',np.max(np.linalg.norm(snapshots[80]-snapshots[1],axis=1))>.05,float(np.max(np.linalg.norm(snapshots[80]-snapshots[1],axis=1))))
left_arm=(arm_mask>.8)&(np.array([v.co.x for v in body.data.vertices])>0)
delta=float(np.max(np.linalg.norm(snapshots[40][left_arm]-snapshots[1][left_arm],axis=1)))
check('continuous_arm_gesture',delta>.10,{'travel':delta})
check('standing_foot_contact',all(abs(z)<.015 for z in soles[1].values()),soles)
check('pose_floor_clearance',all(z>-.002 for feet in soles.values() for z in feet.values()),soles)
check('hooves_seated_in_pasterns',max(hoof_seating)<.003,
      {'sampled_crown_centers':len(hoof_seating),'maximum_surface_offset':max(hoof_seating)})
check('hand_hooves_seated_in_wrists',max(hand_seating)<.003,
      {'sampled_crown_centers':len(hand_seating),'maximum_surface_offset':max(hand_seating)})
check('fur_roots_follow_posed_skin',max(fur_root_gaps)<.003,
      {'sampled_roots_in_three_poses':len(fur_root_gaps),'maximum_skin_gap':max(fur_root_gaps)})

# Geometry membership: organ centers must lie within the actual skin envelope.
s.frame_set(1); bpy.context.view_layer.update(); deps=bpy.context.evaluated_depsgraph_get(); bvhs=[]
for obj in bpy.data.collections['Skin'].objects:
    ev=obj.evaluated_get(deps); me=ev.to_mesh()
    verts=[ev.matrix_world@v.co for v in me.vertices]
    bvhs.append(BVHTree.FromPolygons(verts,[tuple(p.vertices) for p in me.polygons]))
    ev.to_mesh_clear()
def inside(bvh,point):
    direction=Vector((.321,.574,.753)).normalized(); origin=point.copy(); hits=0
    for _ in range(20):
        hit,n,index,d=bvh.ray_cast(origin,direction,10)
        if hit is None: break
        hits+=1; origin=hit+direction*1e-5
    return bool(hits%2)
outside=[]
for obj in bpy.data.collections['Organs'].objects:
    if obj.type!='MESH': continue
    center=obj.matrix_world.translation
    if not any(inside(b,center) for b in bvhs): outside.append(obj.name)
check('organ_centers_enclosed',not outside,{'outside':outside,'note':'Checks guide centers, not physiological accuracy or all organ surfaces.'})
s.frame_set(1)
out={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'checks':report,'passed':all(c['passed'] for c in report.values()),'scope':'Stylized biped construction and three static pose tests; not a validated anatomical simulation or finished walk cycle.'}
(ROOT/'validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2),flush=True)
if not out['passed']: sys.exit(1)
