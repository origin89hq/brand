"""Render the website's site miniatures: a cottage, a telecom shelter and a mine utility.

Self-contained: each scene is modelled here from primitives in an empty file, with
no character or hardware input. From the repository root:

    blender --background --python-exit-code 1 \\
      --python situations/source/build_site_miniatures.py -- --out /tmp/home-media/dioramas

Same world as the website's Controller renders: dark satin materials on black
plinths, a soft key, a blue rim, one green status light per site and blue signal
paths on the ground. The equipment is generic and unbranded. Writes
audience-{cottage,telecom,mine}.png (1400 x 1100 transparent RGBA, 128 samples),
audience-<site>-signals.json with each signal path projected through the camera
(pixel coordinates in that image, in the direction data flows, toward the
building), and the matching .blend for editing. The website animates pulses
along those paths. --out defaults to .build/site-miniatures/; --only renders a
subset; --samples lowers the sample count for test renders.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = 128
# Signal paths drawn by the scene builders, as (name, points) in world space.
SIGNALS = []


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == 'METAL'
    s.cycles.device = 'GPU'
    s.cycles.samples = SAMPLES
    s.cycles.use_denoising = True
    s.render.film_transparent = True
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGBA'
    s.view_settings.view_transform = 'AgX'
    s.view_settings.look = 'AgX - Medium High Contrast'
    w = bpy.data.worlds.new('World')
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (.02, .025, .035, 1)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = .2
    s.world = w
    return s


MATS = {}


def mat(name, color, rough=.55, metal=0., emit=None, strength=0., coat=0.):
    key = name
    if key in MATS:
        return MATS[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Coat Weight'].default_value = coat
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = strength
    MATS[key] = m
    return m


def palette():
    MATS.clear()
    return {
        'plinth': mat('plinth', (.026, .03, .038), .45, coat=.3),
        'ground': mat('ground', (.016, .018, .024), .92),
        'body': mat('body', (.082, .088, .1), .5),
        'body2': mat('body2', (.1, .107, .12), .45),
        'roof': mat('roof', (.04, .044, .05), .35, metal=.6),
        'trim': mat('trim', (.18, .19, .2), .4, metal=.8),
        'glass': mat('glass', (.01, .015, .03), .08, coat=1.),
        'window': mat('window', (.9, .6, .3), .4, emit=(1., .62, .3), strength=3.),
        'solar': mat('solar', (.01, .02, .06), .12, coat=1.),
        'tree': mat('tree', (.02, .035, .028), .75),
        'trunk': mat('trunk', (.03, .025, .02), .8),
        'rock': mat('rock', (.045, .047, .05), .85),
        'signal': mat('signal', (.02, .06, .25), .3, emit=(.08, .24, 1.), strength=3.2),
        'status': mat('status', (.1, .6, .3), .3, emit=(.18, .62, .39), strength=10.),
        'beacon': mat('beacon', (.9, .5, .1), .3, emit=(.91, .63, .24), strength=12.),
        'tank': mat('tank', (.12, .126, .135), .38, metal=.7),
    }


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def bevel(ob, width=.004, segs=2):
    m = ob.modifiers.new('bevel', 'BEVEL')
    m.width = width
    m.segments = segs
    m.limit_method = 'ANGLE'
    return ob


def box(name, size, loc, m, rot=(0, 0, 0), bev=.004):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    ob = link(bpy.data.objects.new(name, me))
    ob.location = loc
    ob.rotation_euler = rot
    if bev:
        bevel(ob, bev)
    return ob


def cyl(name, r, depth, loc, m, rot=(0, 0, 0), verts=32, r2=None, smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r, radius2=r if r2 is None else r2, depth=depth)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    me.materials.append(m)
    ob = link(bpy.data.objects.new(name, me))
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def prism(name, w, d, h, loc, m, overhang=.03):
    """Gable roof along X: width w (X), depth d (Y), ridge height h."""
    bm = bmesh.new()
    x0, x1 = -w / 2 - overhang, w / 2 + overhang
    y0, y1 = -d / 2 - overhang, d / 2 + overhang
    t = .012
    pts = []
    for x in (x0, x1):
        pts.append([bm.verts.new((x, y0, 0)), bm.verts.new((x, 0, h)), bm.verts.new((x, y1, 0)),
                    bm.verts.new((x, y1, -t)), bm.verts.new((x, 0, h - t * 1.4)), bm.verts.new((x, y0, -t))])
    for i in range(6):
        j = (i + 1) % 6
        bm.faces.new((pts[0][i], pts[0][j], pts[1][j], pts[1][i]))
    bm.faces.new(list(reversed(pts[0])))
    bm.faces.new(pts[1])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    ob = link(bpy.data.objects.new(name, me))
    ob.location = loc
    return ob


def tube(name, points, r, m):
    if m.name == 'signal':
        SIGNALS.append((name, points))
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = r
    cu.bevel_resolution = 4
    sp = cu.splines.new('POLY')
    sp.points.add(len(points) - 1)
    for p, co in zip(sp.points, points):
        p.co = (*co, 1)
    cu.materials.append(m)
    return link(bpy.data.objects.new(name, cu))


def tree(name, loc, h, M):
    x, y = loc
    cyl(name + ' trunk', .008, h * .25, (x, y, h * .125), M['trunk'], verts=10)
    for k, (rr, zz) in enumerate(((.075, .3), (.06, .5), (.042, .68))):
        cyl(f'{name} tier {k}', h * rr, h * .38, (x, y, h * zz), M['tree'], verts=9, r2=0., smooth=False)


def plinth(M, w=1.3, d=1.0):
    box('plinth', (w, d, .07), (0, 0, -.035), M['plinth'], bev=.012)
    box('ground', (w - .04, d - .04, .004), (0, 0, .002), M['ground'], bev=0)


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


def cottage(M):
    plinth(M)
    # Cabin
    box('cabin', (.40, .28, .19), (-.16, .06, .095), M['body'])
    prism('cabin roof', .40, .28, .12, (-.16, .06, .19), M['roof'])
    box('porch', (.40, .1, .014), (-.16, -.14, .007), M['body2'])
    for x in (-.35, .03):
        box('porch post', (.012, .012, .15), (x, -.18, .08), M['body2'], bev=.002)
    box('porch roof', (.44, .12, .01), (-.16, -.14, .165), M['roof'], rot=(math.radians(-12), 0, 0))
    for x in (-.27, -.05):
        box('window', (.07, .006, .07), (x, -.081, .1), M['window'], bev=.001)
    box('door', (.06, .006, .12), (-.16, -.081, .065), M['body2'], bev=.001)
    cyl('stove pipe', .012, .12, (-.06, .12, .27), M['trim'], verts=16)
    # Status light on the cabin wall: the Controller inside
    cyl('status', .011, .006, (.045, -.02, .12), M['status'], rot=(0, math.radians(90), 0), verts=16)
    # Solar rack
    for i in range(3):
        x = .22 + i * .135
        box('panel', (.125, .1, .008), (x, .22, .075), M['solar'], rot=(math.radians(28), 0, 0), bev=.002)
        box('panel frame', (.129, .104, .004), (x, .222, .071), M['trim'], rot=(math.radians(28), 0, 0), bev=0)
        for dx in (-.04, .04):
            box('leg', (.006, .006, .09), (x + dx, .25, .045), M['trim'], bev=0)
            box('leg front', (.006, .006, .05), (x + dx, .19, .025), M['trim'], bev=0)
    # Woodshed with the generator
    box('shed', (.18, .14, .12), (.35, -.2, .06), M['body'])
    box('shed roof', (.22, .18, .012), (.35, -.2, .13), M['roof'], rot=(math.radians(8), 0, 0))
    box('generator', (.09, .06, .06), (.35, -.31, .03), M['body2'])
    box('generator panel', (.03, .004, .02), (.33, -.342, .045), M['trim'], bev=0)
    # Propane tank
    cyl('propane', .035, .12, (.02, -.34, .038), M['tank'], rot=(0, math.radians(90), 0), verts=32)
    for dx in (-.045, .045):
        box('saddle', (.01, .05, .02), (.02 + dx, -.34, .01), M['trim'], bev=0)
    # Trees
    for i, (x, y, h) in enumerate(((-.55, .38, .52), (-.44, .42, .38), (-.58, .1, .44), (.05, .42, .46), (-.52, -.32, .32))):
        tree(f'tree {i}', (x, y), h, M)
    # Signal paths: panels and generator to the cabin
    z = .006
    tube('signal solar', [(.22, .19, z), (.1, .19, z), (.1, .02, z), (.04, .02, z)], .0035, M['signal'])
    tube('signal gen', [(.35, -.27, z), (.35, -.1, z), (.1, -.1, z), (.1, -.02, z), (.04, -.02, z)], .0035, M['signal'])


def telecom(M):
    plinth(M)
    # Shelter
    box('shelter', (.46, .24, .22), (-.18, .02, .11), M['body2'])
    for i in range(14):
        box('rib', (.012, .246, .2), (-.39 + i * .031, .02, .11), M['body'], bev=.001)
    box('shelter roof', (.48, .26, .012), (-.18, .02, .226), M['roof'])
    box('door', (.07, .006, .15), (-.02, -.103, .08), M['body'], bev=.001)
    box('hvac', (.06, .09, .1), (.08, .02, .09), M['body'])
    box('hvac grille', (.004, .07, .07), (.111, .02, .09), M['trim'], bev=0)
    cyl('status', .011, .006, (-.12, -.103, .19), M['status'], rot=(math.radians(90), 0, 0), verts=16)
    # Lattice tower
    base, top, H = .085, .024, .78
    cx, cy = .3, .22
    legs = []
    for k in range(3):
        a = math.radians(90 + k * 120)
        p0 = (cx + math.cos(a) * base, cy + math.sin(a) * base, 0)
        p1 = (cx + math.cos(a) * top, cy + math.sin(a) * top, H)
        tube('leg', [p0, p1], .0045, M['trim'])
        legs.append((p0, p1))
    for lvl in range(8):
        f0, f1 = lvl / 8, (lvl + 1) / 8
        for k in range(3):
            a0, b0 = legs[k]
            a1, b1 = legs[(k + 1) % 3]
            lerp = lambda p, q, f: tuple(p[i] + (q[i] - p[i]) * f for i in range(3))
            tube('brace', [lerp(a0, b0, f0), lerp(a1, b1, f1)], .0018, M['trim'])
            tube('ring', [lerp(a0, b0, f1), lerp(a1, b1, f1)], .0018, M['trim'])
    dish = cyl('dish', .05, .02, (cx - .06, cy - .02, .6), M['body2'], rot=(0, math.radians(90), math.radians(-30)), r2=.012, verts=40)
    for k in range(3):
        a = math.radians(30 + k * 120)
        box('antenna', (.018, .012, .09), (cx + math.cos(a) * .042, cy + math.sin(a) * .042, .7), M['body2'], bev=.002)
    cyl('beacon', .009, .018, (cx, cy, H + .01), M['beacon'], verts=16)
    # Genset and fuel
    box('genset', (.2, .1, .1), (.24, -.25, .05), M['body'])
    box('genset grille', (.004, .07, .06), (.141, -.25, .05), M['trim'], bev=0)
    cyl('exhaust', .007, .06, (.31, -.23, .13), M['trim'], verts=12)
    cyl('fuel tank', .045, .14, (-.34, -.3, .045), M['tank'], rot=(0, math.radians(90), 0), verts=32)
    # Fence posts
    for i in range(12):
        x = -.58 + i * .105
        cyl('post', .004, .1, (x, .44, .05), M['trim'], verts=8)
    tube('rail', [(-.58, .44, .09), (.58, .44, .09)], .0015, M['trim'])
    # Signal paths
    z = .006
    tube('signal tower', [(cx, cy - .1, z), (cx, .02, z), (.12, .02, z)], .0035, M['signal'])
    tube('signal gen', [(.24, -.19, z), (.24, -.14, z), (-.02, -.14, z), (-.02, -.1, z)], .0035, M['signal'])
    tube('signal fuel', [(-.27, -.3, z), (-.12, -.3, z), (-.12, -.1, z)], .0035, M['signal'])


def mine(M):
    plinth(M)
    # Quonset utility building
    R, L = .15, .44
    bm = bmesh.new()
    segs = 24
    rings = []
    for x in (-L / 2, L / 2):
        ring = []
        for i in range(segs + 1):
            a = math.pi * i / segs
            ring.append(bm.verts.new((x, math.cos(a) * R, math.sin(a) * R)))
        rings.append(ring)
    for i in range(segs):
        bm.faces.new((rings[0][i], rings[0][i + 1], rings[1][i + 1], rings[1][i]))
    me = bpy.data.meshes.new('quonset')
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(M['body2'])
    q = link(bpy.data.objects.new('quonset', me))
    q.location = (-.2, .12, 0)
    sol = q.modifiers.new('thick', 'SOLIDIFY')
    sol.thickness = .006
    for k in range(9):
        x = -.2 - L / 2 + .02 + k * (L - .04) / 8
        cyl('rib', R + .004, .008, (x, .12, 0), M['body'], rot=(0, math.radians(90), 0), verts=48)
    end = cyl('end wall', R - .002, .01, (-.2 - L / 2, .12, 0), M['body'], rot=(0, math.radians(90), 0), verts=48)
    cut = box('below', (.1, .4, .2), (-.2 - L / 2, .12, -.1), M['body'], bev=0)
    b = end.modifiers.new('cut', 'BOOLEAN')
    b.object = cut
    b.operation = 'DIFFERENCE'
    cut.hide_render = True
    box('door', (.006, .08, .1), (-.2 - L / 2 - .007, .12, .05), M['body2'], bev=.001)
    cyl('status', .011, .006, (-.2 - L / 2 - .008, .06, .1), M['status'], rot=(0, math.radians(90), 0), verts=16)
    # Genset container
    box('genset', (.3, .12, .13), (.22, -.22, .065), M['body'])
    for i in range(6):
        box('louvre', (.03, .004, .08), (.12 + i * .042, -.281, .07), M['trim'], bev=0)
    for dx in (.12, .3):
        cyl('stack', .009, .1, (dx, -.2, .18), M['trim'], verts=12)
    # Tanks and pipe rack
    cyl('tank', .07, .22, (.36, .2, .11), M['tank'], verts=40)
    cyl('tank top', .07, .01, (.36, .2, .225), M['roof'], verts=40, r2=.03)
    for i in range(5):
        x = -.02 + i * .09
        box('support', (.008, .008, .07), (x, .34, .035), M['trim'], bev=0)
    tube('pipe a', [(-.05, .34, .07), (.36, .34, .07), (.36, .27, .07)], .009, M['tank'])
    tube('pipe b', [(-.05, .36, .052), (.42, .36, .052)], .007, M['tank'])
    # Battery skid
    box('battery skid', (.16, .09, .08), (-.36, -.28, .04), M['body2'])
    box('skid base', (.18, .11, .012), (-.36, -.28, .006), M['trim'], bev=.001)
    # Rocks
    for i, (x, y, r) in enumerate(((.5, -.02, .05), (.54, .07, .035), (-.56, .38, .06), (-.48, .42, .04), (.02, -.38, .03))):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)
        for v in bm.verts:
            v.co *= .8 + (hash((i, round(v.co.x, 4), round(v.co.y, 4))) % 40) / 100
            v.co.z *= .6
        me = bpy.data.meshes.new('rock')
        bm.to_mesh(me)
        bm.free()
        me.materials.append(M['rock'])
        ob = link(bpy.data.objects.new('rock', me))
        ob.location = (x, y, r * .3)
    # Signal paths
    z = .006
    tube('signal gen', [(.08, -.22, z), (-.03, -.22, z), (-.03, .0, z), (-.08, .0, z)], .0035, M['signal'])
    tube('signal battery', [(-.36, -.23, z), (-.36, -.05, z)], .0035, M['signal'])
    tube('signal tank', [(.36, .12, z), (.36, .02, z), (.08, .02, z)], .0035, M['signal'])


SCENES = {'cottage': cottage, 'telecom': telecom, 'mine': mine}

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
    build(M)
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
