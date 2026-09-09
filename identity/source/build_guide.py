"""Editable design-guide source. Requires ReportLab and Pillow.
All type and logos in the PDF are vector. The 3D art is rendered from the
delivered .blend. Run from any directory with Python 3.
"""
from pathlib import Path
import json, math, textwrap, shutil, subprocess
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'guide/output/pdf'; OUT.mkdir(parents=True,exist_ok=True)
G=json.loads((ROOT/'source/geometry.json').read_text())
T=json.loads((ROOT/'tokens/brand-tokens.json').read_text())
CONTRAST=json.loads((ROOT/'tokens/contrast-report.json').read_text())
for name,file in [('Body','InterTight-400.ttf'),('Semi','InterTight-600.ttf'),('Bold','InterTight-700.ttf'),('Mono','IBMPlexMono-Regular.ttf'),('Display','Michroma-Regular.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(ROOT/'fonts'/file)))
W,H=960,640; M=48; TOTAL_PAGES=20
BLUE='#2b4a97'; INK='#07090c'; CHALK='#e7eaee'; PAPER='#f4f3ef'; MUTED='#4b5761'; LINE='#d7d9d8'
c=canvas.Canvas(str(OUT/'origin89-design-guide.pdf'),pagesize=(W,H),pageCompression=1,invariant=1)
c.setTitle('Origin89 / Plate 89 / Design guide v1.0');c.setAuthor('Origin89');c.setSubject('Identity, application, 3D and Buddy usage guide')
PAGE=0;DARK=False; copy=[]; bounds=[]
def fill(col):c.setFillColor(HexColor(col))
def rect(x,y,w,h,color,r=0):
    fill(color)
    if r:c.roundRect(x,H-y-h,w,h,r,fill=1,stroke=0)
    else:c.rect(x,H-y-h,w,h,fill=1,stroke=0)
def line(x,y,x2,y2,color=LINE,width=1,dash=None):
    c.setStrokeColor(HexColor(color));c.setLineWidth(width);c.setDash(dash or [])
    c.line(x,H-y,x2,H-y2);c.setDash([])
def text(s,x,y,size=14,font='Body',color=None,record=True):
    color=color or (CHALK if DARK else INK)
    fill(color);c.setFont(font,size);c.drawString(x,H-y-size*.82,s)
    width=pdfmetrics.stringWidth(s,font,size)
    if x<0 or x+width>W+1 or y<0 or y+size>H+1:bounds.append((PAGE,s,x,y,width,size))
    if record:copy.append(s)
    return width
def para(s,x,y,width,size=15,leading=21,color=None,font='Body'):
    words=s.split();lines=[];cur=''
    for word in words:
        trial=(cur+' '+word).strip()
        if pdfmetrics.stringWidth(trial,font,size)>width and cur:lines.append(cur);cur=word
        else:cur=trial
    if cur:lines.append(cur)
    for i,row in enumerate(lines):text(row,x,y+i*leading,size,font,color,record=False)
    copy.append(s);return y+len(lines)*leading
def small(s,x,y,color=None):return text(s,x,y,10,'Mono',color or ('#9aa5b1' if DARK else MUTED))
def path(commands,x,y,scale,color):
    c.saveState();c.translate(x,H-y);c.scale(scale,-scale);fill(color);p=c.beginPath()
    for op,pts in commands:
        if op=='moveTo':p.moveTo(*pts[0])
        elif op=='lineTo':p.lineTo(*pts[0])
        elif op=='curveTo':p.curveTo(*[n for pt in pts for n in pt])
        elif op=='closePath':p.close()
    c.drawPath(p,stroke=0,fill=1,fillMode=0);c.restoreState()
def mark(x,y,w=120,bg=BLUE,fg=CHALK):
    path(G['plate'],x,y,w/200,bg);path(G['eight']+G['nine'],x,y,w/200,fg)
def signature(x,y,width=380,variant='blue',sub=None):
    bg,fg,tc={'blue':(BLUE,CHALK,INK),'white':('#ffffff',INK,'#ffffff'),'black':(INK,'#ffffff',INK)}[variant]
    wd=G['words']['Origin89'];extent=244+wd['width']*(1 if sub else 1.05);s=width/extent
    mark(x,y,200*s,bg,fg)
    path(wd['commands'],x+244*s,y+(6 if sub else (110-wd['height']*1.05)/2)*s,s*(1 if sub else 1.05),tc)
    if sub:path(G['words'][sub]['commands'],x+244*s,y+79*s,s,tc)
def image(name,x,y,w,h,cover=False,trim=False):
    file=ROOT/name;im=Image.open(file)
    if trim:
        boxes=[Image.open(ROOT/f'renders/buddy-{pose}-transparent.png').getbbox() for pose in ['ready','explaining','thinking']]
        im=im.crop((min(b[0] for b in boxes)-10,min(b[1] for b in boxes)-10,max(b[2] for b in boxes)+10,max(b[3] for b in boxes)+10))
    iw,ih=im.size;scale=(max if cover else min)(w/iw,h/ih)
    dw,dh=iw*scale,ih*scale
    # Embed only the pixels used at 180 dpi. Keep type and logo paths vector.
    im.thumbnail((math.ceil(dw*2.5),math.ceil(dh*2.5)),Image.Resampling.LANCZOS)
    c.saveState()
    if cover:
        p=c.beginPath();p.rect(x,H-y-h,w,h);c.clipPath(p,stroke=0)
    if name.startswith('renders/') and 'portrait' in name:
        p=c.beginPath();p.circle(x+w/2,H-y-h/2,min(w,h)/2);c.clipPath(p,stroke=0)
    if name.startswith('../buddy/presentation/') and '-transparent' not in name:
        p=c.beginPath();p.roundRect(x+(w-dw)/2,H-y-h+(h-dh)/2,dw,dh,12);c.clipPath(p,stroke=0)
    c.drawImage(ImageReader(im),x+(w-dw)/2,H-y-h+(h-dh)/2,dw,dh,mask='auto')
    c.restoreState()
def start(section,title=None,subtitle=None,dark=False):
    global PAGE,DARK
    PAGE+=1;DARK=dark;copy.append('\n## '+str(PAGE).zfill(2)+' / '+section+'\n')
    rect(0,0,W,H,INK if dark else PAPER)
    small('ORIGIN89 / PLATE 89',M,24)
    small(section.upper(),590,24)
    line(M,51,W-M,51,'#2b343f' if dark else LINE)
    if title:text(title,M,76,38,'Semi')
    if subtitle:para(subtitle,M,127,825,14,20,'#9aa5b1' if dark else MUTED)
def end():
    line(M,594,W-M,594,'#2b343f' if DARK else LINE)
    small('DESIGN GUIDE / v1.0 / 08 SEP 2026',M,612)
    small(f'{PAGE:02d} / {TOTAL_PAGES}',856,612)
    c.showPage()
def block(label,body,x,y,w=250):
    text(label,x,y,20,'Semi');para(body,x,y+34,w,14,20,MUTED if not DARK else '#9aa5b1')
def pill(s,x,y,w,color=BLUE):
    rect(x,y,w,29,color,7);text(s,x+12,y+8,12,'Semi','#ffffff')
def app_card(x,y,w,h,dark=False,buddy=False):
    t=T['themes']['dark' if dark else 'light'];rect(x,y,w,h,t['page'],16)
    mark(x+20,y+20,48,t['action'],CHALK);text('Origin89 Offgrid',x+82,y+25,15,'Semi',t['fg'])
    text('North cottage',x+20,y+73,25,'Semi',t['fg']);text('Overview',x+20,y+107,12,'Body',t['muted'])
    rect(x+20,y+138,w-40,98,t['surface-raised'],9)
    text('BATTERY',x+35,y+152,10,'Mono',t['muted']);text('78%',x+35,y+174,34,'Semi',t['fg'])
    text('Updated 4 s ago',x+155,y+192,11,'Body',t['muted'])
    rect(x+20,y+247,w-40,66,t['surface-raised'],9)
    text('Cottage temperature',x+35,y+260,13,'Semi',t['fg'])
    text('18.4 C',x+35,y+281,15,'Mono',t['fg']);text('Measured',x+w-104,y+283,11,'Body',t['muted'])
    if buddy:
        rect(x+20,y+322,w-40,60,t['surface-raised'],9)
        image('../buddy/avatar/buddy-welcoming-round.png',x+26,y+325,54,54)
        text('Ask Buddy',x+92,y+331,15,'Semi',t['fg'])
        para('Explain a reading or plan a check.',x+92,y+355,w-126,11,14,t['muted'])
    small('DESIGN PREVIEW / SAMPLE DATA',x+20,y+h-25,t['muted'])

# 01
start('Identity system',dark=True)
signature(48,85,325,'white')
text('Built for',48,210,56,'Semi');text('your corner',48,269,56,'Semi');text('of the world.',48,328,56,'Semi')
para('Simple control. Your way.\nFrom a cottage to the field.',48,425,350,19,27,'#b8c2d0')
image('renders/tile-transparent.png',450,86,478,465)
for i,col in enumerate([BLUE,CHALK,PAPER]):rect(49+i*45,549,32,5,col)
small('THE SELECTED PLATE 89 DIRECTION',48,516)
end()
# 02
start('Brand foundation','Simple at the cottage. Capable in the field.')
para('Origin89 makes site equipment easier to understand and configure. The identity should feel familiar at a cabin and credible beside industrial equipment.',48,137,660,19,27)
image('renders/plate-transparent.png',532,209,380,222)
text('Useful.',48,230,41,'Semi');text('Adaptable.',48,282,41,'Semi');text('Grounded.',48,334,41,'Semi')
block('A place you care about','Cottages, remote buildings and off-grid power. Start with the owner\'s actual site.',48,453,255)
block('Equipment you depend on','Pumps, heaters, valves and field sensors. Keep the interface clear as the site grows.',353,453,255)
block('Control that stays yours','Customizable views and understandable settings. Buddy helps people find the next step.',658,453,254)
end()
# 03
start('Brand architecture','One company. A connected product family.')
signature(340,147,280)
line(480,202,480,240,BLUE,1.5);line(180,240,780,240,BLUE,1.5)
for x,sub,caption in [(48,'Controller','Hardware at your site'),(348,'Offgrid','The app for your site'),(648,'Buddy','Your assistant in app + docs')]:
    line(x+132,240,x+132,267,BLUE,1.5);rect(x,267,264,173,'#ffffff',12)
    mark(x+24,287,63);text('Origin89',x+24,341,22,'Semi');text(sub,x+24,370,28,'Semi',BLUE)
    text(caption,x+24,414,12,'Body',MUTED)
line(313,355,346,355,BLUE,1.5);line(613,355,646,355,BLUE,1.5)
rect(48,464,864,90,'#e6e9e9',10)
text('KM43',72,483,24,'Mono');para('Protocol name for technical documentation. Firmware is described as Origin89 Controller firmware; KM43 is not the app or firmware brand.',243,486,634,15,21)
small('USE "BUDDY" IN CONVERSATION. USE "ORIGIN89 BUDDY" WHERE OWNERSHIP NEEDS CONTEXT.',48,570)
end()
# 04
start('Master identity','A recognizable plate. A clear signature.','The clipped corners recall a field identification plate. The custom 89 carries recognition at small sizes.')
rect(48,183,864,214,'#ffffff',12);signature(99,225,762)
mark(62,455,136);path(G['words']['Origin89']['commands'],335,454,.92,INK)
para('The symbol is custom artwork. Preserve the open counters and the wide, steady stance.',62,548,235,12,17,MUTED)
para('The wordmark is an optically weighted Michroma outline. Use the artwork; typing the name will not recreate this lockup.',335,525,560,14,20,MUTED)
end()
# 05
start('Construction','Precision where it matters.','Use H, the height of the plate, to scale the system. Clear space is measured from the outside edge of the complete lockup.')
x,y,s=185,249,2.1;cw=27.5*s
rect(x-cw,y-cw,420+cw*2,231+cw*2,'#e5e9ef')
for gx in range(10):line(x+gx*46.666,y-cw,x+gx*46.666,y+231+cw,'#d3dae4',.5)
for gy in range(7):line(x-cw,y+gy*38.5,x+420+cw,y+gy*38.5,'#d3dae4',.5)
mark(x,y,420)
line(x,y-20,x+420,y-20,BLUE);small('200 UNITS',x+168,y-38,BLUE)
line(x+440,y,x+440,y+231,BLUE);small('H = 110',x+451,y+109,BLUE)
small('H / 4',x-cw,y-cw-18,BLUE)
block('14-unit chamfer','Four clipped corners. Keep the silhouette; do not round it into an app tile.',706,224,188)
block('27.5-unit margin','Minimum clear space on every side. More space is welcome.',706,374,188)
small('THE LOGO IS THE PLATE. THE ROUNDED APP TILE IS A SEPARATE CONTAINER.',48,563)
end()
# 06
start('Lockups and reproduction','Choose the version for the surface.')
for i,(variant,label,col) in enumerate([('blue','PRIMARY / LIGHT', '#ffffff'),('white','REVERSED / DARK',INK),('black','MONOCHROME / LIGHT','#ffffff')]):
    y=155+i*130;rect(48,y,535,107,col,9);signature(110,y+19,410,variant)
    small(label,620,y+4)
    para(['Bridge blue with chalk numerals. Use for the website, stationery and light interfaces.','White plate and wordmark on a dark surface. Use the knockout SVG when the substrate should show through.','For one-ink printing or marking, use the dedicated knockout plate. Confirm the process with a physical proof.'][i],620,y+27,275,14,20,MUTED)
small('HORIZONTAL: DEFAULT. STACKED: NARROW FORMATS. PRODUCT LOCKUPS: USE THE DELIVERED ART.',48,567)
end()
# 07
start('Small sizes and care','Recognition survives restraint.','Practical starting sizes for this identity; check the final device, substrate and viewing distance.')
text('Symbol',48,195,22,'Semi');text('Signature',351,195,22,'Semi');text('Product lockup',651,195,22,'Semi')
for i,width in enumerate([24,40,64]):mark(48+i*86,249,width)
signature(351,249,170);signature(651,249,250,sub='Offgrid')
para('Start at 24 px wide in normal UI. The dedicated favicon fills more of its canvas and has 16/32/48 px exports.',48,329,250,15,21)
para('Start at 170 px wide on screen or 35 mm in print. Use the symbol alone when the full name becomes cramped.',351,329,250,15,21)
para('Start at 300 px wide on screen or 55 mm in print. Keep the product descriptor readable at the final output size.',651,329,250,15,21)
rect(48,467,864,92,'#e5e9ef',10)
text('Keep the geometry intact.',72,486,22,'Semi')
para('No stretching, independent letter spacing, extra outlines, pasted gradients, new symbols inside the counters or decorative shadows on the flat logo.',390,485,496,14,20)
end()
# 08
start('Brand color','Bridge blue is the anchor.','A focused palette gives the physical product and digital experience a shared identity.')
palette=[('Bridge blue',BLUE,'43 / 74 / 151'),('Ink',INK,'7 / 9 / 12'),('Chalk',CHALK,'231 / 234 / 238'),('Paper',PAPER,'244 / 243 / 239')]
for i,(name,color,rgb) in enumerate(palette):
    x=48+i*221;rect(x,174,201,149,color,10)
    if name=='Paper':
        c.setStrokeColor(HexColor(LINE));c.setLineWidth(1);c.roundRect(x,H-174-149,201,149,10,stroke=1,fill=0)
    text(name,x,341,20,'Semi');small(color.upper(),x,373);small('RGB '+rgb,x,395)
text('Pairs that work',48,447,22,'Semi')
for i,r in enumerate(CONTRAST[:4]):
    x=48+i*221;small(f'{r["ratio"]:.2f}:1',x,488,BLUE);para(r['label'],x,512,185,13,18)
small('sRGB MASTERS. PRINT COLORS REQUIRE A PROCESS-SPECIFIC PROOF; NO UNIVERSAL CMYK MATCH.',48,570)
end()
# 09
start('Product color','Brand color does not replace state.')
app_card(48,152,313,398,False);app_card(385,152,313,398,True)
block('Use semantic tokens','The kit includes the current light and dark product palettes. Keep states connected to labels and icons.',730,167,183)
text('Blue on ink',730,322,19,'Semi');text('2.40:1',730,353,30,'Mono',BLUE)
para('Too low for ordinary body text. Use the lightened dark-theme link token (#6279ad): 4.61:1 on ink.',730,399,179,13,19,MUTED)
para('Missing is a state, not zero. Show freshness beside readings.',730,514,179,13,19,MUTED)
end()
# 10
start('Typography','Character in the mark. Clarity everywhere else.')
path(G['words']['Origin89']['commands'],48,169,.8,INK)
small('MICHROMA / CUSTOM OUTLINED WORDMARK',48,233)
text('Make the site yours.',48,293,44,'Semi');text('Inter Tight / 400, 600, 700',48,353,17)
para('Use Inter Tight for product names, headings, instructions and interface copy. Sentence case keeps complex equipment approachable.',48,392,478,16,23)
rect(594,169,318,303,INK,12)
for i,sample in enumerate(['BATTERY     78%','SOLAR    2.4 kW','PROBE    18.4 C','UPDATED     4 s']):text(sample,620,207+i*54,20,'Mono',CHALK)
small('IBM PLEX MONO / READINGS + IDs',594,493)
small('TYPE SCALE',48,529);text('12 / 14 / 16 / 20 / 28 / 40 / 56',48,554,19,'Semi')
para('Body: 16 px / 24 px line height. Use tabular readings, visible units and a distinct freshness label.',594,533,318,13,18,MUTED)
end()
# 11
start('Three-dimensional language','Tactile. Quiet. Built from the real mark.')
image('renders/plate-transparent.png',22,151,456,286)
image('renders/tile-transparent.png',467,151,443,344)
block('Satin shell','Deep navy #172c50. Roughness 0.48. Fine texture and soft edge highlights.',48,464,263)
block('Ceramic face','Warm ivory #eadfcf. Roughness 0.36. Raised numerals or a recessed inverse plate.',350,464,263)
block('Soft studio','Broad key, soft fill and rim. AgX: plate -0.65 EV; Buddy -0.55 EV. Orthographic views.',652,464,263)
small('3D IS FOR HEROES, ICONS AND EXPLAINERS. USE FLAT SVG FOR NAVIGATION AND HARDWARE MARKING.',48,570)
end()
# 12
start('Offgrid app icon','One mark, from launch screen to favicon.')
image('renders/icon.png',48,180,270,270)
image('icons/offgrid-flat-1024.png',349,180,270,270)
small('3D / FULL-BLEED MASTER',48,470);small('FLAT / FULL-BLEED MASTER',349,470)
para('Both are unmasked square assets. Let the target platform apply its own shape and packaging.',48,510,562,16,23)
text('Small-size family',681,183,22,'Semi')
for i,size in enumerate([32,48,64]):image(f'icons/offgrid-flat-{size}.png',681+i*78,235,size,size)
para('Use the flat icon when relief details disappear. The app name stays in the label below the icon.',681,335,221,15,21)
image('icons/favicon-48.png',683,437,40,40);text('Favicon',739,447,16,'Semi')
para('The compact favicon uses the plate without the large tile margin.',681,503,221,14,20,MUTED)
end()
# 13
start('Buddy','A capable helper with a familiar face.','Warm brown fur, a dark muzzle, broad antlers and tapered cloven hooves. Short legs, soft shoulders and a round belly.')
image('../buddy/presentation/portrait-transparent.png',48,170,385,355)
image('../buddy/presentation/studio-transparent.png',516,170,330,370)
text('A familiar face.',65,545,21,'Semi')
text('Transparent portrait for introductions and explanations.',65,578,12,'Body',MUTED)
text('The whole character.',516,553,19,'Semi')
text('Full character with a transparent background.',516,579,12,'Body',MUTED)
end()
# Expression library
start('Expression library','A face that follows the moment.','Use a front-facing close-up on green for small avatars. Wider portraits belong in website scenes and illustrations.')
for i,(name,label,caption) in enumerate([
    ('welcoming','Welcoming','Here to help.'),('explaining','Explaining','Make the next step clear.'),
    ('thinking','Thinking','Work through the question.'),('delighted','Delighted','Celebrate a confirmed result.'),
    ('concerned','Concerned','Something needs attention.'),('surprised','Surprised','An unexpected change.')]):
    x=48+(i%3)*296;y=169+(i//3)*202
    rect(x,y,272,187,'#e8ebed',10)
    image(f'../buddy/avatar/buddy-{name}-round.png',x+70,y+1,132,132)
    text(label,x+15,y+137,18,'Semi');text(caption,x+15,y+166,12,'Body',MUTED)
small('USE A STILL POSE BESIDE READINGS. EXPRESSIONS SUPPORT THE MESSAGE; LABEL THE ACTUAL STATE.',48,578)
end()
# Playful character moment
start('A little personality','Small legs. Big curiosity.','A rounded tongue peek, relaxed eyes with the same camera, soft coat and studio lighting as the main portrait.')
image('../buddy/presentation/portrait-playful-transparent.png',48,165,385,385)
small('A LIGHTHEARTED INTRODUCTION',492,190)
image('../buddy/avatar/buddy-playful-round.png',493,240,60,60)
text('Buddy',575,245,20,'Semi')
para('Small legs. Big curiosity.',575,281,307,17,23)
para('Use this pose in introductions, optional character moments and celebrations. Keep concerned and neutral expressions available when the message needs care.',492,364,377,16,23,MUTED)
small('LARGE: TRANSPARENT PORTRAIT / SMALL: GREEN CIRCLE',48,578)
end()
# Assistance in context
start('Assistance in context','Buddy belongs beside the task.')
app_card(48,151,338,418,False,True)
rect(421,151,491,418,'#ffffff',14)
small('ORIGIN89 DOCS / TROUBLESHOOTING',446,175)
text('A probe stopped reporting.',446,211,28,'Semi')
para('Start with the last reading and its timestamp. A missing reading needs investigation before a setting is changed.',446,259,438,16,23)
line(446,330,887,330)
image('../buddy/avatar/buddy-welcoming-round.png',449,351,99,99)
text('Buddy',563,358,20,'Semi')
para('The last reading was 12 minutes ago. Check the probe connection, then check whether readings resume.',563,394,302,15,21)
pill('Show the checks',563,475,142)
small('DESIGN PREVIEW / EXAMPLE ASSISTANT COPY',446,542)
end()
# 15
start('Hardware and print','The same identity, made physical.','Artwork placement study. Keep manufacturing details in the controller\'s approved mechanical and electrical sources.')
rect(48,170,474,355,'#151a20',17);rect(63,185,444,325,'#0d1116',13)
signature(99,239,367,'white',sub='Controller')
line(99,343,470,343,'#3a434d')
rect(102,384,7,7,'#4c7d5f',3);text('STATUS',124,383,11,'Mono',CHALK)
text('ORIGIN89',99,459,11,'Mono','#9aa5b1')
rect(575,170,337,183,'#ffffff',9);signature(599,201,286)
text('Simple control. Your way.',599,285,17,'Semi')
rect(575,384,337,141,BLUE,9);mark(599,415,115,CHALK,BLUE)
text('Origin89 Controller',599,498,14,'Semi','#ffffff')
small('PRINT / MARKING: USE FLAT OUTLINED ART AND THE KNOCKOUT FILES.',48,565)
end()
# 16
start('Layout system','Room for the product. Room for the person.')
rect(48,158,553,349,'#ffffff',12)
signature(75,183,227)
text('Your site.',75,259,35,'Semi');text('At a glance.',75,300,35,'Semi')
para('Bring the equipment that matters into one clear view.',75,354,205,14,20,MUTED)
pill('Explore Offgrid',75,433,138)
image('renders/tile-transparent.png',293,218,276,266)
for i,(n,title,body) in enumerate([('01','Lead with a useful statement','Name the site, task or outcome before the technology.'),('02','Give one visual the lead','One hero render per section. Keep labels flat and sharp.'),('03','Use a consistent rhythm','Spacing: 4, 8, 16, 24, 40, 64 px. Align artwork to the same grid as copy.')]):
    y=168+i*139;small(n,635,y,BLUE);text(title,671,y,19,'Semi');para(body,671,y+33,227,14,20,MUTED)
small('EXAMPLE WEB LAYOUT / 24 PX GUTTERS / 40 PX SECTION PADDING',48,552)
end()
# 17
start('Voice and motion','Helpful language. Deliberate movement.')
block('Say what happened','"No new reading for 12 minutes." Include the observation, timestamp and useful next step.',48,175,393)
block('Explain a choice','"Choose which equipment appears in this view." Use concrete verbs and respect the site owner\'s configuration.',48,314,393)
block('Avoid a false promise','Do not say "Everything is safe" or imply that an assistant suggestion has already changed equipment.',48,460,393)
rect(492,164,420,397,INK,13)
text('Buddy proposes.',518,195,31,'Semi',CHALK);text('The user decides.',518,236,31,'Semi',CHALK)
para('Keep proposed changes separate from measurements and confirmed actions. Surface uncertainty and missing information.',518,294,357,16,23,'#b8c2d0')
line(518,379,883,379,'#2b343f')
para('Motion direction: 180-240 ms fades or small pose transitions. No perpetual bobbing beside live readings. Reduced motion uses a still pose.',518,405,357,15,22,'#b8c2d0')
small('STILLS + KEYED SOURCE POSES INCLUDED.',518,531,'#9aa5b1')
end()
# 18
start('Handoff','A kit you can keep working with.')
rows=[('logos/','23 outlined SVGs + 2000 px transparent PNGs'),('icons/','Flat + 3D PNG sizes, favicon SVG / PNG / ICO'),('blender/','Four identity scenes; Buddy lives in its own shared source'),('renders/','Studio and transparent PNGs with render metadata'),('tokens/','CSS + JSON palette snapshot and measured contrast'),('fonts/','Michroma, Inter Tight, IBM Plex Mono + OFL licenses'),('source/','Rebuild, render, export, guide and packaging scripts')]
for i,(folder,desc) in enumerate(rows):
    y=159+i*42;small(folder,48,y,BLUE);text(desc,190,y,14);line(48,y+29,912,y+29,LINE,.6)
text('Working-source status',48,477,20,'Semi')
para('Buddy has one editable model with a 22-bone rig. Front-facing avatars use green circles. Wider portraits and full-body images stay transparent. Run pnpm brand:avatars after front camera or expression edits, brand:export after composition edits, or brand:rebuild after model edits.',48,511,541,13,18,MUTED)
small('REFERENCE + LICENSES',628,477)
links=[('Font sources + OFL','https://github.com/google/fonts'),('WCAG contrast minimum','https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html')]
for i,(label,url) in enumerate(links):
    y=505+i*28;tw=text(label,628,y,13,'Body',BLUE);c.linkURL(url,(628,H-y-16,628+tw,H-y),relative=0)
small('HEX VALUES MEASURED; SEE CONTRAST REPORT.',628,564)
end()

assert PAGE==TOTAL_PAGES, 'Update the guide page total'
if bounds:raise RuntimeError('Out-of-page content: '+repr(bounds))
c.save()
(ROOT/'guide/design-guide.md').write_text('# Origin89 / Plate 89 / Design guide v1.0\n\n'+'\n\n'.join(copy)+'\n\n## Sources\n\n- Font binaries and OFL: https://github.com/google/fonts/tree/main/ofl (Michroma, Inter Tight, IBM Plex Mono).\n- Contrast guidance: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html\n- Product color snapshot: packages/tokens/src/palette.mjs, 2026-09-06.\n- Direction: 01-plate-89.png in the repository concept archive. Native geometry is an original redraw.\n')
(ROOT/'.build/guide-validation.json').write_text(json.dumps({'pages':PAGE,'out_of_page_content':bounds,'output':str(OUT/'origin89-design-guide.pdf')},indent=2))
poppler=shutil.which('pdftoppm')
if not poppler:raise SystemExit('Install Poppler (pdftoppm) to export the guide cover.')
subprocess.run([poppler,'-f','1','-l','1','-singlefile','-r','100','-png',str(OUT/'origin89-design-guide.pdf'),str(ROOT/'guide/cover')],check=True)
print(f'Created {PAGE}-page guide with vector logos, embedded fonts and native Blender renders.')
