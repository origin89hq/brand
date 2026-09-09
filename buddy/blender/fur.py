"""Native hair material and triangulated surface attachment shared by Buddy.
The character builder owns the groom and its regional length masks.
"""
import math,bmesh,bpy
from array import array
UV_NAME="Buddy fur attachment"

def linear(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4

def hair_material(name,color,roughness):
    material=bpy.data.materials.get(name) or bpy.data.materials.new(name);material.use_nodes=True
    nodes=material.node_tree.nodes;nodes.clear();links=material.node_tree.links
    output=nodes.new('ShaderNodeOutputMaterial');output.location=(700,0)
    hair=nodes.new('ShaderNodeBsdfHairPrincipled');hair.location=(470,0);hair.parametrization='COLOR'
    rgb=[linear(int(color[i:i+2],16)/255) for i in (1,3,5)]
    hair.inputs['Roughness'].default_value=roughness;hair.inputs['Radial Roughness'].default_value=.48
    hair.inputs['Coat'].default_value=.10;hair.inputs['Random Roughness'].default_value=.10
    info=nodes.new('ShaderNodeHairInfo');info.location=(-660,60)
    random=nodes.new('ShaderNodeValToRGB');random.name='Fur | individual strand variation';random.location=(-420,170)
    random.color_ramp.elements[0].color=(*(v*.83 for v in rgb),1)
    random.color_ramp.elements[1].color=(*(min(1,v*1.19) for v in rgb),1)
    links.new(info.outputs['Random'],random.inputs['Fac'])
    gradient=nodes.new('ShaderNodeValToRGB');gradient.name='Fur | dark root to luminous tip';gradient.location=(-420,-60)
    gradient.color_ramp.elements[0].position=0;gradient.color_ramp.elements[0].color=(.45,.48,.54,1)
    mid=gradient.color_ramp.elements.new(.55);mid.color=(.83,.89,.99,1)
    gradient.color_ramp.elements[-1].position=1;gradient.color_ramp.elements[-1].color=(1.13,1.17,1.23,1)
    if 'ivory' in name:
        gradient.color_ramp.elements[0].color=(.64,.51,.35,1)
        mid.color=(.94,.86,.72,1)
        gradient.color_ramp.elements[-1].color=(1.10,1.07,1.0,1)
    links.new(info.outputs['Intercept'],gradient.inputs['Fac'])
    mix=nodes.new('ShaderNodeMixRGB');mix.name='Fur | strand and root color blend';mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
    links.new(random.outputs['Color'],mix.inputs[1]);links.new(gradient.outputs['Color'],mix.inputs[2])
    # Slow coherent variation joins adjacent strands into visibly shaded locks.
    coord=nodes.new('ShaderNodeTexCoord');noise=nodes.new('ShaderNodeTexNoise');noise.name='Fur | soft color patches';noise.inputs['Scale'].default_value=14;noise.inputs['Detail'].default_value=2
    links.new(coord.outputs['Object'],noise.inputs['Vector'])
    patches=nodes.new('ShaderNodeMapRange');patches.inputs['To Min'].default_value=.76;patches.inputs['To Max'].default_value=1.12
    links.new(noise.outputs['Fac'],patches.inputs['Value'])
    final=nodes.new('ShaderNodeMixRGB');final.blend_type='MULTIPLY';final.inputs[0].default_value=1
    links.new(mix.outputs[0],final.inputs[1]);links.new(patches.outputs[0],final.inputs[2]);links.new(final.outputs[0],hair.inputs['Color'])
    pigment=nodes.new('ShaderNodeBsdfDiffuse');pigment.name='Fur | soft pigmented fiber';pigment.inputs['Roughness'].default_value=.45
    links.new(final.outputs[0],pigment.inputs['Color'])
    blend=nodes.new('ShaderNodeMixShader');blend.name='Fur | controlled fiber sheen';blend.inputs[0].default_value=.60
    links.new(hair.outputs[0],blend.inputs[1]);links.new(pigment.outputs[0],blend.inputs[2]);links.new(blend.outputs[0],output.inputs['Surface'])
    material.diffuse_color=(*rgb,1)
    return material

def attachment_atlas(surface):
    mesh=surface.data
    # Triangulate the attachment skin so native UV evaluation cannot choose
    # the opposite diagonal of a non-planar quad after a pose deformation.
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
    mesh.calc_loop_triangles();grid=math.ceil(math.sqrt(len(mesh.polygons)))
    uv=mesh.uv_layers.get(UV_NAME) or mesh.uv_layers.new(name=UV_NAME)
    values=array('f',[0.0])*(len(mesh.loops)*2)
    for poly in mesh.polygons:
        x,y=poly.index%grid,poly.index//grid
        for j,loop in enumerate(poly.loop_indices):
            angle=2*math.pi*j/poly.loop_total+math.pi/4
            values[loop*2]=(x+.5+.39*math.cos(angle))/grid
            values[loop*2+1]=(y+.5+.39*math.sin(angle))/grid
    uv.data.foreach_set('uv',values);surface.add_rest_position_attribute=True
    return values
