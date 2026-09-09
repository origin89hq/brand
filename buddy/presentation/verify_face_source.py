"""Blender regression: manual avatar edits survive rendering and change output."""
import json
import sys
from pathlib import Path

import bpy

FOLDER = Path(__file__).resolve().parent
sys.path.insert(0, str(FOLDER))
from render_face import ROOT, render, sha

source = FOLDER / 'face-front.blend'
source_sha = sha(source)
output = ROOT / '.build/face-source-check'
output.mkdir(parents=True, exist_ok=True)
baseline = render('welcoming', 96, 8, output_dir=output / 'baseline')

bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene
scene.camera.data.lens = 120
scene.camera.location.x += .12
bpy.data.objects['Bounce | face'].data.energy = 310
rig = bpy.data.objects['Buddy | pose rig']
rig['face_brow_raise_L'] = .48
rig.update_tag()
bpy.context.view_layer.update()
edited = output / 'edited.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(edited), compress=True)
edited_sha = sha(edited)
greeting = render('welcoming', 96, 8, scene_source=edited, output_dir=output / 'edited')
assert greeting['camera']['lens'] == 120
assert abs(greeting['camera']['position'][0] - .12) < 1e-6
assert greeting['controls']['face_brow_raise_L'] == .48
assert bpy.data.objects['Bounce | face'].data.energy == 310
assert greeting['render_sha256'] != baseline['render_sha256']
thinking = render('thinking', 96, 8, scene_source=edited, output_dir=output / 'edited')
assert thinking['camera'] == greeting['camera']
assert bpy.data.objects['Bounce | face'].data.energy == 310
assert thinking['controls'] != greeting['controls']
assert sha(source) == source_sha and sha(edited) == edited_sha
assert greeting['scene_source_sha256'] == edited_sha == thinking['scene_source_sha256']
(output / 'checks.json').write_text(json.dumps({
    'passed': True, 'authoredSourceUnchanged': True, 'editedSourceUnchanged': True,
    'cameraEditUsed': True, 'lightEditUsed': True, 'greetingEditUsed': True,
    'editsChangeRenderedPixels': True, 'expressionRetainsAuthoredCameraAndLight': True,
}, indent=2) + '\n')
print('PASS: edited avatar camera, light and greeting affect rendering without overwriting either Blender scene')
