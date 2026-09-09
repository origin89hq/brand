"""Refresh the app preview from the native scene export, including configured mirrors."""
import base64,io,json
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
template=(ROOT/'source/reserve-alert.html').read_text()
with Image.open(ROOT/'app-scenes/buddy-reserve.png') as im:
    im.thumbnail((680,680));buf=io.BytesIO();im.save(buf,format='WEBP',quality=90)
fragment=template.replace('{{BUDDY_IMAGE}}','data:image/webp;base64,'+base64.b64encode(buf.getvalue()).decode())
assert len(fragment.encode())<1_000_000
(ROOT/'app-scenes/preview.html').write_text(fragment)
(ROOT/'app-scenes/index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Origin89 Offgrid / Reserve mode</title><style>:root{color-scheme:light dark}body{margin:0;padding:28px 10px;background:light-dark(#edf0f3,#111b29)}</style><body>'+fragment+'</body></html>')
config=ROOT/'source/preview-targets.json'
if config.exists():
    for value in json.loads(config.read_text()).get('inline_mirrors',[]):
        path=Path(value)
        if path.parent.exists():path.write_text(fragment)
print('APP_PREVIEW_REFRESHED',flush=True)
