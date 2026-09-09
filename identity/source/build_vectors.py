"""Build the Plate 89 master geometry and outlined SVGs. Requires fontTools.

The custom plate and numerals below are the single source for SVG and Blender.
Coordinates are a 200 x 110 unit plate. Fonts remain editable upstream; delivery
SVGs contain paths only, so recipients do not need fonts installed.
"""
from pathlib import Path
import json
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.recordingPen import RecordingPen, DecomposingRecordingPen
from fontTools.pens.qu2cuPen import Qu2CuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen

ROOT = Path(__file__).resolve().parents[1]
BLUE, INK, WHITE = '#2b4a97', '#07090c', '#e7eaee'

def rr(x,y,w,h,r):
    k=.5522847498
    return [('moveTo',[(x+r,y)]),('lineTo',[(x+w-r,y)]),
        ('curveTo',[(x+w-r+k*r,y),(x+w,y+r-k*r),(x+w,y+r)]),('lineTo',[(x+w,y+h-r)]),
        ('curveTo',[(x+w,y+h-r+k*r),(x+w-r+k*r,y+h),(x+w-r,y+h)]),('lineTo',[(x+r,y+h)]),
        ('curveTo',[(x+r-k*r,y+h),(x,y+h-r+k*r),(x,y+h-r)]),('lineTo',[(x,y+r)]),
        ('curveTo',[(x,y+r-k*r),(x+r-k*r,y),(x+r,y)]),('closePath',[])]

def parse(s):
    # Intentionally small grammar: all coordinates absolute; M, L, C and Z only.
    import re
    t=re.findall(r'[MLCZ]|-?\d+(?:\.\d+)?',s); out=[]; i=0
    while i<len(t):
        op=t[i]; i+=1; n={'M':2,'L':2,'C':6,'Z':0}[op]
        vals=list(map(float,t[i:i+n])); i+=n
        out.append(({'M':'moveTo','L':'lineTo','C':'curveTo','Z':'closePath'}[op],list(zip(vals[::2],vals[1::2]))))
    return out

plate=parse('M 14 0 L 186 0 L 200 14 L 200 96 L 186 110 L 14 110 L 0 96 L 0 14 Z')
eight=parse('M 37 17 L 70 17 C 85 17 92 24 92 37 L 92 42 C 92 48 89 52 84 55 C 90 58 93 63 93 71 L 93 77 C 93 88 86 93 72 93 L 36 93 C 22 93 16 87 16 77 L 16 71 C 16 63 19 58 25 55 C 19 51 16 47 16 40 L 16 37 C 16 24 23 17 37 17 Z')
eight += rr(30,31,48,16,6)+rr(30,63,49,16,6)
nine=parse('M 132 17 L 157 17 C 174 17 182 25 182 42 L 182 68 C 182 85 173 93 155 93 L 132 93 C 115 93 106 86 106 73 L 121 73 C 122 78 127 79 133 79 L 155 79 C 164 79 168 75 168 66 L 168 61 C 163 65 158 66 151 66 L 132 66 C 115 66 106 58 106 42 C 106 25 114 17 132 17 Z')
nine += rr(120,31,48,21,7)

def svgpath(cmds):
    pen=SVGPathPen(None)
    for op,pts in cmds: getattr(pen,op)(*pts)
    return pen.getCommands()

def word(text,fontname,size):
    font=TTFont(ROOT/'fonts'/fontname); gs=font.getGlyphSet(); cmap=font.getBestCmap(); upm=font['head'].unitsPerEm
    rec=RecordingPen(); x=0
    for ch in text:
        g=gs[cmap[ord(ch)]]
        decomp=DecomposingRecordingPen(gs); g.draw(decomp)
        decomp.replay(Qu2CuPen(TransformPen(rec,(size/upm,0,0,-size/upm,x,0)),max_err=.05,all_cubic=True))
        x+=g.width*size/upm+(1.5 if text=='Origin89' else 0)
    bounds=BoundsPen(None); rec.replay(bounds); x0,y0,x1,y1=bounds.bounds
    shifted=RecordingPen(); rec.replay(TransformPen(shifted,(1,0,0,1,-x0,-y0)))
    commands=shifted.value
    if text=='Origin89':
        # Optical weight adjustment, frozen as actual outlines (not live strokes).
        # Retains Michroma's extended forms while approaching the chosen concept.
        from shapely.geometry import Polygon, GeometryCollection
        solid=GeometryCollection(); ring=[]; current=None
        for op,points in commands:
            if op=='moveTo': ring=[points[0]]; current=points[0]
            elif op=='lineTo': ring.append(points[0]); current=points[0]
            elif op=='curveTo':
                a=current;b,c,d=points
                for i in range(1,13):
                    t=i/12;q=1-t
                    ring.append(tuple(q**3*a[j]+3*q*q*t*b[j]+3*q*t*t*c[j]+t**3*d[j] for j in (0,1)))
                current=d
            elif op=='closePath': solid=solid.symmetric_difference(Polygon(ring))
        solid=solid.buffer(1.1,resolution=8,join_style=1)
        lx,ly,rx,ry=solid.bounds; commands=[]
        for poly in solid.geoms if hasattr(solid,'geoms') else [solid]:
            for r in [poly.exterior,*poly.interiors]:
                pts=[(px-lx,py-ly) for px,py in list(r.coords)[:-1]]
                commands += [('moveTo',[pts[0]])]+[('lineTo',[pt]) for pt in pts[1:]]+[('closePath',[])]
        return {'commands':commands,'width':rx-lx,'height':ry-ly,'optical_expansion':1.1,'tracking':1.5}
    return {'commands':commands,'width':x1-x0,'height':y1-y0}

