"""Buddy has spotted something: a native, editable binoculars situation.

Builds a derivative of the shared character, retaining the approved presentation
materials and lights. The character and face source files are read-only inputs.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'buddy/blender'))
from studio import configure, expression, avatar, device
from finish import render_quality


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def linear(value):
    rgb = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--size', type=int, default=1600)
    parser.add_argument('--samples', type=int, default=192)
    parser.add_argument('--draft', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    master = ROOT / 'buddy/blender/buddy.blend'
    presentation = ROOT / 'buddy/presentation/face-front.blend'
    source_sha, presentation_sha = sha(master), sha(presentation)
    lineage = json.loads((presentation.parent / 'face-front-source.json').read_text())
    assert lineage['base_sha256'] == source_sha, 'Presentation scene must derive from the current Buddy.'

    # Evaluate the canonical standing body, then transfer it to the approved set.
    bpy.ops.wm.open_mainfile(filepath=str(master))
    scene = bpy.context.scene
    configure(scene, True)
    expression(scene, 'welcoming', pose='standing')
    avatar(scene, 'welcoming', isolated=False)
    rig = bpy.data.objects['Buddy | pose rig']
    if rig.animation_data:
        rig.animation_data.action = None
    bpy.context.view_layer.update()
    body_pose = {bone.name: bone.matrix_basis.copy() for bone in rig.pose.bones}

    bpy.ops.wm.open_mainfile(filepath=str(presentation))
    scene = bpy.context.scene
    scene.name = 'Buddy | Equipment scout'
    layer = configure(scene, True)
    rig = bpy.data.objects['Buddy | pose rig']
    if rig.animation_data:
        rig.animation_data.action = None
    for name, matrix in body_pose.items():
        rig.pose.bones[name].matrix_basis = matrix
    for name, value in {
        'jaw_open': .025, 'smile': .48, 'tongue_out': 0,
        'brow_raise_L': .13, 'brow_raise_R': .22,
        'upper_lid_L': .02, 'upper_lid_R': .02,
        'lower_lid_L': .09, 'lower_lid_R': .12,
    }.items():
        rig['face_' + name] = value
    rig.update_tag()
    bpy.context.view_layer.update()

    def point_bone(name, direction):
        bone = rig.pose.bones[name]
        old = bone.matrix.copy()
        current = (old.to_quaternion() @ Vector((0, 1, 0))).normalized()
        rotation = current.rotation_difference(Vector(direction).normalized()).to_matrix().to_4x4()
        matrix = rotation @ old
        matrix.translation = old.translation
        bone.matrix = matrix
        bpy.context.view_layer.update()

    def arm(side, sign):
        upper = rig.pose.bones['upper_arm.' + side]
        lower = rig.pose.bones['forearm.' + side]
        shoulder = upper.head.copy()
        wrist = Vector((sign * .405, -.51, 1.03))
        delta = wrist - shoulder
        distance = delta.length
        axis = delta.normalized()
        assert abs(upper.length - lower.length) < distance < upper.length + lower.length
        along = (upper.length ** 2 - lower.length ** 2 + distance ** 2) / (2 * distance)
        bend = Vector((sign, 0, -.55))
        bend = (bend - axis * bend.dot(axis)).normalized()
        elbow = shoulder + axis * along + bend * math.sqrt(upper.length ** 2 - along ** 2)
        point_bone(upper.name, elbow - shoulder)
        point_bone(lower.name, wrist - elbow)
        point_bone('hand.' + side, (-sign * .70, -.62, .18))

    arm('L', 1)
    arm('R', -1)
    # A small turn back toward the visitor, with the body facing into the copy.
    head = rig.pose.bones['head']
    matrix = head.matrix.copy()
    turned = Matrix.Rotation(math.radians(-11), 4, 'Z') @ matrix
    turned.translation = matrix.translation
    head.matrix = turned
    head.rotation_euler[2] += math.radians(-3)
    rig.pose.bones['ear.R'].rotation_euler[1] = math.radians(-7)
    rig.update_tag()
    bpy.context.view_layer.update()

    props = bpy.data.collections.new('Scout | editable binoculars and strap')
    field = bpy.data.collections.new('Scout | optional field details')
    scene.collection.children.link(props)
    scene.collection.children.link(field)

    def link(obj, collection=props):
        for existing in list(obj.users_collection):
            existing.objects.unlink(obj)
        collection.objects.link(obj)
        return obj

    palette_path = ROOT / 'identity/tokens/brand-tokens.json'
    palette = json.loads(palette_path.read_text())
    colors = palette['themes']

    def material(name, color, roughness=.5, metallic=0):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        shader = mat.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = linear(color)
        shader.inputs['Roughness'].default_value = roughness
        shader.inputs['Metallic'].default_value = metallic
        return mat

    blue = material('Scout | Origin89 blue rubber armor', palette['brand']['blue'], .48)
    rubber = material('Scout | charcoal eyecups and rims', colors['dark']['line-strong'], .62)
    strap_mat = material('Scout | woven blue neck strap', palette['materials_3d']['shell'], .9)
    metal = material('Scout | satin hinge metal', colors['light']['faint'], .3, .65)
    glass = material('Scout | coated optical glass', palette['materials_3d']['shell'], .12, .30)
    glass.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value = 1
    glass.node_tree.nodes['Principled BSDF'].inputs['Coat Roughness'].default_value = .06
    dark_glass = material('Scout | dark lens interior', colors['dark']['surface-raised'], .25)
    grass_mat = material('Scout | field grass', colors['light']['nominal'], .94)
    dry_mat = material('Scout | dry grass tips', palette['materials_3d']['ceramic'], .95)

    for mat, scale, strength in ((blue, 240, .10), (rubber, 190, .12), (strap_mat, 360, .23)):
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = scale
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = strength
        bump.inputs['Distance'].default_value = .0012
        links.new(noise.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], nodes['Principled BSDF'].inputs['Normal'])

    # Local barrel axis: eyepieces at -Z, objectives at +Z. Lowered, pitched down.
    assembly = bpy.data.objects.new('Binoculars | pose control', None)
    props.objects.link(assembly)
    assembly.empty_display_type = 'PLAIN_AXES'
    assembly.empty_display_size = .18
    assembly.location = (0, -.635, 1.015)
    assembly.rotation_euler = Vector((0, -.94, -.34)).to_track_quat('Z', 'Y').to_euler()

    def finish(obj, name, mat, bevel=0):
        link(obj)
        obj.name = name
        obj.parent = assembly
        obj.data.materials.append(mat)
        if bevel:
            mod = obj.modifiers.new('Soft manufactured edges', 'BEVEL')
            mod.width, mod.segments = bevel, 4
            obj.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
        for poly in obj.data.polygons:
            poly.use_smooth = True
        return obj

    def cylinder(name, position, radius, depth, mat, radius2=None, bevel=.007):
        bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=radius, radius2=radius if radius2 is None else radius2, depth=depth, location=position)
        return finish(bpy.context.object, name, mat, bevel)

    def box(name, position, dimensions, mat, bevel=.016):
        bpy.ops.mesh.primitive_cube_add(size=1, location=position)
        obj = bpy.context.object
        obj.dimensions = dimensions
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        return finish(obj, name, mat, bevel)

    def ring(name, position, radius, thickness, mat):
        bpy.ops.mesh.primitive_torus_add(major_segments=64, minor_segments=12, location=position, major_radius=radius, minor_radius=thickness)
        return finish(bpy.context.object, name, mat)

    for side, x in (('L', .179), ('R', -.179)):
        cylinder('Binoculars | tapered blue barrel ' + side, (x, 0, .006), .103, .34, blue, .144, .016)
        cylinder('Binoculars | objective housing ' + side, (x, 0, .166), .147, .062, rubber)
        cylinder('Binoculars | recessed objective ' + side, (x, 0, .193), .125, .009, dark_glass, bevel=.002)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=24, location=(x, 0, .199))
        lens = bpy.context.object
        lens.scale = (.116, .116, .013)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        finish(lens, 'Binoculars | convex coated front glass ' + side, glass)
        ring('Binoculars | objective lip ' + side, (x, 0, .203), .136, .009, rubber)
        cylinder('Binoculars | ocular collar ' + side, (x, 0, -.182), .092, .062, blue)
        cylinder('Binoculars | soft eyecup ' + side, (x, 0, -.23), .097, .055, rubber)
        cylinder('Binoculars | eyepiece glass ' + side, (x, 0, -.26), .064, .004, dark_glass)
        ring('Binoculars | eyecup rim ' + side, (x, 0, -.262), .078, .014, rubber)
        for i in range(3):
            ring('Binoculars | grip seam ' + side + ' ' + str(i), (x, 0, -.092 + i * .034), .117 + i * .004, .0023, blue)
        box('Binoculars | strap lug ' + side, (x + (.122 if x > 0 else -.122), .028, -.098), (.037, .056, .060), metal, .009)
    box('Binoculars | center bridge', (0, .025, -.075), (.29, .10, .12), blue)
    cylinder('Binoculars | central hinge', (0, .025, .005), .044, .23, metal)
    cylinder('Binoculars | focus wheel', (0, .065, -.035), .063, .087, rubber)
    for i in range(28):
        angle = i * 2 * math.pi / 28
        cylinder('Binoculars | focus wheel knurl ' + str(i), (.063 * math.cos(angle), .065 + .063 * math.sin(angle), -.035), .003, .067, rubber, bevel=.001)

    def ribbon(name, points, width, mat, collection=props):
        # Catmull-Rom center line, with an actual flat webbing cross section.
        controls = [Vector(points[0]), *map(Vector, points), Vector(points[-1])]
        centers = []
        for index in range(1, len(controls) - 2):
            p0, p1, p2, p3 = controls[index - 1:index + 3]
            for step in range(12):
                t = step / 12
                centers.append(.5 * ((2 * p1) + (-p0 + p2) * t + (2*p0 - 5*p1 + 4*p2 - p3) * t*t + (-p0 + 3*p1 - 3*p2 + p3) * t*t*t))
        centers.append(Vector(points[-1]))
        vertices, faces = [], []
        for p in centers:
            vertices += [tuple(p + Vector((-width/2, 0, 0))), tuple(p + Vector((width/2, 0, 0)))]
        for i in range(len(centers) - 1):
            j = i * 2
            faces.append((j, j+1, j+3, j+2))
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        mesh.materials.append(mat)
        for p in mesh.polygons:
            p.use_smooth = True
        obj.modifiers.new('Woven strap thickness', 'SOLIDIFY').thickness = .006
        bevel = obj.modifiers.new('Soft strap edges', 'BEVEL')
        bevel.width, bevel.segments = .003, 3
        return obj

    bpy.context.view_layer.update()
    for side, sign in (('L', 1), ('R', -1)):
        lug = assembly.matrix_world @ Vector((sign*.307, .028, -.098))
        ribbon('Strap | shoulder to binocular ' + side, [
            (sign*.13, .28, 1.64), (sign*.29, .12, 1.66),
            (sign*.335, -.13, 1.54), (sign*.34, -.35, 1.36),
            (sign*.33, -.47, 1.19), tuple(lug),
        ], .034, strap_mat)

    # A few native grass blades ground the outdoor idea without making a diorama.
    rng = random.Random(89)
    for tuft, (cx, cy, height) in enumerate(((-.63, .02, .16), (.56, .16, .12))):
        for blade in range(11):
            angle = rng.uniform(0, 2*math.pi)
            length = rng.uniform(height*.45, height)
            lean = rng.uniform(.022, .085)
            x, y = cx+rng.uniform(-.035,.035), cy+rng.uniform(-.025,.025)
            width = rng.uniform(.006,.013)
            vertices = []
            for k in range(7):
                t = k/6
                p = Vector((x+math.cos(angle)*lean*t*t, y+math.sin(angle)*lean*t*t, .007+length*t))
                offset = Vector((-math.sin(angle), math.cos(angle), 0))*width*(1-t)*.5
                vertices.extend((tuple(p-offset), tuple(p+offset)))
            mesh = bpy.data.meshes.new('Grass blade')
            mesh.from_pydata(vertices, [], [(2*i,2*i+1,2*i+3,2*i+2) for i in range(6)])
            mesh.update()
            obj = bpy.data.objects.new('Field | grass %02d.%02d' % (tuft, blade), mesh)
            field.objects.link(obj)
            mesh.materials.append(dry_mat if blade % 5 == 0 else grass_mat)

    bpy.data.objects['Presentation | seamless sweep'].visible_camera = False
    scene.frame_start = scene.frame_end = 1
    scene.frame_set(1)
    for marker in list(scene.timeline_markers):
        scene.timeline_markers.remove(marker)
    scene.timeline_markers.new('Found something | static scout pose', frame=1)
    cam = scene.camera
    cam.name = 'Scout | full body camera'
    cam.data.type, cam.data.lens = 'PERSP', 70
    cam.data.sensor_width = 36
    scene.render.resolution_x = scene.render.resolution_y = args.size
    scene.render.resolution_percentage = 100
    target = Vector((0, -.06, 1.58))
    direction = Vector((-2.15, -9, 1.15)).normalized()
    cam.location = target + direction * 9.6
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    render_quality(scene, args.samples)
    scene.cycles.adaptive_min_samples = min(64, args.samples)
    scene.cycles.adaptive_threshold = .02 if args.draft else .006
    device(scene)
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    bpy.context.view_layer.update()

    # Check that antlers and hooves are in-frame before the expensive fur render.
    graph = bpy.context.evaluated_depsgraph_get()
    visible_bounds = []
    for obj in scene.objects:
        if obj.name.startswith(('Antler |', 'Hoof | foot', 'Binoculars |')) and obj.type == 'MESH':
            evaluated = obj.evaluated_get(graph)
            visible_bounds.extend(world_to_camera_view(scene, cam, evaluated.matrix_world @ Vector(p)) for p in evaluated.bound_box)
    framing_ok = all(.03 < p.x < .97 and .03 < p.y < .97 for p in visible_bounds)
    assert framing_ok, 'Scout camera clips the character or binoculars.'
    assert all(abs(rig.pose.bones[name].matrix.to_scale()[i] - 1) < .001 for name in ('upper_arm.L','upper_arm.R','forearm.L','forearm.R') for i in range(3)), 'Arm poses must not stretch bones.'

    output_dir = ROOT / ('.build/equipment-scout' if args.draft else 'situations/scenes/equipment-scout')
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / 'buddy-equipment-scout.png'
    scene_path = output_dir / 'scene.blend'
    scene.render.filepath = str(output)
    scene['buddy_master'] = str(master.relative_to(ROOT))
    scene['buddy_source_sha256'] = source_sha
    scene['situation'] = 'Equipment scout: binoculars lowered, looking back toward the visitor.'
    scene['rebuild'] = 'blender -b --python situations/source/build_equipment_scout.py -- --size 1600 --samples 192'
    notes = bpy.data.texts.new('READ ME | Equipment scout')
    notes.write('Editable derivative of the canonical Buddy. The binoculars, strap, optional grass and camera are named objects. Shared geometry, rig and fur remain in buddy/blender/buddy.blend. This is a static pose. Rebuilding resets this derivative to the recipe; save hand edits to a separate scene before rebuilding.\n')
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.region_3d.view_perspective = 'CAMERA'
    bpy.ops.object.select_all(action='DESELECT')
    assembly.select_set(True)
    bpy.context.view_layer.objects.active = assembly
    bpy.ops.wm.save_as_mainfile(filepath=str(scene_path), compress=True)
    bpy.ops.render.render(write_still=True, layer=layer.name)
    assert sha(master) == source_sha and sha(presentation) == presentation_sha, 'Authored Buddy inputs changed.'
    metadata = {
        'name': 'Buddy equipment scout', 'base': str(master.relative_to(ROOT)),
        'base_sha256': source_sha, 'presentation_source': str(presentation.relative_to(ROOT)),
        'presentation_sha256': presentation_sha, 'recipe': str(Path(__file__).relative_to(ROOT)),
        'recipe_sha256': sha(Path(__file__)), 'palette_source': str(palette_path.relative_to(ROOT)),
        'palette_sha256': sha(palette_path), 'source': 'scene.blend', 'scene_sha256': sha(scene_path),
        'render': output.name, 'render_sha256': sha(output), 'native_blender_render': True,
        'transparent': True, 'static_pose': True, 'size': [args.size, args.size],
        'samples': args.samples, 'denoising': scene.cycles.use_denoising,
        'camera': {'position': list(cam.location), 'target': list(target), 'lens': cam.data.lens},
        'checks': {'character_inputs_unchanged': True, 'framing': framing_ok, 'arm_lengths_preserved': True},
        'controls': {k: float(rig[k]) for k in rig.keys() if k.startswith('face_') and isinstance(rig[k], (int, float))},
    }
    (output_dir / 'scene.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('SCOUT_RENDERED', output, flush=True)


if __name__ == '__main__':
    main()
