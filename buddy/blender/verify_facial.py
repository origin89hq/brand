"""Check evaluated facial deformation, tooth occlusion and actual lid coverage."""
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
from dental import arch as dental_arch
source=ROOT/'blender/buddy.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
scene=bpy.context.scene
rig=bpy.data.objects['Buddy | pose rig']
for child in bpy.context.view_layer.layer_collection.children: child.exclude=False
presets=json.loads(scene['expression_presets'])
checks={}
def check(name,passed,detail): checks[name]={'passed':bool(passed),'detail':detail}
def frame(number):
    scene.frame_set(number); rig.update_tag(); bpy.context.view_layer.update()
def mesh_data(obj):
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh=ev.to_mesh()
    points=[ev.matrix_world@v.co for v in mesh.vertices]
    polygons=[tuple(p.vertices) for p in mesh.polygons]
    ev.to_mesh_clear()
    return points,polygons
def bvh(obj): return BVHTree.FromPolygons(*mesh_data(obj))
def coverage(side):
    eye=bpy.data.objects['Eye | globe '+side]
    center=eye.matrix_world.translation; rotation=eye.matrix_world.to_quaternion()
    globe=bvh(eye)
    lids=[bvh(bpy.data.objects[f'Face | {kind} eyelid {side}']) for kind in ('upper','lower')]
    total=covered=0
    for u in np.linspace(-.80,.80,13):
        for v in np.linspace(-.80,.80,13):
            if u*u+v*v>.70: continue
            point=center+rotation@Vector((.111*u,-.070*np.sqrt(1-u*u-v*v),.124*v))
            direction=rotation@Vector((0,1,0)); origin=point-direction*.15
            distance=globe.ray_cast(origin,direction,.5)[3]
            if distance is None: raise AssertionError('Coverage ray missed cornea')
            lid_distances=[tree.ray_cast(origin,direction,.5)[3] for tree in lids]
            covered+=any(d is not None and d<distance for d in lid_distances)
            total+=1
    return covered/total

