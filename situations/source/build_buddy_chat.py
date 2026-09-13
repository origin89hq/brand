"""Build and render Buddy's editable chat-bubble social scene from the shared rig."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'buddy/blender'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from studio import configure, expression, avatar, device
from finish import render_quality
from chat_geometry import rounded, shape, logo


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def linear(value):
    channels = [int(value[i:i+2], 16)/255 for i in (1, 3, 5)]
    return tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in channels)+(1,)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--width', type=int, default=2560)
    parser.add_argument('--samples', type=int, default=192)
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--no-render', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if args.width < 320 or args.width % 2 or args.samples < 1:
        parser.error('width must be even and at least 320; samples must be positive')
    out = ROOT / ('.build/buddy-chat' if args.draft else 'situations/scenes/buddy-chat')
    out.mkdir(parents=True, exist_ok=True)
    master = ROOT/'buddy/blender/buddy.blend'
    presentation = ROOT/'buddy/presentation/face-front.blend'
    input_hashes = {str(path.relative_to(ROOT)): sha(path) for path in (master, presentation)}
    assert json.loads((presentation.parent/'face-front-source.json').read_text())['base_sha256'] == sha(master)
    bpy.ops.wm.open_mainfile(filepath=str(master))
    configure(bpy.context.scene, True)
    expression(bpy.context.scene, 'welcoming', pose='standing')
    avatar(bpy.context.scene, 'welcoming', isolated=False)
    rig = bpy.data.objects['Buddy | pose rig']
    rig.animation_data.action = None
    pose = {bone.name: bone.matrix_basis.copy() for bone in rig.pose.bones}
    bpy.ops.wm.open_mainfile(filepath=str(presentation))
    scene = bpy.context.scene
    scene.name = 'Buddy | Chat social cover'
    layer = configure(scene, False)
    rig = bpy.data.objects['Buddy | pose rig']
    rig.animation_data.action = None
    for name, matrix in pose.items():
        rig.pose.bones[name].matrix_basis = matrix
    for name, value in {'jaw_open': .035, 'smile': .5, 'tongue_out': 0,
                        'brow_raise_L': .22, 'brow_raise_R': .10,
                        'upper_lid_L': .01, 'upper_lid_R': .01,
                        'lower_lid_L': .09, 'lower_lid_R': .12}.items():
        rig['face_'+name] = value
    rig.update_tag()
    bpy.context.view_layer.update()

    def point(name, direction):
        bone = rig.pose.bones[name]
        matrix = bone.matrix.copy()
        axis = matrix.to_quaternion() @ Vector((0, 1, 0))
        rotated = axis.rotation_difference(Vector(direction).normalized()).to_matrix().to_4x4() @ matrix
        rotated.translation = matrix.translation
        bone.matrix = rotated
        bpy.context.view_layer.update()

    for side, target, hand_direction in (
        ('L', (.86, -.19, 1.55), (.25, -.45, .8)),
        ('R', (-.52, -.44, .90), (0, -.65, -.65)),
    ):
        upper, lower = rig.pose.bones['upper_arm.'+side], rig.pose.bones['forearm.'+side]
        shoulder = upper.head.copy()
        delta = Vector(target)-shoulder
        distance, axis = delta.length, delta.normalized()
        assert abs(upper.length-lower.length) < distance < upper.length+lower.length
        along = (upper.length**2-lower.length**2+distance**2)/(2*distance)
        bend = Vector((1 if side == 'L' else -1, 0, -.6))
        bend = (bend-axis*bend.dot(axis)).normalized()
        elbow = shoulder+along*axis+bend*math.sqrt(upper.length**2-along**2)
        point(upper.name, elbow-shoulder)
        point(lower.name, Vector(target)-elbow)
        point('hand.'+side, hand_direction)
    head = rig.pose.bones['head']
    head_matrix = head.matrix.copy()
    tilted = Matrix.Rotation(math.radians(-9), 4, 'Z') @ Matrix.Rotation(math.radians(-4), 4, 'Y') @ head_matrix
    tilted.translation = head_matrix.translation
    head.matrix = tilted
    rig.update_tag()
    bpy.context.view_layer.update()
    scene.frame_start = scene.frame_end = 1
    scene.frame_set(1)
    scene.timeline_markers.clear()
    scene.timeline_markers.new('Static explanatory pose', frame=1)
    character_objects = [obj for obj in scene.objects if obj.type in ('MESH', 'CURVE', 'CURVES')
                         and not obj.name.startswith(('Studio |', 'Presentation |'))]
    props = bpy.data.collections.new('Chat | editable bubble and cards')
    branding = bpy.data.collections.new('Brand | editable logo and text')
    scene.collection.children.link(props)
    scene.collection.children.link(branding)
    palette_path = ROOT/'identity/tokens/brand-tokens.json'
    palette = json.loads(palette_path.read_text())
    dark, light = palette['themes']['dark'], palette['themes']['light']

    def material(name, colour, roughness=.5, emission=False):
        result = bpy.data.materials.new(name)
        result.use_nodes = True
        if emission:
            result.node_tree.nodes.clear()
            shader = result.node_tree.nodes.new('ShaderNodeEmission')
            shader.inputs['Color'].default_value = linear(colour)
            shader.inputs['Strength'].default_value = 1.6
            output = result.node_tree.nodes.new('ShaderNodeOutputMaterial')
            result.node_tree.links.new(shader.outputs[0], output.inputs['Surface'])
        else:
            shader = result.node_tree.nodes.get('Principled BSDF')
            shader.inputs['Base Color'].default_value = linear(colour)
            shader.inputs['Roughness'].default_value = roughness
        return result

    blue = material('Chat | Origin89 blue', palette['brand']['blue'], .46)
    inner_blue = material('Chat | inset blue', palette['materials_3d']['shell'], .46)
    cream = material('Cards | warm paper', light['page'], .62)
    white = material('Brand | white emission', '#ffffff', emission=True)
    ink = material('Brand | ink emission', dark['page'], emission=True)
    muted = material('Brand | secondary label', dark['muted'], emission=True)
    floor_mat = material('Stage | midnight blue', dark['page'], .9)
    floor_shader = floor_mat.node_tree.nodes['Principled BSDF']
    floor_shader.inputs['Specular IOR Level'].default_value = 0

    # The shader reveal hides the waist below the bubble without deleting rigged geometry.
    reveal = bpy.data.objects.new('Chat | waist reveal height', None)
    props.objects.link(reveal)
    reveal.location.z = .80
    reveal.empty_display_size = .15
    copied = {}
    for obj in character_objects:
        for slot in obj.material_slots:
            original = slot.material
            if original is None or not original.use_nodes:
                continue
            if original.name not in copied:
                mat = original.copy()
                mat.name = 'Chat reveal | '+original.name
                nodes, links = mat.node_tree.nodes, mat.node_tree.links
                output = next(node for node in nodes if node.type == 'OUTPUT_MATERIAL' and node.is_active_output)
                previous = output.inputs['Surface'].links[0].from_socket
                geometry = nodes.new('ShaderNodeNewGeometry')
                separate = nodes.new('ShaderNodeSeparateXYZ')
                below = nodes.new('ShaderNodeMath'); below.operation = 'LESS_THAN'
                transparent = nodes.new('ShaderNodeBsdfTransparent')
                mix = nodes.new('ShaderNodeMixShader')
                links.new(geometry.outputs['Position'], separate.inputs[0])
                links.new(separate.outputs['Z'], below.inputs[0])
                driver = below.inputs[1].driver_add('default_value').driver
                variable = driver.variables.new(); variable.name = 'height'; variable.type = 'TRANSFORMS'
                variable.targets[0].id = reveal; variable.targets[0].transform_type = 'LOC_Z'
                variable.targets[0].transform_space = 'WORLD_SPACE'; driver.expression = 'height'
                links.new(below.outputs[0], mix.inputs[0])
                links.new(previous, mix.inputs[1]); links.new(transparent.outputs[0], mix.inputs[2])
                links.new(mix.outputs[0], output.inputs['Surface'])
                copied[original.name] = mat
            slot.material = copied[original.name]

    outer = rounded(2.30, 1.32, .28)
    outer.extend([(-.75, -.66), (-.88, -.93), (-.88, -.955), (-.86, -.96), (-.26, -.66)])
    bubble = shape(props, 'Chat | speech bubble frame', [outer, list(reversed(rounded(1.91, .98, .18)))],
                   blue, (0, -.12, 1.30), .055, .04)
    bubble.rotation_euler.x = math.radians(60)
    shape(props, 'Chat | inset backing', [rounded(2.10, 1.14, .23)], inner_blue, (0, .34, 1.19), .04, .025)
    font = bpy.data.fonts.load(str(ROOT/'fonts/InterTight-600.ttf')); font.pack()
    mono = bpy.data.fonts.load(str(ROOT/'fonts/IBMPlexMono-Regular.ttf')); mono.pack()

    def text(name, body, location, size, mat, face=font, collection=branding):
        data = bpy.data.curves.new(name, 'FONT'); data.body = body; data.font = face
        data.size = size; data.align_x = 'LEFT'; data.resolution_u = 24
        obj = bpy.data.objects.new(name, data); collection.objects.link(obj)
        obj.location = location; obj.rotation_euler.x = math.pi/2
        data.materials.append(mat)
        return obj

    for name, position, angle in (
        ('Question', (-1.52, -.04, 1.91), -12),
        ('Conversation', (1.61, .08, 1.93), 11),
        ('Answer', (1.65, -.05, .99), 13),
    ):
        card = shape(props, 'Card | '+name, [rounded(.72, .63, .11)], cream, position, .055, .035)
        card.rotation_euler.y = math.radians(angle)
        if name == 'Question':
            question = text('Card | question mark', '?', (0, 0, 0), .58, blue, collection=props)
            question.parent = card; question.rotation_euler = (0, 0, 0)
            question.location = (-.13, -.19, .095)
            question.data.extrude = .012; question.data.bevel_depth = .006
        elif name == 'Conversation':
            for x in (-.20, 0, .20):
                bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=.06)
                dot = bpy.context.object
                for collection in list(dot.users_collection): collection.objects.unlink(dot)
                props.objects.link(dot); dot.name = 'Card | conversation dot'; dot.parent = card
                dot.location = (x, 0, .10); dot.scale.z = .45
                dot.data.materials.append(blue)
                for polygon in dot.data.polygons: polygon.use_smooth = True
        else:
            for index, width in enumerate((.43, .43, .29)):
                bar = shape(props, 'Card | answer line '+str(index+1), [rounded(width, .048, .023)], blue, (0, 0, 0), .012, .009)
                bar.parent = card; bar.rotation_euler = (0, 0, 0)
                bar.location = (-.215+width/2, .16-.16*index, .10)

    for name in ('Studio | seamless floor', 'Presentation | seamless sweep'):
        obj = bpy.data.objects.get(name)
        if obj:
            obj.hide_render = True
            obj.data.materials.clear(); obj.data.materials.append(floor_mat)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, .01))
    floor = bpy.context.object
    floor.name = 'Chat | native shadow floor'
    for collection in list(floor.users_collection): collection.objects.unlink(floor)
    props.objects.link(floor)
    floor.data.materials.append(floor_mat)
    for obj in scene.objects:
        if obj.type == 'LIGHT' and obj.name == 'Backdrop | soft pool':
            obj.data.color = (.22, .40, 1); obj.data.energy = 160
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (.18, .23, .35, 1)
    background.inputs['Strength'].default_value = .07
    camera = scene.camera
    camera.data.type = 'ORTHO'; camera.data.ortho_scale = 8
    camera.location = (-1.5, -10, 2.575)
    camera.rotation_euler = (Vector((-1.5, 0, 1.7))-camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.resolution_x = args.width; scene.render.resolution_y = args.width//2
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'; scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    mark = logo(branding, ROOT/'logos/origin89-horizontal-white.svg', {'#ffffff': white, dark['page']: ink}, (0, 0, 0), 1.7875)
    mark.parent = camera; mark.location = (-3.6, 1.525, -7.2)
    for child in mark.children:
        child.rotation_euler = (0, 0, 0)
        child.location.z = -child.location.y; child.location.y = 0
    for obj, position in (
        (text('Brand | Buddy title', 'Buddy', (0, 0, 0), 1.03, white), (-3.6, -.04, -7.2)),
        (text('Brand | package name', '@origin89/buddy', (0, 0, 0), .196, muted, mono), (-3.5875, -.375, -7.2)),
    ):
        obj.parent = camera; obj.location = position; obj.rotation_euler = (0, 0, 0)
    render_quality(scene, args.samples)
    scene.cycles.adaptive_min_samples = min(32, args.samples)
    scene.cycles.adaptive_threshold = .04 if args.draft else .009
    scene.cycles.transparent_max_bounces = 24
    device(scene)
    bpy.context.view_layer.update()
    assert all(abs(value-1) < .001 for bone in rig.pose.bones for value in bone.matrix.to_scale())
    graph = bpy.context.evaluated_depsgraph_get()
    framing = {}
    for obj in scene.objects:
        if obj.name.startswith(('Antler |', 'Card |')) and obj.type in ('MESH', 'CURVE'):
            evaluated = obj.evaluated_get(graph)
            mesh = evaluated.to_mesh()
            corners = [world_to_camera_view(scene, camera, evaluated.matrix_world @ vertex.co) for vertex in mesh.vertices]
            evaluated.to_mesh_clear()
            framing[obj.name] = {'x': [min(p.x for p in corners), max(p.x for p in corners)],
                                 'y': [min(p.y for p in corners), max(p.y for p in corners)]}
    assert all(.025 < value < .975 for bounds in framing.values() for axis in bounds.values() for value in axis), framing
    scene['buddy_source_sha256'] = input_hashes['buddy/blender/buddy.blend']
    scene['source_type'] = 'Native Buddy rig, editable curves, packed fonts, native stage and lights'
    notes = bpy.data.texts.new('READ ME | Buddy chat')
    notes.write('F12 renders this live scene. Buddy uses the canonical rig, geometry, fur, and face controls.\n'
                'Chat props are editable curves and meshes; Brand contains the original outlined logo and packed-font text.\n'
                'Move Chat | waist reveal height to change the non-destructive shader reveal below the bubble.\n'
                'The pose is static. Rebuilding recreates the saved source; preserve manual edits before rebuilding.\n')
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D': area.spaces.active.region_3d.view_perspective = 'CAMERA'
    bpy.ops.object.select_all(action='DESELECT')
    bubble.select_set(True); bpy.context.view_layer.objects.active = bubble
    scene.render.filepath = '//buddy-social.png'
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'), compress=True)
    if not args.no_render:
        scene.render.filepath = str(out/'buddy-social.png')
        bpy.ops.render.render(write_still=True, layer=layer.name)
    assert all(sha(ROOT/path) == digest for path, digest in input_hashes.items())
    metadata = {'base': 'buddy/blender/buddy.blend', 'inputs': input_hashes,
                'recipe': 'situations/source/build_buddy_chat.py',
                'source_files': {str(path.relative_to(ROOT)): sha(path) for path in (
                    Path(__file__), Path(__file__).with_name('chat_geometry.py'), palette_path,
                    ROOT/'logos/origin89-horizontal-white.svg', ROOT/'fonts/InterTight-600.ttf', ROOT/'fonts/IBMPlexMono-Regular.ttf')},
                'native_character': True, 'native_props': True, 'native_branding': True, 'static_pose': True,
                'width': args.width, 'height': args.width//2, 'samples': args.samples,
                'framing': framing, 'arm_lengths_preserved': True, 'character_inputs_unchanged': True,
                'scene_sha256': sha(out/'scene.blend')}
    if not args.no_render: metadata['render_sha256'] = sha(out/'buddy-social.png')
    (out/'scene.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print('BUDDY_CHAT_READY', out, flush=True)


if __name__ == '__main__':
    main()
