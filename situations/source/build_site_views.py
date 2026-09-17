"""Render the website's site views: a cottage, a telecom shelter and a mine utility.

The scenes come from site_scenes.py, the same models the miniatures use, but
standing on an open field under a perspective camera instead of a plinth. From the
repository root:

    blender --background --python-exit-code 1 \\
      --python situations/source/build_site_views.py -- --out /tmp/site-views

Writes site-{cottage,telecom,mine}.png (1536 x 1024 opaque, 160 samples) and the
matching .blend for editing. Night on the site: a graded sky, ground fading into
the horizon with distance, warm light in the windows, one green status light per
site and blue signal paths between the equipment. The equipment is generic and
unbranded, and no scene shows a real installation. --out defaults to
.build/site-views/; --only renders a subset; --samples lowers the sample count for
test renders.
"""
import argparse
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))  # Blender does not add the script's directory
from site_scenes import ROOT, SCENES, SIGNALS, box, link, palette, reset, tree  # noqa: E402

SAMPLES = 160
WIDTH, HEIGHT = 1536, 1024
# The sky, and the colour the ground fades into at the horizon.
ZENITH = (.0025, .0035, .006)
HORIZON = (.020, .027, .042)
# Where the ground starts and finishes fading into the horizon, in camera depth.
FADE = (1.6, 8.5)
# Each site's camera: where it looks, from which bearing, height angle, distance and lens.
VIEWS = {
    'cottage': {'target': (.0, .04, .13), 'az': 25, 'el': 14, 'dist': 1.8, 'lens': 45},
    'telecom': {'target': (.0, .05, .30), 'az': 25, 'el': 12, 'dist': 2.3, 'lens': 42},
    'mine': {'target': (.0, .0, .13), 'az': -35, 'el': 15, 'dist': 2.0, 'lens': 45},
}


def sky(s):
    """A graded night sky: ZENITH overhead, HORIZON at eye level."""
    w = bpy.data.worlds.new('sky')
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    height = nt.nodes.new('ShaderNodeMapRange')
    axis = nt.nodes.new('ShaderNodeSeparateXYZ')
    ray = nt.nodes.new('ShaderNodeNewGeometry')
    # The ray's vertical component, 0 at the horizon, 1 overhead.
    height.inputs['From Min'].default_value = -.02
    height.inputs['From Max'].default_value = .42
    ramp.color_ramp.elements[0].color = (*HORIZON, 1)
    ramp.color_ramp.elements[1].color = (*ZENITH, 1)
    nt.links.new(ray.outputs['Incoming'], axis.inputs['Vector'])
    nt.links.new(axis.outputs['Z'], height.inputs['Value'])
    nt.links.new(height.outputs['Result'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    s.world = w


def field(M):
    """A wide ground plane that fades into the horizon with distance."""
    m = bpy.data.materials.new('field')
    m.use_nodes = True
    nt = m.node_tree
    surface = nt.nodes['Principled BSDF']
    surface.inputs['Base Color'].default_value = (.015, .017, .022, 1)
    surface.inputs['Roughness'].default_value = .88
    grain = nt.nodes.new('ShaderNodeTexNoise')
    grain.inputs['Scale'].default_value = 26.
    grain.inputs['Detail'].default_value = 8.
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .28
    nt.links.new(grain.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], surface.inputs['Normal'])
    # Past FADE the ground reads as the sky it meets.
    haze = nt.nodes.new('ShaderNodeEmission')
    haze.inputs['Color'].default_value = (*HORIZON, 1)
    depth = nt.nodes.new('ShaderNodeCameraData')
    into = nt.nodes.new('ShaderNodeMapRange')
    into.inputs['From Min'].default_value = FADE[0]
    into.inputs['From Max'].default_value = FADE[1]
    blend = nt.nodes.new('ShaderNodeMixShader')
    out = nt.nodes['Material Output']
    nt.links.new(depth.outputs['View Z Depth'], into.inputs['Value'])
    nt.links.new(into.outputs['Result'], blend.inputs['Fac'])
    nt.links.new(surface.outputs['BSDF'], blend.inputs[1])
    nt.links.new(haze.outputs['Emission'], blend.inputs[2])
    nt.links.new(blend.outputs['Shader'], out.inputs['Surface'])
    return box('field', (30., 30., .02), (0, 0, -.01), m, bev=0)


def rock(name, loc, r, M, rng):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)
    for v in bm.verts:
        v.co *= rng.uniform(.75, 1.2)
        v.co.z *= rng.uniform(.45, .8)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M['rock'])
    ob = link(bpy.data.objects.new(name, me))
    ob.location = (*loc, r * .25)
    ob.rotation_euler = (0, 0, rng.uniform(0, math.tau))
    return ob


