"""Render the website's site miniatures: a cottage, a telecom shelter and a mine utility.

The scenes come from site_scenes.py, which models each one from primitives in an
empty file. From the repository root:

    blender --background --python-exit-code 1 \\
      --python situations/source/build_site_miniatures.py -- --out /tmp/home-media/dioramas

Each site stands on a black plinth under an orthographic studio camera, in the same
world as the website's Controller renders. Writes
audience-{cottage,telecom,mine}.png (1400 x 1100 transparent RGBA, 128 samples),
audience-<site>-signals.json with each signal path projected through the camera
(pixel coordinates in that image, in the direction data flows, toward the
building), and the matching .blend for editing. The website animates pulses
along those paths. --out defaults to .build/site-miniatures/; --only renders a
subset; --samples lowers the sample count for test renders.

build_site_views.py renders the same scenes wide, over a field, for the site pages.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))  # Blender does not add the script's directory
from site_scenes import ROOT, SAMPLES, SCENES, SIGNALS, link, palette, plinth, reset  # noqa: E402


def studio(s, scale, target=(0, 0, .12)):
    cam_d = bpy.data.cameras.new('cam')
    cam_d.type = 'ORTHO'
    cam_d.ortho_scale = scale
    cam = link(bpy.data.objects.new('cam', cam_d))
    az, el, dist = math.radians(-38), math.radians(30), 4.
    t = Vector(target)
    cam.location = t + Vector((math.sin(az) * math.cos(el) * dist, -math.cos(az) * math.cos(el) * dist, math.sin(el) * dist))
    cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler()
    s.camera = cam

    def area(name, loc, energy, size, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, 'AREA')
        d.shape = 'DISK'
        d.size = size
        d.energy = energy
        d.color = color
        ob = link(bpy.data.objects.new(name, d))
        ob.location = loc
        ob.rotation_euler = (t - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        ob.visible_camera = False
        return ob

    area('key', (-1.6, -1.2, 2.2), 90, 1.4, (1., .97, .93))
    area('rim', (1.2, 2.1, .55), 200, .8, (.38, .52, 1.))
    area('fill', (1.8, -1.6, .6), 18, 2.)


parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--out', type=Path, default=ROOT / '.build/site-miniatures')
parser.add_argument('--only', nargs='+', choices=tuple(SCENES), default=())
parser.add_argument('--samples', type=int, default=SAMPLES)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
OUT = args.out
ONLY = set(args.only)
OUT.mkdir(parents=True, exist_ok=True)
for name, build in SCENES.items():
    if ONLY and name not in ONLY:
        continue
    s = reset()
    s.cycles.samples = args.samples
    M = palette()
    SIGNALS.clear()
    build(M, plinth)
    studio(s, 1.6 if name != 'telecom' else 1.75, target=(0, 0, .12 if name != 'telecom' else .27))
    s.render.resolution_x, s.render.resolution_y = 1400, 1100
    w, h = s.render.resolution_x, s.render.resolution_y
    bpy.context.view_layer.update()  # the camera's world matrix is stale until the scene updates
    paths = []
    for signal, points in SIGNALS:
        projected = [world_to_camera_view(s, s.camera, Vector(p)) for p in points]
        paths.append({'name': signal, 'points': [[round(co.x * w, 1), round((1 - co.y) * h, 1)] for co in projected]})
    (OUT / f'audience-{name}-signals.json').write_text(json.dumps({'width': w, 'height': h, 'paths': paths}, indent=1) + '\n')
    s.render.filepath = str(OUT / f'audience-{name}.png')
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / f'audience-{name}.blend'))
