"""Shared camera, palette and pose setup for Buddy exports and situations."""
import bpy,json
from mathutils import Vector
LAYERS={'skeleton':'01 Skeleton','organs':'02 Organs','muscles':'03 Muscles','skin':'04 Skin','fur':'05 Fur'}
ALIASES={'welcoming':'smile','explaining':'smile','thinking':'skeptical','playful':'tongue-peek'}
def configure(scene,transparent=False,palette='brown',layer='fur'):
    selected=scene.view_layers[LAYERS[layer]];bpy.context.window.view_layer=selected
    for item in scene.view_layers:item.use=item==selected
    scene['coat_brown']=float(palette=='brown');scene.update_tag()
    scene.render.film_transparent=transparent
    bpy.data.objects['Studio | seamless floor'].hide_render=transparent
    bpy.context.view_layer.update();return selected
def expression(scene,name,pose=None):
    presets=json.loads(scene['expression_presets']);native=ALIASES.get(name,name)
    if native not in presets:raise ValueError('Unknown expression: '+name)
    rig=bpy.data.objects['Buddy | pose rig'];transforms={}
    pose=pose or ('explaining' if name=='explaining' else None)
    if pose:
        scene.frame_set({'standing':1,'explaining':40,'step':80}[pose]);bpy.context.view_layer.update()
        for bone in rig.pose.bones:
            if bone.name not in ('head','jaw','ear.L','ear.R'):transforms[bone.name]=bone.matrix_basis.copy()
    scene.frame_set(presets[native]);bpy.context.view_layer.update()
    # Hold the evaluated facial controls while applying a different body pose.
    # Otherwise Cycles re-evaluates the action and restores the standing arms.
    if transforms and rig.animation_data:rig.animation_data.action=None
    for name,matrix in transforms.items():rig.pose.bones[name].matrix_basis=matrix
    bpy.context.view_layer.update();return native,pose
def avatar(scene,name,isolated=True):
    """A complete head silhouette, with a calm greeting for small app surfaces."""
    rig=bpy.data.objects['Buddy | pose rig'];overrides={}
    if name=='welcoming':
        if rig.animation_data:rig.animation_data.action=None
        overrides={'jaw_open':.045,'smile':.5,'lip_raise':0.,'lip_lower':0.,
                   'brow_raise_L':.18,'brow_raise_R':.10,'lower_lid_L':.12,'lower_lid_R':.18}
        for control,value in overrides.items():rig['face_'+control]=value
        rig.update_tag()
    if not isolated:bpy.context.view_layer.update();return overrides
    hidden={bpy.data.objects[name] for name in ('Skin | continuous torso and limbs','Skin | short moose tail')}
    hidden.update(o for o in scene.objects if o.name.startswith('Hoof |'))
    for obj in scene.objects:
        parent=obj
        while parent:
            if parent in hidden:obj.hide_render=True;break
            parent=parent.parent
    bpy.context.view_layer.update();return overrides
def camera(scene,view,size,padding=1.):
    playful=scene.frame_current==json.loads(scene['expression_presets']).get('tongue-peek')
    drop=scene['leg_height_drop'];target=Vector((0,-.08,1.84-drop*.5));scale=4.50
    offsets={'front':(0,-9,0),'side':(9,0,0),'hero':(4.3,-8,1.1),'face':(4,-8,.55),'face-front':(0,-9,0),'face-side':(9,0,0),'face-muzzle':(4,-8,.55),'hooves':(3,-8,1.6),'hands':(3,-8,1.1),'antlers':(3.4,-8,1.6),'portrait':(2.8,-8,.4),'avatar':(1.1,-8,.15),'feet-side':(8,-.4,1.2)}
    if view.startswith('face'):target=Vector((0,-.32,2.08-drop));scale=2.
    if view=='face-muzzle':target=Vector((0,-.73,2.035-drop));scale=1.02
    if view=='hooves':target=Vector((0,-.055,.40));scale=1.25
    if view=='feet-side':target=Vector((.33,-.09,.27));scale=.80
    if view=='hands':
        rig=bpy.data.objects['Buddy | pose rig'];hand=rig.pose.bones['hand.L'];elbow=rig.pose.bones['forearm.L'];shoulder=rig.pose.bones['upper_arm.L']
        target=rig.matrix_world@((hand.tail+elbow.head+shoulder.head)/3);scale=.95
    if view=='antlers':target=Vector((0,.24,3.12-drop));scale=3.6
    if view=='portrait':target=Vector((0,-.12,2.22));scale=3.5
    if view=='avatar-compact':target=Vector((0,-.35,1.95));scale=1.95;offsets[view]=(.7,-8,-.15) if playful else (3.8,-8,.45)
    if view=='avatar':
        offset=Vector((.7,-8,-.15) if playful else (3.8,-8,.8));basis=(-offset).to_track_quat('-Z','Y').to_matrix()
        names=('Skin | long moose head and integrated muzzle','Skin | lower jaw and closing lip',
               'Skin | throat bell','Skin | cupped leaf ear L','Skin | cupped leaf ear R',
               'Antler | cupped palmate L','Antler | cupped palmate R')
        points=[];graph=bpy.context.evaluated_depsgraph_get()
        for name in names:
            obj=bpy.data.objects[name].evaluated_get(graph)
            points.extend(basis.transposed()@(obj.matrix_world@Vector(corner)) for corner in obj.bound_box)
        low=Vector(tuple(min(p[i] for p in points) for i in range(3)))
        high=Vector(tuple(max(p[i] for p in points) for i in range(3)))
        target=basis@((low+high)*.5);scale=max(high.x-low.x,high.y-low.y)*1.10
        offsets['avatar']=offset
    cam=scene.camera;cam.location=target+Vector(offsets[view]);cam.data.ortho_scale=scale*padding
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.resolution_x=size;scene.render.resolution_y=round(size*1.12)
    if view.startswith('face') or view in ('hooves','hands','avatar','avatar-compact','portrait','feet-side'):scene.render.resolution_y=size
    if view=='antlers':scene.render.resolution_y=round(size*.60)
    return target
def device(scene):
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
        gpu=any(d.type=='METAL' for d in prefs.devices)
        for dev in prefs.devices:dev.use=dev.type=='METAL'
        scene.cycles.device='GPU' if gpu else 'CPU'
    except Exception:scene.cycles.device='CPU'