def path(cmds,color): return f'<path fill="{color}" fill-rule="evenodd" d="{svgpath(cmds)}"/>'
def mark(bg,fg): return path(plate,bg)+path(eight+nine,fg)
def svg(name,w,h,body):
    (ROOT/'logos'/name).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.4f} {h:.4f}" role="img"><title>Origin89 - Plate 89</title>{body}</svg>\n')

def main():
    for weight in (400,600,700):
        f=instantiateVariableFont(TTFont(ROOT/'fonts/InterTight-Variable.ttf'),{'wght':weight},inplace=False)
        style={400:'Regular',600:'SemiBold',700:'Bold'}[weight]
        for record in f['name'].names:
            names={1:'Inter Tight',2:style,3:'InterTight-'+style+'-O89-static',4:'Inter Tight '+style,6:'InterTight-'+style,16:'Inter Tight',17:style}
            if record.nameID in names:record.string=names[record.nameID].encode(record.getEncoding())
        f.save(ROOT/f'fonts/InterTight-{weight}.ttf')
    words={s:word(s,'Michroma-Regular.ttf',72 if s=='Origin89' else 30) for s in ['Origin89']}
    for s in ['Controller','Offgrid','Buddy']:
        words[s]=word(s,'InterTight-600.ttf',35)
    geometry={'version':'1.0','plate':plate,'eight':eight,'nine':nine,'words':words,
        'dimensions':{'plate_width':200,'plate_height':110,'chamfer':14,'clear_space':27.5},
        'source_reference':'01-plate-89.png; redrawn as native vector geometry, not a pixel trace'}
    (ROOT/'source/geometry.json').write_text(json.dumps(geometry,indent=2)+'\n')
    mainword=words['Origin89']; ww=mainword['width']; wh=mainword['height']
    for variant,bg,fg,text in [('blue',BLUE,WHITE,INK),('black',INK,'#ffffff',INK),('white','#ffffff',INK,'#ffffff')]:
        svg(f'plate-89-{variant}.svg',200,110,mark(bg,fg))
        svg(f'wordmark-{variant}.svg',ww,wh,path(mainword['commands'],text))
        scale=1.05; tx=200+44; ty=(110-wh*scale)/2
        body=mark(bg,fg)+f'<g transform="translate({tx} {ty}) scale({scale})">{path(mainword["commands"],text)}</g>'
        svg(f'origin89-horizontal-{variant}.svg',tx+ww*scale,110,body)
        sw=ww; mx=(sw-260)/2
        body=f'<g transform="translate({mx} 0) scale(1.3)">{mark(bg,fg)}</g><g transform="translate(0 169)">{path(mainword["commands"],text)}</g>'
        svg(f'origin89-stacked-{variant}.svg',sw,169+wh,body)
        for name in ('Controller','Offgrid','Buddy'):
            wd=words[name]
            body=mark(bg,fg)+f'<g transform="translate(244 6)">{path(mainword["commands"],text)}</g><g transform="translate(244 79)">{path(wd["commands"],text)}</g>'
            svg(f'origin89-{name.lower()}-{variant}.svg',244+ww,110,body)
    # A stencil-style knockout with true transparent numerals, for one-ink plates.
    svg('plate-89-knockout-black.svg',200,110,path(plate+eight+nine,INK))
    svg('plate-89-knockout-white.svg',200,110,path(plate+eight+nine,'#ffffff'))
    # Default flat unmasked app source. Platform masks are applied by the platform.
    (ROOT/'icons/offgrid-flat-master.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024"><title>Origin89 Offgrid</title><path fill="#2b4a97" d="M0 0H1024V1024H0Z"/><g transform="translate(194.56 337.408) scale(3.1744)">'+mark(WHITE,BLUE)+'</g></svg>\n')
    print('Wrote master geometry, 23 outlined logos and icon master')

if __name__=='__main__': main()
