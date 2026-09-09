"""Editable muzzle grain anchored to the undeformed skin coordinates."""
import numpy as np


def face_warmth(points):
    """Soft chestnut markings in the shared, undeformed head coordinates."""
    p = np.asarray(points)
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    forehead = .72 * np.exp(-(x / .25)**2 - ((z - 2.73) / .20)**2
                             - ((y + .21) / .28)**2)
    bridge = .42 * np.exp(-(x / .12)**2 - ((y + .49) / .25)**2
                           - ((z - 2.47) / .22)**2)
    cheeks = .50 * np.exp(-((np.abs(x) - .30) / .12)**2
                           - ((z - 2.40) / .22)**2 - ((y + .20) / .22)**2)
    weight = 1 - (1 - forehead) * (1 - bridge) * (1 - cheeks)
    # Leave the terminal nose dark and keep the markings above the jaw seam.
    fade = np.clip((y + .90) / .25, 0, 1) * np.clip((z - 2.22) / .16, 0, 1)
    fade = fade * fade * (3 - 2 * fade)
    grain = .90 + .06 * np.sin(x * 17 + z * 7) * np.cos(y * 13 - z * 5)
    grain += .04 * np.sin(x * 31 - y * 11)
    return weight * fade * grain


def install_muzzle_detail(head, nostril_material):
    mesh = head.data
    rest = mesh.attributes.new('muzzle_rest', 'FLOAT_VECTOR', 'POINT')
    mask = mesh.attributes.new('muzzle_detail', 'FLOAT', 'POINT')
    positions = np.array([head.matrix_world @ v.co for v in mesh.vertices])
    weight = np.clip((-positions[:, 1] - .56) / .35, 0, 1)
    weight = weight * weight * (3 - 2 * weight)
    rest.data.foreach_set('vector', positions.reshape(-1))
    mask.data.foreach_set('value', weight)
    material = mesh.materials[0].copy()
    material.name = 'Muzzle | fine pores and uneven soft coat'
    mesh.materials[0] = material

    for mat, interior in [(material, False), (nostril_material, True)]:
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        shader = nodes['Principled BSDF']
        position = nodes.new('ShaderNodeAttribute')
        position.attribute_name = 'muzzle_rest'
        position.label = 'Rest coordinates follow the facial skin'
        coverage = nodes.new('ShaderNodeAttribute')
        coverage.attribute_name = 'muzzle_detail'
        mottle = nodes.new('ShaderNodeTexNoise')
        mottle.name = 'Muzzle | soft tonal variation'
        mottle.inputs['Scale'].default_value = 24
        mottle.inputs['Detail'].default_value = 3
        mottle.inputs['Roughness'].default_value = .7
        links.new(position.outputs['Vector'], mottle.inputs['Vector'])
        tone = nodes.new('ShaderNodeMapRange')
        tone.inputs['To Min'].default_value = .72 if interior else .80
        tone.inputs['To Max'].default_value = 1.17
        links.new(mottle.outputs['Fac'], tone.inputs['Value'])
        color = nodes.new('ShaderNodeMixRGB')
        color.blend_type = 'MULTIPLY'
        if interior:
            color.inputs[0].default_value = 1
        else:
            links.new(coverage.outputs['Fac'], color.inputs[0])
        if shader.inputs['Base Color'].is_linked:
            links.new(shader.inputs['Base Color'].links[0].from_socket, color.inputs[1])
        else:
            color.inputs[1].default_value = shader.inputs['Base Color'].default_value
        links.new(tone.outputs[0], color.inputs[2])
        links.new(color.outputs[0], shader.inputs['Base Color'])

        pores = nodes.new('ShaderNodeTexVoronoi')
        pores.name = 'Muzzle | irregular fine pores'
        pores.inputs['Scale'].default_value = 360
        pores.inputs['Randomness'].default_value = 1
        links.new(position.outputs['Vector'], pores.inputs['Vector'])
        relief = nodes.new('ShaderNodeValToRGB')
        relief.color_ramp.elements[0].position = .08
        relief.color_ramp.elements[0].color = (0, 0, 0, 1)
        relief.color_ramp.elements[1].position = .45
        relief.color_ramp.elements[1].color = (1, 1, 1, 1)
        relief.color_ramp.interpolation = 'EASE'
        links.new(pores.outputs['Distance'], relief.inputs[0])
        bump = nodes.new('ShaderNodeBump')
        bump.name = 'Muzzle | shallow pore relief'
        bump.inputs['Distance'].default_value = .0012
        strength = nodes.new('ShaderNodeMath')
        strength.operation = 'MULTIPLY'
        strength.inputs[1].default_value = .38
        if interior:
            strength.inputs[0].default_value = 1
        else:
            links.new(coverage.outputs['Fac'], strength.inputs[0])
        links.new(strength.outputs[0], bump.inputs['Strength'])
        links.new(relief.outputs[0], bump.inputs['Height'])
        if shader.inputs['Normal'].is_linked:
            links.new(shader.inputs['Normal'].links[0].from_socket, bump.inputs['Normal'])
        links.new(bump.outputs[0], shader.inputs['Normal'])
        rough = nodes.new('ShaderNodeMapRange')
        rough.name = 'Muzzle | varied surface roughness'
        rough.inputs['To Min'].default_value = .46 if interior else .57
        rough.inputs['To Max'].default_value = .70 if interior else .80
        links.new(mottle.outputs['Fac'], rough.inputs['Value'])
        blend = nodes.new('ShaderNodeMixRGB')
        blend.inputs[1].default_value = (.72, .72, .72, 1)
        if interior:
            blend.inputs[0].default_value = 1
        else:
            links.new(coverage.outputs['Fac'], blend.inputs[0])
        links.new(rough.outputs[0], blend.inputs[2])
        links.new(blend.outputs[0], shader.inputs['Roughness'])
