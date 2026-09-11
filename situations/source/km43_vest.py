"""Fitted fabric life jacket for Buddy's seated canoe pose."""
import math
import bpy
from mathutils import Vector


def tailor_vest(collection,placement):
    for obj in list(collection.objects):
        if obj.name.startswith('Vest |'):bpy.data.objects.remove(obj,do_unlink=True)
    blue=bpy.data.materials['Vest | Origin89 bridge blue']
    navy=bpy.data.materials['Vest | binding and webbing']
    buckle=bpy.data.materials['Vest | charcoal buckles']
    shader=blue.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value=.88
    shader.inputs['Specular IOR Level'].default_value=.25
    shader.inputs['Sheen Weight'].default_value=.24
    shader.inputs['Sheen Roughness'].default_value=.8

    def mesh(name,verts,faces,material,thickness=0):
        data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
        obj=bpy.data.objects.new(name,data);collection.objects.link(obj);obj.parent=placement;data.materials.append(material)
        for p in data.polygons:p.use_smooth=True
        if thickness:
            mod=obj.modifiers.new('Fabric and foam thickness','SOLIDIFY');mod.thickness=thickness
            mod=obj.modifiers.new('Soft sewn edge','BEVEL');mod.width=.008;mod.segments=3
        return obj

    def rail(name,points,radius,material):
        data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.bevel_depth=radius;data.bevel_resolution=3
        spline=data.splines.new('POLY');spline.points.add(len(points)-1)
        for point,value in zip(spline.points,points):point.co=(*value,1)
        obj=bpy.data.objects.new(name,data);collection.objects.link(obj);obj.parent=placement;data.materials.append(material)
        return obj

    def rounded_pattern(points):
        result=[]
        for i in range(len(points)):
            p0,p1,p2,p3=[Vector(points[(i+j)%len(points)]) for j in (-1,0,1,2)]
            for step in range(8):
                t=step/8
                result.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
        return result

    pattern=[(.045,.49),(.37,.50),(.455,.65),(.455,.83),(.39,.98),(.29,1.15),(.19,1.16),(.10,1.03),(.045,.88)]
    for sign in (-1,1):
        boundary=rounded_pattern(pattern);center=Vector((.225,.81));verts=[];rim=[];stitches=[]
        rings=12;count=len(boundary)
        for j in range(rings+1):
            r=max(.003,j/rings)
            for p in boundary:
                x,z=center+(p-center)*r;x*=sign
                chest_depth=.45*(1-.16*max(0,(z-.7)/.5))
                y=.025-chest_depth*math.sqrt(max(.15,1-(x/.53)**2))-.040-.035*(1-r*r)
                verts.append((x,y,z))
                if j==rings:rim.append((x,y-.007,z))
                if j==rings-1:stitches.append((x,y-.003,z))
        faces=[(j*count+i,j*count+(i+1)%count,(j+1)*count+(i+1)%count,(j+1)*count+i) for j in range(rings) for i in range(count)]
        faces.append(tuple(range(count-1,-1,-1)))
        panel=mesh('Vest | curved padded front '+str(sign),verts,faces,blue,.035)
        sub=panel.modifiers.new('Supple padded fabric','SUBSURF');sub.levels=1;sub.render_levels=1
        rail('Vest | sewn panel binding',rim+[rim[0]],.006,navy)
        rail('Vest | inset stitching',stitches+[stitches[0]],.0015,navy)
        # Wide cloth shoulder bridge; a real opening remains around each arm.
        points=[Vector((sign*.275,-.30,1.115)),Vector((sign*.28,-.08,1.255)),Vector((sign*.28,.16,1.255)),Vector((sign*.28,.37,1.105))]
        verts=[]
        for p in points:
            verts += [tuple(p+Vector((-.06,0,0))),tuple(p+Vector((.06,0,0)))]
        bridge=mesh('Vest | fabric shoulder bridge',verts,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(3)],blue,.035)
        sub=bridge.modifiers.new('Curved shoulder seam','SUBSURF');sub.levels=2;sub.render_levels=2
        # Lower side fabric joins front and back beneath the arm opening.
        verts=[]
        for j in range(17):
            a=-.65+2.0*j/16
            for z in (.50,.83):verts.append((sign*.49*math.cos(a),.035+.43*math.sin(a),z))
        mesh('Vest | shaped side panel',verts,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(16)],blue,.027)
    back_pattern=rounded_pattern([(-.29,.52),(.29,.52),(.35,.8),(.29,1.1),(.16,1.14),(-.16,1.14),(-.29,1.1),(-.35,.8)])
    verts=[(p.x,.37+.09*(1-(p.x/.45)**2),p.y) for p in back_pattern]
    mesh('Vest | curved back panel',verts,[tuple(range(len(verts)))],blue,.045)

    # Flat woven straps follow the vest, with small open-frame side-release buckles.
    for z in (.69,.91):
        verts=[]
        for i in range(97):
            a=math.tau*i/96
            x=.512*math.sin(a);y=.035-.515*math.cos(a)
            for dz in (-.019,.019):verts.append((x,y,z+dz))
        mesh('Vest | fitted woven strap',verts,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(96)],navy,.003)
        y=-.49
        border=[(-.046,y,z-.025),(.046,y,z-.025),(.046,y,z+.025),(-.046,y,z+.025),(-.046,y,z-.025)]
        rail('Vest | buckle frame',border,.007,buckle)
        rail('Vest | buckle bridge',[(0,y-.003,z-.025),(0,y-.003,z+.025)],.005,buckle)
    rail('Vest | front zipper tape',[(0,-.478,.53),(0,-.47,.76),(0,-.425,.99)],.009,navy)
