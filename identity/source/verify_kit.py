"""Check delivered files and render provenance, without modifying artifacts."""
from pathlib import Path
from buddy_source import digest
import hashlib,json,re,xml.etree.ElementTree as ET
from PIL import Image
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
logos=list((ROOT/'logos').glob('*.svg'));assert len(logos)==23
for file in logos:
    tree=ET.parse(file);elements=list(tree.getroot().iter())
    assert any(e.tag.endswith('path') for e in elements)
    assert not any(e.tag.endswith('text') or e.tag.endswith('image') for e in elements)
    assert 'NaN' not in file.read_text()
pngs=list(ROOT.rglob('*.png'));checked=0
for file in pngs:
    if '.build' in file.parts:continue
    with Image.open(file) as im:im.verify()
    checked+=1
blend_hash=hashlib.sha256((ROOT/'blender/origin89-brand.blend').read_bytes()).hexdigest()
for file in (ROOT/'renders').glob('*.json'):
    meta=json.loads(file.read_text());expected=digest() if file.stem.startswith(('buddy-','expression-')) else blend_hash
    assert meta['source_sha256']==expected,file
    im=Image.open(file.with_suffix('.png'));assert list(im.size)==meta['size'],file
    if meta['transparent']:
        assert im.mode=='RGBA' and im.getchannel('A').getextrema()==(0,255),file
    else:assert im.convert('RGBA').getchannel('A').getextrema()==(255,255),file
for file in (ROOT/'icons').glob('offgrid-*.png'):
    size=int(file.stem.split('-')[-1]);im=Image.open(file);assert im.size==(size,size)
    assert im.convert('RGBA').getchannel('A').getextrema()==(255,255)
pdf=PdfReader(ROOT/'guide/output/pdf/origin89-design-guide.pdf');assert len(pdf.pages)==20
all_text='\n'.join(page.extract_text() for page in pdf.pages)
for name in ['Origin89','Controller','Offgrid','Buddy','KM43']:assert name in all_text,name
assert 'not a skinned animation rig' not in all_text
assert 'cloven hooves' in all_text and '22-bone rig' in all_text
assert not any(stale in all_text for stale in ('paddle','57-bone','four stylized digits'))
html=(ROOT/'index.html').read_text()
missing=[]
for href in re.findall(r'(?:src|href)="([^"]+)"',html):
    if href.startswith(('#','http','data:')):continue
    if not (ROOT/href).is_file():missing.append(href)
assert not missing,missing
for file in (ROOT/'applications').glob('*.json'):
    meta=json.loads(file.read_text())
    if 'source_sha256' in meta:assert meta['source_sha256']==digest(),file
report={'outlined_svg_logos':len(logos),'valid_png_files':checked,'pdf_pages':len(pdf.pages),'plate_source_sha256':blend_hash,'buddy_source_sha256':digest(),'missing_preview_links':missing}
(ROOT/'.build/kit-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
