"""Lay out native Blender expression renders with editable vector typography."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
from buddy_source import digest
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--poses',action='store_true');args=p.parse_args()
source_hash=digest()
states=[('welcoming','Welcoming','Here to help.'),('explaining','Explaining','Make the next step clear.'),
        ('thinking','Thinking','Work through the question.'),('delighted','Delighted','Celebrate a confirmed result.'),
        ('concerned','Concerned','Something needs attention.'),('surprised','Surprised','An unexpected change.')]
for font,file in [('Body','InterTight-400.ttf'),('Semi','InterTight-600.ttf'),('Mono','IBMPlexMono-Regular.ttf')]:
    pdfmetrics.registerFont(TTFont(font,str(ROOT/'fonts'/file)))
W,H=1500,1330
stem='buddy-expression-poses' if args.poses else 'buddy-expression-sheet'
pdf=ROOT/f'.build/{stem}.pdf';c=canvas.Canvas(str(pdf),pagesize=(W,H))
def rect(x,y,w,h,color,r=0):
    c.setFillColor(HexColor(color));c.roundRect(x,H-y-h,w,h,r,stroke=0,fill=1)
def text(value,x,y,size=18,font='Body',color='#172c50'):
    c.setFillColor(HexColor(color));c.setFont(font,size);c.drawString(x,H-y-size*.82,value)
rect(0,0,W,H,'#f4f3ef')
text('ORIGIN89 / CHARACTER DEVELOPMENT',48,34,14,'Mono')
text('Buddy, with more to say.',48,75,51,'Semi')
text('Six expressions. One familiar helper.',48,143,21,color='#4b5761')
text('01 / PORTRAIT GESTURES' if args.poses else '01 / CIRCULAR AVATARS',1165,42,13,'Mono')
names=[]
for i,(name,label,caption) in enumerate(states):
    x=48+(i%3)*478;y=205+(i//3)*527
    portrait_stem='portrait' if name=='welcoming' else 'portrait-'+name
    render=f'../buddy/presentation/{portrait_stem}-transparent.png' if args.poses else f'../buddy/avatar/buddy-{name}-round.png'
    names.append(render)
    if args.poses:
        meta=json.loads((ROOT/render).with_suffix('.json').read_text())
        assert meta['source_sha256']==source_hash
    else:
        meta=json.loads((ROOT/'../buddy/avatar/manifest.json').read_text())
        assert meta['source_sha256']==source_hash
    rect(x,y,448,495,'#e8ebed',18)
    c.drawImage(str(ROOT/render),x+10,H-y-402,428,390,mask='auto',preserveAspectRatio=True,anchor='c')
    text(f'{i+1:02d} / {label}',x+23,y+420,25,'Semi')
    text(caption,x+23,y+460,18,color='#4b5761')
text('Eyes, brows, cheeks and mouth move together; head tilt and hoof hands carry the gesture.',48,1258,19)
text('EDITABLE BLENDER SOURCE / SIX PRESETS / TRANSPARENT PORTRAITS' if args.poses else 'SHARED NATIVE PORTRAITS / GREEN CIRCULAR AVATARS',48,1302,12,'Mono','#4b5761')
c.save()
poppler=shutil.which('pdftoppm')
if not poppler:raise SystemExit('Install Poppler (pdftoppm) to export the board.')
dest=ROOT/f'applications/{stem}'
subprocess.run([poppler,'-singlefile','-r','96','-png',str(pdf),str(dest)],check=True)
dest.with_suffix('.json').write_text(json.dumps({'source_sha256':source_hash,'composition':'source/build_expression_board.py','source_renders':names},indent=2)+'\n')
print('Created',dest.with_suffix('.png'))
