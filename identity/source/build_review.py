"""Compose a review board from final Blender renders. Requires pdftoppm."""
from pathlib import Path
from buddy_source import digest
import hashlib,json,shutil,subprocess
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

ROOT=Path(__file__).resolve().parents[1]
names=['buddy-feet-side','buddy-antlers','buddy-hands']
source_hash=digest()
for name in names:
    assert json.loads((ROOT/f'renders/{name}.json').read_text())['source_sha256']==source_hash
presentation=ROOT.parent/'buddy/presentation/studio-transparent.png'
assert json.loads(presentation.with_suffix('.json').read_text())['source_sha256']==source_hash
portrait=ROOT.parent/'buddy/presentation/portrait-transparent.png'
assert json.loads(portrait.with_suffix('.json').read_text())['source_sha256']==source_hash
for font,file in [('Body','InterTight-400.ttf'),('Semi','InterTight-600.ttf'),('Mono','IBMPlexMono-Regular.ttf')]:
    pdfmetrics.registerFont(TTFont(font,str(ROOT/'fonts'/file)))
W,H=1440,1000
pdf=ROOT/'.build/buddy-review-board.pdf'
c=canvas.Canvas(str(pdf),pagesize=(W,H))
def rect(x,y,w,h,color,r=0):
    c.setFillColor(HexColor(color))
    if r:c.roundRect(x,H-y-h,w,h,r,stroke=0,fill=1)
    else:c.rect(x,H-y-h,w,h,stroke=0,fill=1)
def text(value,x,y,size=18,font='Body',color='#172c50'):
    c.setFillColor(HexColor(color));c.setFont(font,size);c.drawString(x,H-y-size*.82,value)
def image(name,x,y,w,h):
    file=presentation if name=='studio' else portrait if name=='expression-welcoming' else ROOT/f'renders/{name}.png'
    with Image.open(file) as im:iw,ih=im.size
    scale=min(w/iw,h/ih);dw,dh=iw*scale,ih*scale
    c.drawImage(str(file),x+(w-dw)/2,H-y-h+(h-dh)/2,dw,dh,mask='auto')
rect(0,0,W,H,'#f4f3ef')
text('ORIGIN89 / BUDDY',40,30,14,'Mono')
text('Buddy / Character study.',40,63,42,'Semi')
text('SHARED BLENDER CHARACTER / V1',1060,35,12,'Mono')
rect(40,132,620,768,'#e8ebed',18)
image('studio',40,141,620,714)
text('Short legs. Big curiosity.',68,855,21,'Semi')
for name,x,y,title,caption in [
    ('buddy-antlers',692,132,'01 / Broad palmate antlers','Continuous palms and tapered tines.'),
    ('expression-welcoming',1060,132,'02 / Face & expression','Soft brows with a gentle lift.'),
    ('buddy-feet-side',692,527,'03 / Tapered cloven hooves','Rounded crowns seated inside the fur.'),
    ('buddy-hands',1060,527,'04 / Soft connected shoulders','Longer fur follows the raised arm.')]:
    rect(x,y,340,373,'#ffffff',16);image(name,x,y+5,340,305)
    text(title,x+19,y+318,18,'Semi');text(caption,x+19,y+347,14,color='#4b5761')
text('A round belly, short legs and soft shoulders. Dark muzzle, expressive eyes and broad antlers.',40,937,19)
text('Native geometry and attached hair curves. One 22-bone rig supports the skin, hooves and facial controls.',40,972,13,'Mono','#4b5761')
c.save()
poppler=shutil.which('pdftoppm')
if not poppler:raise SystemExit('Install Poppler (pdftoppm) to export the review PNG.')
dest=ROOT/'applications/buddy-review-board'
subprocess.run([poppler,'-singlefile','-r','100','-png',str(pdf),str(dest)],check=True)
dest.with_suffix('.json').write_text(json.dumps({'source_sha256':source_hash,'composition':'source/build_review.py','source_renders':names,'presentation_source':'../buddy/presentation/studio-transparent.png','presentation_sha256':hashlib.sha256(presentation.read_bytes()).hexdigest(),'portrait_source':'../buddy/presentation/portrait-transparent.png','portrait_sha256':hashlib.sha256(portrait.read_bytes()).hexdigest()},indent=2)+'\n')
print('Created',dest.with_suffix('.png'))