rows={}; lid_clearance=[]; jaw_motion={}; lower_teeth=[]
head=bpy.data.objects['Skin | long moose head and integrated muzzle']
for name,number in presets.items():
    frame(number)
    rows[name]={k:float(rig[k]) for k in rig.keys() if k.startswith('face_') and isinstance(rig[k],(float,int))}
    jaw_motion[name]=float(rig.pose.bones['jaw'].rotation_euler.x)
    for side in ('L','R'):
        globe=bvh(bpy.data.objects['Eye | globe '+side])
        for kind in ('upper','lower'):
            points,polygons=mesh_data(bpy.data.objects[f'Face | {kind} eyelid {side}'])
            for face in polygons[::max(1,len(polygons)//160)]:
                point=sum((points[i] for i in face),Vector())/len(face)
                nearest,normal,_,distance=globe.find_nearest(point)
                lid_clearance.append(float((point-nearest).dot(normal)))
    # A crown must remain rigid relative to its owning jaw across every preset.
    tooth=bpy.data.objects['Tooth | lower incisor 4']
    points,_=mesh_data(tooth)
    jaw_matrix=rig.matrix_world@rig.pose.bones['jaw'].matrix
    lower_teeth.append(np.array([jaw_matrix.inverted()@point for point in points]))

check('ten_distinct_expressions',len(rows)==10 and len({tuple(r.values()) for r in rows.values()})==10,rows)
check('jaw_driver_moves_mandible',jaw_motion['neutral']==0 and jaw_motion['delighted']>.30,jaw_motion)
check('rigid_teeth_follow_jaw',max(float(np.max(np.abs(p-lower_teeth[0]))) for p in lower_teeth)<1e-5,
      {'max_local_drift':max(float(np.max(np.abs(p-lower_teeth[0]))) for p in lower_teeth)})
frame(1); roots=[]; arch_errors=[]
for i in range(8):
    tooth=bpy.data.objects[f'Tooth | lower incisor {i+1}']; points,_=mesh_data(tooth)
    root=sum(points[:32],Vector())/32; expected=Vector(dental_arch(tooth['dental_arch_angle']))
    expected.z-=scene['head_height_offset']
    roots.append(root); arch_errors.append((root-expected).length)
guide=bpy.data.objects.get('Bone | incisor alveolar arch')
check('teeth_follow_mandibular_arch',max(arch_errors)<1e-5 and max(p.y for p in roots)-min(p.y for p in roots)>.05
      and guide is not None and guide.parent_bone=='jaw',
      {'maximum_root_error':max(arch_errors),'arch_depth':max(p.y for p in roots)-min(p.y for p in roots),'teeth':8})
check('eyelid_faces_clear_cornea',min(lid_clearance)>.0001,
      {'sampled_faces':len(lid_clearance),'minimum_clearance':min(lid_clearance)})
driver_blocks=[rig,*[o.data.shape_keys for o in scene.objects if o.type=='MESH' and o.data.shape_keys]]
drivers=[d for block in driver_blocks if block.animation_data for d in block.animation_data.drivers]
check('valid_facial_drivers',len(drivers)>=13 and all(d.driver.is_valid for d in drivers),len(drivers))

cover={}
for name in ('neutral','wink','blink'):
    frame(presets[name]); cover[name]={side:coverage(side) for side in ('L','R')}
check('closed_lids_cover_eyes',all(v>.995 for v in cover['blink'].values()),cover)
check('independent_wink',cover['wink']['L']>.995 and cover['wink']['R']<.12,cover['wink'])
check('open_eyes_unobscured',all(v<.12 for v in cover['neutral'].values()),cover['neutral'])

# Visibility is tested against evaluated skin, gum and tongue geometry from
# three review angles. This catches crowns poking through a closed cheek.
occluder_names=[head.name,'Skin | lower jaw and closing lip','Face | oral chamber',
                'Face | mouth corner tissue L','Face | mouth corner tissue R',
                'Face | inner cheek L','Face | inner cheek R','Face | mouth floor',
                'Face | tongue','Face | lower gum','Face | upper dental pad']
visible={}
for name in ('neutral','smile','delighted'):
    frame(presets[name]); occluders=[bvh(bpy.data.objects[n]) for n in occluder_names]
    visible[name]={}
    for angle,offset in [('front',(0,-1,0)),('three_quarter',(4,-8,.55)),('side',(1,0,0))]:
        direction=Vector(offset).normalized(); counts={}
        for tooth in [o for o in scene.objects if o.name.startswith('Tooth |')]:
            points,_=mesh_data(tooth); count=0
            for point in points[::4]:
                hit_distances=[tree.ray_cast(point+direction*2,-direction,2.001)[3] for tree in occluders]
                count+=not any(d is not None and d<1.9999 for d in hit_distances)
            if count: counts[tooth.name]=count
        visible[name][angle]=counts
check('teeth_concealed_when_closed',not any(visible['neutral'].values()),visible['neutral'])
revealed={name:sum(count for tooth,count in visible[name]['three_quarter'].items() if 'incisor' in tooth)
          for name in ('smile','delighted')}
check('teeth_revealed_in_smile',all(count>25 for count in revealed.values()),revealed)

# A single brow and lip change must deform their mesh without moving the
# opposite brow or the skull. Evaluate actual mesh coordinates, not key values.
frame(1)
names=['Face | eyebrow L','Face | eyebrow R',head.name,'Skin | lower jaw and closing lip']
before={name:np.array(mesh_data(bpy.data.objects[name])[0]) for name in names}
rig['face_brow_raise_L']=1.; rig['face_lip_raise']=1.; rig.update_tag(); bpy.context.view_layer.update()
travel={name:float(np.max(np.linalg.norm(np.array(mesh_data(bpy.data.objects[name])[0])-before[name],axis=1))) for name in names}
check('independent_brow_and_lip_deformation',travel[names[0]]>.04 and travel[names[1]]<1e-6 and travel[head.name]>.025,travel)
frame(1)
jaw=bpy.data.objects['Skin | lower jaw and closing lip']
rest_lip=np.array(mesh_data(jaw)[0])
rig['face_lip_lower']=1.; rig.update_tag(); bpy.context.view_layer.update()
rolled_lip=np.array(mesh_data(jaw)[0]); thickness=[]
sections=np.unique(rest_lip[:,1]); sections=sections[(sections>-.84)&(sections<-.56)]
for y in sections[::max(1,len(sections)//12)]:
    selected=np.abs(rest_lip[:,1]-y)<.00001
    if selected.sum()<4: continue
    before=np.ptp(rest_lip[selected,2]); after=np.ptp(rolled_lip[selected,2])
    if before>.005: thickness.append(float(after/before))
check('lower_lip_keeps_thickness',len(thickness)>4 and min(thickness)>.92,
      {'sampled_sections':len(thickness),'minimum_thickness_ratio':min(thickness)})
frame(1)
hair_roots={}; root_distances=[]
for number in (1,170,260):
    frame(number)
    for name in ('Face | eyebrow L','Face | upper eyelid L','Face | lower eyelid L'):
        obj=bpy.data.objects['Fur | '+name]
        ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        position=ev.data.attributes['position'].data
        roots=[ev.matrix_world@position[i].vector for i in range(0,len(position),5*37)]
        surface=bvh(bpy.data.objects[name])
        root_distances.extend(float(surface.find_nearest(point)[3]) for point in roots)
        hair_roots[(number,name)]=np.array(roots)
brow_hair_travel=float(np.max(np.linalg.norm(hair_roots[(170,'Face | eyebrow L')]-hair_roots[(1,'Face | eyebrow L')],axis=1)))
check('facial_hair_follows_surface',max(root_distances)<.002 and brow_hair_travel>.04,
      {'sampled_roots':len(root_distances),'max_surface_distance':max(root_distances),'brow_hair_travel':brow_hair_travel})
lash_roots={}; lash_distances=[]
for number in (1,230,260):
    frame(number)
    for side in ('L','R'):
        obj=bpy.data.objects['Fur | upper eyelashes '+side]
        ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        position=ev.data.attributes['position'].data
        roots=[ev.matrix_world@position[i].vector for i in range(0,len(position),obj['point_stride'])]
        surface=bvh(bpy.data.objects['Face | upper eyelid '+side])
        lash_distances.extend(float(surface.find_nearest(point)[3]) for point in roots)
        lash_roots[(number,side)]=np.array(roots)
lash_travel={side:float(np.max(np.linalg.norm(lash_roots[(230,side)]-lash_roots[(1,side)],axis=1))) for side in ('L','R')}
check('eyelashes_follow_independent_lids',max(lash_distances)<.002 and lash_travel['L']>.04 and lash_travel['R']<1e-5,
      {'sampled_roots':len(lash_distances),'maximum_surface_distance':max(lash_distances),'wink_travel':lash_travel})
frame(1)
tongue=bpy.data.objects['Face | tongue']; baseline=np.array(mesh_data(tongue)[0]); tongue_travel={}
for control in ('out','curl','side','twist','widen'):
    frame(1); rig['face_tongue_'+control]=1.; rig.update_tag(); bpy.context.view_layer.update()
    tongue_travel[control]=float(np.max(np.linalg.norm(np.array(mesh_data(tongue)[0])-baseline,axis=1)))
check('independent_flexible_tongue',tongue_travel['out']>.60 and tongue_travel['curl']>.28 and min(tongue_travel.values())>.02,tongue_travel)
frame(1)
beard=bpy.data.objects['Fur | Skin | throat bell']; violations=[]; sampled=0
for number in (140,290):
    frame(number)
    rest=(rig.matrix_world@rig.pose.bones['jaw'].matrix@rig.data.bones['jaw'].matrix_local.inverted()).inverted()
    points,polygons=mesh_data(bpy.data.objects['Face | mouth floor'])
    floor=BVHTree.FromPolygons([rest@point for point in points],polygons)
    ev=beard.evaluated_get(bpy.context.evaluated_depsgraph_get())
    positions=ev.data.attributes['position'].data
    for index in range(0,len(positions),13):
        item=positions[index]
        point=rest@ev.matrix_world@item.vector
        if abs(point.x)>.145 or not -.70<point.y<-.17: continue
        hit=floor.ray_cast(Vector((point.x,point.y,2.5)),Vector((0,0,-1)),2)[0]
        if hit is None: continue
        sampled+=1
        if point.z>hit.z+.001: violations.append({'frame':number,'height_above_floor':point.z-hit.z})
check('beard_stays_below_mouth',sampled>50 and not violations,{'sampled_hair_points':sampled,'intrusions':violations[:10]})
tongue_clearance={}
for name in ('playful','tongue-peek'):
    frame(presets[name]); points,_=mesh_data(tongue); upper=bvh(head); distances=[]
    for point in points[int(len(points)*.65)::7]:
        nearest,normal,_,distance=upper.find_nearest(point)
        distances.append(float((point-nearest).dot(normal)))
    tongue_clearance[name]=min(distances)
check('extended_tongue_clears_muzzle',min(tongue_clearance.values())>0,tongue_clearance)
frame(1)
from studio import expression as studio_expression
frame(40)
arm_names=('upper_arm.L','forearm.L','hand.L')
raised={name:np.array(rig.pose.bones[name].matrix_basis) for name in arm_names}
frame(presets['smile'])
smile={name:float(rig[name]) for name in rig.keys() if name.startswith('face_') and isinstance(rig[name],(int,float))}
studio_expression(scene,'explaining')
frame(presets['smile'])  # Rendering re-evaluates the current animation frame.
pose_error=max(float(np.max(np.abs(np.array(rig.pose.bones[name].matrix_basis)-raised[name]))) for name in arm_names)
face_error=max(abs(float(rig[name])-value) for name,value in smile.items())
check('combined_pose_survives_frame_evaluation',pose_error<1e-5 and face_error<1e-5,
      {'raised_arm_matrix_error':pose_error,'smile_control_error':face_error})
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'passed':all(c['passed'] for c in checks.values()),
        'expression_frames':presets,'checks':checks,
        'scope':'Sampled expression deformation and visibility; not a speech rig or validated facial muscle simulation.'}
(ROOT/'facial-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
if not report['passed']: sys.exit(1)
