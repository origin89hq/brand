"""Shared mandibular arch for the bony ridge, gum and lower incisor crowns."""
import math

def arch(theta):
    return (.150*math.sin(theta), -.640-.160*math.cos(theta),
            2.059-.008*math.sin(theta)**2)

def tangent_angle(theta):
    return math.atan2(.160*math.sin(theta),.150*math.cos(theta))

def incisor_mesh(index):
    theta=math.radians(-52+104*index/7)
    root=arch(theta); turn=tangent_angle(theta)
    fraction=abs(theta)/math.radians(52)
    width=.034*(1-.18*fraction); height=.055*(1-.15*fraction); depth=.025
    points=[]; faces=[]; around=32
    sections=[(0,.30,.30),(.18,.40,.39),(.72,.50,.50),(.92,.49,.43),(1,.42,.32)]
    for t,wx,dy in sections:
        for j in range(around):
            a=j*2*math.pi/around; c=math.cos(a); s=math.sin(a)
            x=width*wx*math.copysign(abs(c)**.60,c)
            y=depth*dy*math.copysign(abs(s)**.60,s)-height*t*.12
            points.append((root[0]+x*math.cos(turn)-y*math.sin(turn),
                           root[1]+x*math.sin(turn)+y*math.cos(turn),root[2]+height*t))
    for i in range(len(sections)-1):
        for j in range(around):
            a=i*around+j; b=i*around+(j+1)%around; faces.append((a,b,b+around,a+around))
    faces.extend([tuple(reversed(range(around))),tuple((len(sections)-1)*around+j for j in range(around))])
    return points,faces,theta

def gum_mesh():
    points=[]; faces=[]; rings=65; around=32
    for i in range(rings):
        t=i/(rings-1); theta=math.radians(-65+130*t)
        center=arch(theta); angle=tangent_angle(theta)
        taper=.25+.75*math.sin(math.pi*t)**.22
        for j in range(around):
            a=2*math.pi*j/around; lateral=.023*taper*math.cos(a)
            points.append((center[0]-math.sin(angle)*lateral,
                           center[1]+math.cos(angle)*lateral,
                           center[2]+.002+.020*taper*math.sin(a)))
    for i in range(rings-1):
        for j in range(around):
            a=i*around+j; b=i*around+(j+1)%around; faces.append((a,b,b+around,a+around))
    faces.extend([tuple(reversed(range(around))),tuple((rings-1)*around+j for j in range(around))])
    return points,faces