def scatter(count, near, far, cam, rng):
    """Positions in a ring around the equipment, skipping the camera's near field."""
    eye = Vector((cam.location.x, cam.location.y))
    reach = eye.length * .85  # nothing between the camera and the site it came to look at
    placed = []
    while len(placed) < count:
        a, r = rng.uniform(0, math.tau), rng.uniform(near, far)
        p = Vector((math.cos(a) * r, math.sin(a) * r))
        if (p - eye).length < reach:
            continue  # between the camera and the site
        placed.append(p)
    return placed


def surroundings(name, M, cam):
    """Sparse terrain around the equipment, so the site sits in a place."""
    rng = random.Random(89)
    if name == 'cottage':
        # Woodland closing in behind the cabin, thinning toward the water.
        for i, p in enumerate(scatter(26, .95, 3.6, cam, rng)):
            tree(f'wood {i}', (p.x, p.y), rng.uniform(.3, .58), M)
    elif name == 'telecom':
        # Open tundra: low rocks only, so the mast keeps the skyline.
        for i, p in enumerate(scatter(30, .9, 4.5, cam, rng)):
            rock(f'stone {i}', (p.x, p.y), rng.uniform(.012, .05), M, rng)
    else:
        # Waste rock, coarser the further it is from the working area.
        for i, p in enumerate(scatter(30, .8, 4.2, cam, rng)):
            spread = min(p.length / 4.2, 1.)
            rock(f'stone {i}', (p.x, p.y), rng.uniform(.02, .04 + spread * .11), M, rng)


def camera(s, view):
    cam_d = bpy.data.cameras.new('cam')
    cam_d.lens = view['lens']
    cam = link(bpy.data.objects.new('cam', cam_d))
    az, el = math.radians(view['az']), math.radians(view['el'])
    dist = view['dist']
    t = Vector(view['target'])
    cam.location = t + Vector((math.sin(az) * math.cos(el) * dist, -math.cos(az) * math.cos(el) * dist, math.sin(el) * dist))
    cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler()
    s.camera = cam
    return cam


def lights(target):
    t = Vector(target)

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

    # The same rig as the miniatures, opened up for a wide frame: a cool moon key
    # from the left, a blue rim behind, and a low fill toward the camera.
    area('key', (-2.4, 1.6, 2.6), 70, 2.2, (.78, .85, 1.))
    area('rim', (1.8, 2.8, .8), 110, 1.2, (.38, .52, 1.))
    area('fill', (2.2, -2.4, .7), 10, 3.)


parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--out', type=Path, default=ROOT / '.build/site-views')
parser.add_argument('--only', nargs='+', choices=tuple(SCENES), default=())
parser.add_argument('--samples', type=int, default=SAMPLES)
parser.add_argument('--scale', type=int, default=100, help='render at this percent of 1536 x 1024')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
OUT = args.out
ONLY = set(args.only)
OUT.mkdir(parents=True, exist_ok=True)
for name, build in SCENES.items():
    if ONLY and name not in ONLY:
        continue
    s = reset()
    s.cycles.samples = args.samples
    s.render.film_transparent = False
    s.render.image_settings.color_mode = 'RGB'
    M = palette()
    SIGNALS.clear()
    build(M, field)
    view = VIEWS[name]
    cam = camera(s, view)
    surroundings(name, M, cam)
    lights(view['target'])
    sky(s)
    s.render.resolution_x, s.render.resolution_y = WIDTH, HEIGHT
    s.render.resolution_percentage = args.scale
    s.render.filepath = str(OUT / f'site-{name}.png')
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / f'site-{name}.blend'))
