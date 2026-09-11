"""Editable cedar construction, carved paddle and integrated native lake surface."""
import math
import random
import bpy
from mathutils import Matrix, Vector
from km43_vest import tailor_vest


def linear(hex):
    values=[int(hex[i:i+2],16)/255 for i in (1,3,5)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values)+(1,)


def craft(scene,props,hull,high,low,plate,heading=0,boat_scale=1,boat_offset=Vector((0,0,0))):
    tailor_vest(props,bpy.data.objects['Buddy | middle seat placement'])
    def mesh(name,vertices,faces,material,uv=None):
        data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
        obj=bpy.data.objects.new(name,data);props.objects.link(obj);data.materials.append(material)
        for p in data.polygons:p.use_smooth=True
        if uv:
            layer=data.uv_layers.new(name='Craft grain')
            for loop in data.loops:layer.data[loop.index].uv=uv[loop.vertex_index]
        return obj

    def wood(name,colors,grain=(3,100,3)):
        mat=bpy.data.materials.new(name);mat.use_nodes=True
        n,l=mat.node_tree.nodes,mat.node_tree.links;bs=n.get('Principled BSDF')
        bs.inputs['Roughness'].default_value=.38;bs.inputs['Coat Weight'].default_value=.19
        bs.inputs['Coat Roughness'].default_value=.23
        bs.inputs['Specular IOR Level'].default_value=.3
        coord=n.new('ShaderNodeTexCoord');mapping=n.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY'
        mapping.inputs[1].default_value=grain;l.new(coord.outputs['UV'],mapping.inputs[0])
        noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=2.5
        noise.inputs['Detail'].default_value=4;noise.inputs['Roughness'].default_value=.7
        l.new(mapping.outputs[0],noise.inputs['Vector'])
        wave=n.new('ShaderNodeTexWave');wave.wave_type='BANDS';wave.bands_direction='Y'
        wave.inputs['Scale'].default_value=4;wave.inputs['Distortion'].default_value=7
        wave.inputs['Detail'].default_value=3;wave.inputs['Detail Scale'].default_value=1.8
        l.new(mapping.outputs[0],wave.inputs['Vector'])
        mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.38
        l.new(noise.outputs['Fac'],mix.inputs[1]);l.new(wave.outputs['Color'],mix.inputs[2])
        ramp=n.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position=.12;ramp.color_ramp.elements[0].color=linear(colors[0])
        ramp.color_ramp.elements[1].position=.8;ramp.color_ramp.elements[1].color=linear(colors[2])
        ramp.color_ramp.elements.new(.43).color=linear(colors[1]);l.new(mix.outputs[0],ramp.inputs[0])
        l.new(ramp.outputs[0],bs.inputs['Base Color'])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.0015
        l.new(mix.outputs[0],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
        return mat

    cedar=wood('Craft | mellow cedar with subtle grain',('#3d2d23','#6e503a','#9a7b5c'),(3,65,3))
    cedar_shader=cedar.node_tree.nodes.get('Principled BSDF')
    cedar_shader.inputs['Roughness'].default_value=.49
    cedar_shader.inputs['Coat Weight'].default_value=.10
    cedar_shader.inputs['Coat Roughness'].default_value=.34
    cedar_shader.inputs['Specular IOR Level'].default_value=.25
    for node in cedar.node_tree.nodes:
        if node.type=='BUMP':
            node.inputs['Strength'].default_value=.12
            node.inputs['Distance'].default_value=.0008
    ash=wood('Craft | oiled ash paddle',('#694017','#b78140','#debc7c'),(2,100,3))
    hull_obj=bpy.data.objects['Canoe | cedar hull'];hull_obj.data.materials.clear();hull_obj.data.materials.append(cedar)
    uv=hull_obj.data.uv_layers.new(name='Longitudinal cedar strips')
    columns=37
    for loop in hull_obj.data.loops:
        i,j=divmod(loop.vertex_index,columns);uv.data[loop.index].uv=(i/100,j/36)
    # Slight tonal differences between adjacent structural strips.
    for index,factor in enumerate((.93,.97,1.02,1.06)):
        variant=cedar.copy();variant.name='Craft | cedar strip tone '+str(index)
        for node in variant.node_tree.nodes:
            if node.type=='VALTORGB':
                for element in node.color_ramp.elements:
                    element.color=tuple(v*factor for v in element.color[:3])+(1,)
        hull_obj.data.materials.append(variant)
    for poly in hull_obj.data.polygons:
        # Each pair of angular cells is one plank, consistently colored end to end.
        strip=(poly.index%36)//2;poly.material_index=(strip*7)%5
    transom=bpy.data.objects['Canoe | flat stern transom'];transom.data.materials.clear();transom.data.materials.append(cedar)
    uv=transom.data.uv_layers.new(name='Transom grain')
    for loop in transom.data.loops:
        p=transom.data.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(p.y+.5,p.z)
    # Wet varnish becomes darker only around the real immersion line.
    for mat in hull_obj.data.materials:
        n,l=mat.node_tree.nodes,mat.node_tree.links;bs=n.get('Principled BSDF')
        color=bs.inputs['Base Color'].links[0].from_socket
        geometry=n.new('ShaderNodeNewGeometry');split=n.new('ShaderNodeSeparateXYZ');l.new(geometry.outputs['Position'],split.inputs[0])
        wet=n.new('ShaderNodeMapRange');wet.inputs['From Min'].default_value=-.03;wet.inputs['From Max'].default_value=.12
        wet.inputs['To Min'].default_value=.46;wet.inputs['To Max'].default_value=1
        l.new(split.outputs['Z'],wet.inputs['Value'])
        scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE';l.new(color,scale.inputs[0]);l.new(wet.outputs[0],scale.inputs['Scale']);l.new(scale.outputs[0],bs.inputs['Base Color'])

    for obj in list(props.objects):
        if obj.name.startswith('Canoe | ash rib'):bpy.data.objects.remove(obj,do_unlink=True)
    for index in range(1,20):
        t=-1+2*index/20;verts=[];uvs=[]
        for j in range(49):
            a=math.pi*j/48
            for dx in (-.019,.019):
                p=Vector(hull(t,a));p.x+=dx;p.y*=.95;p.z+=.025
                verts.append(tuple(p));uvs.append((j/48,0 if dx<0 else 1))
        rib=mesh('Canoe | bent ash rib %02d'%index,verts,[(j*2,j*2+1,j*2+3,j*2+2) for j in range(48)],ash,uvs)
        mod=rib.modifiers.new('Bent rib thickness','SOLIDIFY');mod.thickness=.014
        mod=rib.modifiers.new('Rounded rib edges','BEVEL');mod.width=.004;mod.segments=3

    metal=bpy.data.materials['Canoe | brass fasteners']
    def rail(name,points,radius,mat):
        data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.bevel_depth=radius;data.bevel_resolution=3
        spline=data.splines.new('POLY');spline.points.add(len(points)-1)
        for p,v in zip(spline.points,points):p.co=(*v,1)
        obj=bpy.data.objects.new(name,data);props.objects.link(obj);data.materials.append(mat)
        return obj
    def bead(name,point,radius,mat):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=radius,location=point)
        obj=bpy.context.object;obj.name=name
        for c in list(obj.users_collection):c.objects.unlink(obj)
        props.objects.link(obj);obj.data.materials.append(mat)
        for poly in obj.data.polygons:poly.use_smooth=True
        return obj
    for a in (0,math.pi):
        for i in range(1,40):
            p=Vector(hull(-1+2*i/40,a));p.z-=.032;p.y+=.012 if a==0 else -.012
            bead('Canoe | gunwale fastener',p,.0065,metal)
    protection=bpy.data.materials['Canoe | dark walnut gunwales'].copy();protection.name='Craft | bronze stem protection'
    bs=protection.node_tree.nodes.get('Principled BSDF');bs.inputs['Metallic'].default_value=.65;bs.inputs['Roughness'].default_value=.36
    rail('Canoe | curved bronze bow strip',[hull(.997,math.pi*j/80) for j in range(81)],.025,protection)
    rail('Canoe | bronze transom edging',[hull(-1,math.pi*j/80) for j in range(81)],.017,protection)

    # One continuously tapered oval shaft, broad sculpted blade, and palm grip.
    for name in ('Paddle | ash shaft','Paddle | T grip','Paddle | shaped ottertail blade'):
        bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
    direction=(low-high).normalized()
    normal=Vector((.8,-.3,.45));normal=(normal-direction*normal.dot(direction)).normalized()
    tangent=normal.cross(direction).normalized()
    shaft_start=high-direction*.085
    def section_mesh(name,sections):
        verts=[];uvs=[];count=40
        for s,width,thick in sections:
            spoon=max(0,s-.55)**2*.018
            for j in range(count):
                angle=j/count*math.tau
                p=low+direction*s+tangent*width*math.cos(angle)+normal*(thick*math.sin(angle)+spoon)
                verts.append(tuple(p));uvs.append((s*.6,j/count))
        faces=[(i*count+j,i*count+(j+1)%count,(i+1)*count+(j+1)%count,(i+1)*count+j) for i in range(len(sections)-1) for j in range(count)]
        faces += [tuple(range(count-1,-1,-1)),tuple((len(sections)-1)*count+j for j in range(count))]
        obj=mesh(name,verts,faces,ash,uvs)
        sub=obj.modifiers.new('Carved smooth surface','SUBSURF');sub.levels=2;sub.render_levels=2
        return obj,verts
    length=(high-low).length
    section_mesh('Paddle | carved oval shaft',[(-length-.09,.022,.018),(-length-.08,.024,.019),(-length,.025,.019),(-length+.15,.022,.017),(-.1,.022,.017),(.35,.025,.019),(.54,.03,.019),(.57,.031,.018)])
    blade,blade_vertices=section_mesh('Paddle | shaped ottertail blade',[(.48,.027,.019),(.54,.035,.018),(.68,.09,.015),(.83,.145,.012),(1.06,.172,.010),(1.30,.172,.009),(1.49,.145,.008),(1.61,.095,.006),(1.68,.032,.004),(1.70,.003,.002)])
    grip=bead('Paddle | shaped palm grip',shaft_start,.075,ash)
    grip.scale=(1,.45,.62);grip.rotation_euler=direction.to_track_quat('Z','Y').to_euler()
    # Actual UVs on the grip make its grain follow the same carved material.
    # Native water replaces the transparent shadow catcher, occluding immersion.
    old_water=bpy.data.objects['Lake | editable reflection surface'];old_water.hide_render=True
    water=bpy.data.materials.new('Lake | projected color with native reflection');water.use_nodes=True
    n,l=water.node_tree.nodes,water.node_tree.links;n.clear()
    output=n.new('ShaderNodeOutputMaterial');coord=n.new('ShaderNodeTexCoord')
    tex=n.new('ShaderNodeTexImage');tex.image=plate;tex.extension='EXTEND';l.new(coord.outputs['Window'],tex.inputs[0])
    occlusion=n.new('ShaderNodeAmbientOcclusion');occlusion.inputs['Distance'].default_value=.3
    l.new(tex.outputs['Color'],occlusion.inputs['Color'])
    emission=n.new('ShaderNodeEmission');l.new(occlusion.outputs['Color'],emission.inputs['Color'])
    glossy=n.new('ShaderNodeBsdfGlossy');glossy.inputs['Color'].default_value=(.65,.70,.70,1);glossy.inputs['Roughness'].default_value=.065
    fresnel=n.new('ShaderNodeFresnel');fresnel.inputs['IOR'].default_value=1.333
    reflection=n.new('ShaderNodeMath');reflection.operation='MULTIPLY';reflection.inputs[1].default_value=1.5;reflection.use_clamp=True;l.new(fresnel.outputs[0],reflection.inputs[0])
    mix=n.new('ShaderNodeMixShader');l.new(reflection.outputs[0],mix.inputs[0]);l.new(emission.outputs[0],mix.inputs[1]);l.new(glossy.outputs[0],mix.inputs[2])
    # Smooth, localized coverage; the central surface is fully opaque water.
    split=n.new('ShaderNodeSeparateXYZ');l.new(coord.outputs['Object'],split.inputs[0])
    far=n.new('ShaderNodeMath');far.operation='MAXIMUM';far.inputs[1].default_value=0;l.new(split.outputs['Y'],far.inputs[0])
    vector=n.new('ShaderNodeCombineXYZ');l.new(split.outputs['X'],vector.inputs['X']);l.new(far.outputs[0],vector.inputs['Y'])
    objcoord=n.new('ShaderNodeVectorMath');objcoord.operation='MULTIPLY';objcoord.inputs[1].default_value=(1/5,1/3.8,0)
    l.new(vector.outputs[0],objcoord.inputs[0]);radius=n.new('ShaderNodeVectorMath');radius.operation='LENGTH';l.new(objcoord.outputs[0],radius.inputs[0])
    fade=n.new('ShaderNodeMapRange');fade.interpolation_type='SMOOTHERSTEP';fade.inputs['From Min'].default_value=.68;fade.inputs['From Max'].default_value=1
    fade.inputs['To Min'].default_value=1;fade.inputs['To Max'].default_value=0;l.new(radius.outputs['Value'],fade.inputs['Value'])
    # Keep the foreground bank dry: only the open water receives 3D reflections.
    screen=n.new('ShaderNodeSeparateXYZ');l.new(coord.outputs['Window'],screen.inputs[0])
    bank=n.new('ShaderNodeMapRange');bank.inputs['From Min'].default_value=.40;bank.inputs['From Max'].default_value=.64
    bank.inputs['To Min'].default_value=.34;bank.inputs['To Max'].default_value=.075;l.new(screen.outputs['X'],bank.inputs['Value'])
    right_bank=n.new('ShaderNodeMapRange');right_bank.inputs['From Min'].default_value=.70;right_bank.inputs['From Max'].default_value=.91
    right_bank.inputs['To Min'].default_value=.075;right_bank.inputs['To Max'].default_value=.30;l.new(screen.outputs['X'],right_bank.inputs['Value'])
    banks=n.new('ShaderNodeMath');banks.operation='MAXIMUM';l.new(bank.outputs[0],banks.inputs[0]);l.new(right_bank.outputs[0],banks.inputs[1])
    above=n.new('ShaderNodeMath');above.operation='SUBTRACT';l.new(screen.outputs['Y'],above.inputs[0]);l.new(banks.outputs[0],above.inputs[1])
    bank_fade=n.new('ShaderNodeMapRange');bank_fade.interpolation_type='SMOOTHERSTEP';bank_fade.inputs['From Min'].default_value=0;bank_fade.inputs['From Max'].default_value=.055
    l.new(above.outputs[0],bank_fade.inputs['Value'])
    coverage=n.new('ShaderNodeMath');coverage.operation='MULTIPLY';l.new(fade.outputs[0],coverage.inputs[0]);l.new(bank_fade.outputs[0],coverage.inputs[1])
    transparent=n.new('ShaderNodeBsdfTransparent');alpha=n.new('ShaderNodeMixShader');l.new(coverage.outputs[0],alpha.inputs[0]);l.new(transparent.outputs[0],alpha.inputs[1]);l.new(mix.outputs[0],alpha.inputs[2]);l.new(alpha.outputs[0],output.inputs[0])
    # Intersect the same paddle axis with the water for correctly centered rings.
    rotation=Matrix.Rotation(heading,3,'Z')
    contact=boat_offset+boat_scale*(rotation@(low+direction*(-low.z/direction.z)))
    verts=[];nx,ny=220,300
    for j in range(ny+1):
        y=-12+16.2*j/ny
        for i in range(nx+1):
            x=-5.2+10.4*i/nx
            local=(rotation.transposed()@(Vector((x,y,0))-boat_offset))/boat_scale
            r=math.sqrt((local.x/2.4)**2+(local.y/.65)**2)
            wake=.004*math.sin((r-1)*31)*math.exp(-((r-1.12)/.8)**2) if r>1 else 0
            d=math.hypot(x-contact.x,y-contact.y)
            ripple=.009*math.sin(d*28)*math.exp(-d*2.2)
            z=.0015*math.sin(x*6+y*2)*math.sin(y*9)+wake+ripple
            verts.append((x,y,z))
    faces=[(j*(nx+1)+i,j*(nx+1)+i+1,(j+1)*(nx+1)+i+1,(j+1)*(nx+1)+i) for j in range(ny) for i in range(nx)]
    surface=mesh('Lake | physical water and paddle ripples',verts,faces,water)
    # Small edge menisci at the immersed hull's actual section intersections.
    for sign in (-1,1):
        line=[]
        for i in range(151):
            t=-.998+1.996*i/150
            top=hull(t,0)[2];bottom=hull(t,math.pi/2)[2]
            if bottom>=0:continue
            a=math.asin((top/(top-bottom))**1.25)
            p=Vector(hull(t,a if sign>0 else math.pi-a));p.y+=sign*.012;p.z=.006
            line.append(p)
        rail('Lake | hull meniscus',line,.006,water)
    # Lighting matches the soft forest plate, with restrained varnish highlights.
    for obj in scene.objects:
        if obj.type=='LIGHT':obj.data.specular_factor=.25
    return shaft_start,low+direction*.57,blade_vertices,contact
