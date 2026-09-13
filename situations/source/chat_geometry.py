"""Native chat props and the existing SVG wordmark for Buddy's social scene."""

import math
import re
from xml.etree import ElementTree

import bpy
from mathutils import Matrix, Vector


def rounded(width, height, radius, steps=12):
    points = []
    for x, y, start in ((width/2-radius, -height/2+radius, -math.pi/2),
                        (width/2-radius, height/2-radius, 0),
                        (-width/2+radius, height/2-radius, math.pi/2),
                        (-width/2+radius, -height/2+radius, math.pi)):
        points.extend((x+radius*math.cos(start+i*math.pi/2/steps),
                       y+radius*math.sin(start+i*math.pi/2/steps)) for i in range(steps+1))
    return points


def shape(collection, name, contours, material, location, depth=0, bevel=0):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '2D'
    curve.resolution_u = 24
    curve.fill_mode = 'BOTH'
    curve.extrude = depth
    curve.bevel_depth = bevel
    curve.bevel_resolution = 5
    for points in contours:
        spline = curve.splines.new('POLY')
        spline.points.add(len(points)-1)
        for point, (x, y) in zip(spline.points, points):
            point.co = (x, y, 0, 1)
        spline.use_cyclic_u = True
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler.x = math.pi/2
    curve.materials.append(material)
    return obj


def svg_contours(data):
    """Read the absolute commands emitted by identity/source/build_vectors.py."""
    unsupported = set(re.findall(r'[A-DF-Za-df-z]', data))-set('MLHVCZ')
    if unsupported:
        raise ValueError(f'Unsupported command in the original logo: {unsupported}')
    tokens = re.findall(r'[MLHVCZ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?', data)
    contours, points = [], []
    cursor = Vector((0, 0))
    index, command = 0, None
    while index < len(tokens):
        if tokens[index] in 'MLHVCZ':
            command = tokens[index]
            index += 1
        if command == 'Z':
            if points:
                contours.append(points)
                cursor = Vector(points[0])
                points = []
            command = None
            continue
        count = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'C': 6}[command]
        values = list(map(float, tokens[index:index+count]))
        index += count
        if command == 'C':
            a, b, c = Vector(values[:2]), Vector(values[2:4]), Vector(values[4:])
            start = cursor.copy()
            for step in range(1, 9):
                t = step/8
                points.append(tuple((1-t)**3*start+3*(1-t)**2*t*a+3*(1-t)*t*t*b+t**3*c))
            cursor = c
        else:
            if command == 'M' and points:
                contours.append(points)
                points = []
            cursor = Vector((values[0], cursor.y)) if command == 'H' else (
                Vector((cursor.x, values[0])) if command == 'V' else Vector(values))
            points.append(tuple(cursor))
            if command == 'M':
                command = 'L'
    if points:
        contours.append(points)
    return contours


def logo(collection, path, materials, location, width):
    document = ElementTree.parse(path).getroot()
    viewbox = list(map(float, document.attrib['viewBox'].split()))
    scale = width/viewbox[2]
    control = bpy.data.objects.new('Brand | original Origin89 vector logo', None)
    collection.objects.link(control)
    control.location = location
    control.empty_display_size = .12

    def visit(element, transform):
        local = Matrix.Identity(3)
        for kind, raw in re.findall(r'(translate|scale)\(([^)]+)\)', element.get('transform', '')):
            values = list(map(float, re.split(r'[ ,]+', raw)))
            if kind == 'translate':
                matrix = Matrix(((1, 0, values[0]), (0, 1, values[1] if len(values)>1 else 0), (0, 0, 1)))
            else:
                matrix = Matrix(((values[0], 0, 0), (0, values[-1], 0), (0, 0, 1)))
            local = local @ matrix
        transform = transform @ local
        if element.tag.endswith('path'):
            contours = []
            for contour in svg_contours(element.attrib['d']):
                mapped = [transform @ Vector((x, y, 1)) for x, y in contour]
                contours.append([(p.x*scale, -p.y*scale) for p in mapped])
            obj = shape(collection, 'Brand | outlined logo path', contours,
                        materials[element.attrib['fill']], (0, 0, 0))
            obj.parent = control
            obj.location.y = -.0001*len(control.children)
        for child in element:
            visit(child, transform)
    visit(document, Matrix.Identity(3))
    return control
