"""Composite front-facing native Buddy cutouts on green for small avatars."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw
out=Path(__file__).resolve().parent
root=out.parents[1]
EXPRESSIONS=('welcoming','explaining','thinking','delighted','concerned','surprised','playful')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_hash=sha(root/'buddy/blender/buddy.blend')
registry=json.loads((root/'buddy-source.json').read_text())
scene=root/registry['avatar_scene']
inputs={}
for expression in EXPRESSIONS:
    name=scene.stem+('' if expression=='welcoming' else '-'+expression)
    source=scene.with_name(name+'.png')
    meta=json.loads(source.with_suffix('.json').read_text())
    assert meta['source_sha256']==source_hash and meta['render_sha256']==sha(source),f'Stale native portrait: {source}'
    assert meta['recipe_sha256']==sha(root/'buddy/presentation/render_face.py'),f'Stale face recipe: {source}'
    assert meta['scene_source_sha256']==sha(root/meta['scene_source']),f'Stale presentation scene: {source}'
    assert meta['transparent'] and meta['look']=='face-front' and meta['expression']==expression
    if expression=='welcoming':assert meta['controls']['face_tongue_out']==0.,'The default avatar keeps its tongue tucked in'
    if 'scene_sha256' in meta:assert meta['scene_sha256']==sha(source.with_suffix('.blend'))
    inputs[expression]={'path':str(source.relative_to(root)),'sha256':sha(source)}
for expression,source_info in inputs.items():
    source=root/source_info['path']
    with Image.open(source) as original:
        assert original.mode=='RGBA' and original.getextrema()[3]==(0,255),f'Native alpha missing: {source}'
        # Preserve the approved front camera crop. The source stays transparent;
        # only avatars and platform icons acquire the solid green background.
        im=Image.new('RGBA',original.size,'#3d5749')
        im.alpha_composite(original)
        im=im.convert('RGB').resize((512,512),Image.Resampling.LANCZOS)
        im.save(out/f'buddy-{expression}.png',optimize=True)
        mask=Image.new('L',(2048,2048));ImageDraw.Draw(mask).ellipse((0,0,2047,2047),fill=255)
        rounded=im.convert('RGBA');rounded.putalpha(mask.resize((512,512),Image.Resampling.LANCZOS))
        rounded.save(out/f'buddy-{expression}-round.png',optimize=True)
        for size in (48,96,192,384):
            im.resize((size,size),Image.Resampling.LANCZOS).save(out/f'buddy-{expression}-{size}.webp','WEBP',quality=88,method=6)
(out/'manifest.json').write_text(json.dumps({'source_sha256':source_hash,'recipe_sha256':sha(Path(__file__)),'construction':'Front-facing native alpha renders composited on green, shown in a circle at small sizes.','background':'#3d5749','crop_normalized':[0,0,1,1],'expressions':list(EXPRESSIONS),'inputs':inputs,'files':{p.name:sha(p) for p in sorted(out.glob('buddy-*')) if p.suffix in ('.png','.webp')}},indent=2)+'\n')
print('Built',len(EXPRESSIONS),'native Buddy avatars with green backgrounds')

html='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Buddy · Circular avatars</title><style>*{box-sizing:border-box}body{margin:0;background:#f4f3ef;color:#24332c;font:16px/1.5 system-ui}main{max-width:960px;padding:32px;margin:auto}h1{letter-spacing:-.04em}.row{display:flex;gap:24px;flex-wrap:wrap;align-items:center}figure{margin:12px 0}img{border-radius:50%;display:block}figcaption{margin-top:8px;font-size:13px}.message{display:flex;align-items:center;gap:14px;background:white;padding:20px;border-radius:16px;margin:32px 0;max-width:380px}</style><main><h1>One Buddy, at every size.</h1><p>A front-facing close-up on green for avatars. Wider portraits and scenes keep their own framing.</p><div class="row">'
for size in (24,32,48,64,96):
    html+=f'<figure><img src="buddy-welcoming-96.webp" srcset="buddy-welcoming-48.webp 48w, buddy-welcoming-96.webp 96w, buddy-welcoming-192.webp 192w, buddy-welcoming-384.webp 384w" sizes="{size}px" width="{size}" height="{size}" alt="Buddy"><figcaption>{size} px</figcaption></figure>'
html+='</div><div class="message"><img src="buddy-welcoming-96.webp" srcset="buddy-welcoming-48.webp 48w, buddy-welcoming-96.webp 96w, buddy-welcoming-192.webp 192w" sizes="48px" width="48" height="48" alt="Buddy"><div><b>Buddy</b><div>Here to help.</div></div></div><div class="row">'
for expression in EXPRESSIONS:
    html+=f'<figure><img src="buddy-{expression}-192.webp" srcset="buddy-{expression}-96.webp 96w, buddy-{expression}-192.webp 192w, buddy-{expression}-384.webp 384w" sizes="96px" width="96" height="96" alt="Buddy, {expression}"><figcaption>{expression.capitalize()}</figcaption></figure>'
(out/'index.html').write_text(html+'</div><p><a href="../presentation/face-front.blend">Editable front-facing scene</a> · <a href="../presentation/face-front.png">Transparent source PNG</a></p></main></html>')
