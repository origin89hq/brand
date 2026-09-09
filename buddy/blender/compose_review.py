"""Compose native render contact sheets and verify their shared provenance."""
from pathlib import Path
import hashlib, json
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=sha(ROOT/'blender/buddy.blend')
def font(size,bold=False):
    return ImageFont.truetype(str(ROOT.parent/'identity/fonts'/('InterTight-600.ttf' if bold else 'InterTight-400.ttf')),size)
def sheet(name,title,subtitle,items,width=1800,columns=None):
    n=columns or len(items); gutter=24; margin=40; cell=(width-2*margin-gutter*(n-1))//n
    rows=(len(items)+n-1)//n; height=round(cell*1.12)
    canvas=Image.new('RGB',(width,162+rows*(height+76)),'#eeeae3'); draw=ImageDraw.Draw(canvas)
    draw.text((margin,28),'BUDDY / CHARACTER',font=font(18,True),fill='#526272')
    draw.text((margin,64),title,font=font(40,True),fill='#1d2d40')
    draw.text((margin,118),subtitle,font=font(20),fill='#526272')
    for i,(file,label) in enumerate(items):
        path=ROOT/'renders'/f'{file}.png'; meta=json.loads(path.with_suffix('.json').read_text())
        assert meta['source_sha256']==source,f'Stale render: {file}'
        im=Image.open(path).convert('RGB'); im.thumbnail((cell,height),Image.Resampling.LANCZOS)
        x=margin+(i%n)*(cell+gutter); y=162+(i//n)*(height+76)
        canvas.paste(im,(x+(cell-im.width)//2,y))
        draw.text((x,y+14+height),label,font=font(25 if n<4 else 20,True),fill='#1d2d40')
    canvas.save(ROOT/f'{name}.png')
sheet('color-comparison','Warm brown or navy','Identical geometry, camera, standing pose and lighting.',[('brown-hero','Warm brown'),('navy-hero','Navy')])
sheet('anatomy-layers','Built from the inside out','Stylized construction guides: adapted biped anatomy, not a specimen reconstruction.',[('skeleton-hero','Skeleton + cartilage'),('organs-hero','Organ volumes'),('muscles-hero','Muscle envelopes'),('skin-hero','Skin / clay'),('brown-hero','Fur')],2200)
sheet('pose-study','Upright pose studies','Standing, explaining and one step. A finished walk cycle is a later animation pass.',[('brown-hero','Standing / frame 1'),('explaining','Explaining / frame 40'),('step','Step / frame 80')])
sheet('proportion-study','Front and side proportions','The same skeleton, tissue envelopes and skin support both views.',[('brown-front','Front'),('brown-side','Side'),('skeleton-side','Skeleton under skin')])
sheet('face-study','Muzzle, nostrils and ears','Front, three-quarter and profile views of the same native head geometry.',[('brown-face-front','Front'),('brown-face','Three-quarter'),('brown-face-side','Profile')])
sheet('expression-study','A face that can move','Jaw, lips, brows and eyelids share one editable character and attached fur.',[
    ('expression-neutral','Neutral / 1'),('expression-smile','Smile / 110'),
    ('expression-delighted','Delighted / 140'),('expression-surprised','Surprised / 170'),
    ('expression-concerned','Concerned / 200'),('expression-wink','Wink / 230'),
    ('expression-blink','Blink / 260'),('expression-playful','Playful / 290'),
    ('expression-skeptical','Skeptical / 320'),
    ('expression-tongue-peek','Tongue peek / 350')],width=2600,columns=5)
sheet('eyelid-study','Blink, wink and squint','Independent upper and lower lids cover the corneas as the face changes.',[
    ('expression-neutral','Open'),('expression-wink','One-sided wink'),('expression-blink','Closed / 260')])
sheet('mouth-study','Smile and tooth visibility','The curved tooth row follows the mandible; soft lips cover or reveal the crowns.',[
    ('expression-smile-front','Smile / front'),('expression-delighted','Open smile / three-quarter'),
    ('expression-delighted-side','Open mouth / profile')])
sheet('tongue-study','A flexible, playful tongue','Extension, curl, sideways bend, twist and width are independently keyframeable.',[
    ('expression-playful-front','Front'),('expression-playful','Three-quarter'),('expression-playful-side','Profile')])
files=[p for p in ROOT.rglob('*') if p.is_file() and not any(v in ('.build','__pycache__') for v in p.relative_to(ROOT).parts) and p.suffix in ('.blend','.py','.png','.jpg','.json','.html','.md','.svg','.mjs','.webp') and p.name!='manifest.json']
(ROOT/'manifest.json').write_text(json.dumps({'character':'Buddy the moose','native_source':'blender/buddy.blend','source_sha256':source,'shared_fur_helper':'blender/fur.py','shared_fur_sha256':sha(ROOT/'blender/fur.py'),'files':{str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}},indent=2)+'\n')
print('Verified and composed',len(files),'native-source and review files.')
