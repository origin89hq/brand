"""Render front-facing avatars without overwriting the authored Blender scene."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'buddy/blender'))
from studio import configure, expression, avatar, device
from finish import render_quality

EXPRESSIONS = ('welcoming', 'explaining', 'thinking', 'delighted', 'concerned', 'surprised', 'playful')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(expression_name, size=1920, samples=256, *, scene_source=None, output_dir=None):
    master = ROOT / 'buddy/blender/buddy.blend'
    scene_source = scene_source or FOLDER / 'face-front.blend'
    output_dir = output_dir or FOLDER
    source_sha, scene_sha = sha(master), sha(scene_source)
    lineage = json.loads((FOLDER / 'face-front-source.json').read_text())
    assert lineage['base_sha256'] == source_sha, 'Rebase the editable avatar scene on the changed Buddy model before rendering'

    # Other expressions use the canonical keyed controls and body gestures.
    # The authored greeting, head/ear pose, camera, lights and materials belong
    # to face-front.blend and must survive every render.
    pose, controls = {}, {}
    if expression_name != 'welcoming':
        bpy.ops.wm.open_mainfile(filepath=str(master))
        scene = bpy.context.scene
        configure(scene, True, 'brown', 'fur')
        expression(scene, expression_name)
        avatar(scene, expression_name, isolated=False)
        rig = bpy.data.objects['Buddy | pose rig']
        if rig.animation_data:
            rig.animation_data.action = None
        rig.update_tag()
        bpy.context.view_layer.update()
        pose = {bone.name: bone.matrix_basis.copy() for bone in rig.pose.bones if bone.name not in ('head', 'ear.L', 'ear.R')}
        controls = {key: float(rig[key]) for key in rig.keys() if key.startswith('face_') and isinstance(rig[key], (int, float))}

    bpy.ops.wm.open_mainfile(filepath=str(scene_source))
    scene = bpy.context.scene
    layer = configure(scene, True, 'brown', 'fur')
    rig = bpy.data.objects['Buddy | pose rig']
    if rig.animation_data:
        rig.animation_data.action = None
    for name, matrix in pose.items():
        rig.pose.bones[name].matrix_basis = matrix
    for key, value in controls.items():
        rig[key] = value
    rig.update_tag()
    bpy.context.view_layer.update()

    # The delivery format is transparent; keep the set's indirect illumination.
    bpy.data.objects['Presentation | seamless sweep'].visible_camera = False
    render_quality(scene, samples, True)
    scene.cycles.adaptive_min_samples = min(64, samples)
    scene.cycles.adaptive_threshold = .006
    device(scene)
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    stem = 'face-front' + ('' if expression_name == 'welcoming' else '-' + expression_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / (stem + '.png')
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True, layer=layer.name)
    assert sha(master) == source_sha and sha(scene_source) == scene_sha, 'Rendering must not change an authored scene'
    camera = scene.camera
    metadata = {
        'base': str(master.relative_to(ROOT)), 'source_sha256': source_sha,
        'scene_source': str(scene_source.relative_to(ROOT)), 'scene_source_sha256': scene_sha,
        'recipe_sha256': sha(Path(__file__)), 'render_sha256': sha(output),
        'look': 'face-front', 'expression': expression_name,
        'size': [size, size], 'samples': samples,
        'camera': {'type': camera.data.type, 'lens': camera.data.lens, 'position': list(camera.location), 'rotation': list(camera.rotation_euler)},
        'transparent': True, 'alpha': 'Native Cycles coverage; green added only to avatar exports',
        'controls': {key: rig[key] for key in rig.keys() if key.startswith('face_') and isinstance(rig[key], (float, int))},
        'preserved': ['authored avatar scene', 'greeting controls', 'head and ear pose', 'camera', 'lights', 'materials', 'native geometry', 'fur'],
        'denoising': scene.cycles.use_denoising, 'depth_of_field': camera.data.dof.use_dof,
    }
    output.with_suffix('.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('FACE_FRONT_RENDERED', output, flush=True)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expression', choices=EXPRESSIONS, default='welcoming')
    parser.add_argument('--size', type=int, default=1920)
    parser.add_argument('--samples', type=int, default=256)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    render(args.expression, args.size, args.samples)


if __name__ == '__main__':
    main()
