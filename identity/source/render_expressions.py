"""Render Buddy's six expressions from a saved Blender source."""
import argparse,os,shutil,subprocess
from buddy_source import master
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--file',type=Path,default=master())
p.add_argument('--output-dir',type=Path,default=ROOT/'renders')
p.add_argument('--size',type=int,default=1200);p.add_argument('--samples',type=int,default=96)
p.add_argument('--full-body',action='store_true');p.add_argument('--transparent',action='store_true')
a=p.parse_args();blender=os.environ.get('BLENDER') or shutil.which('blender')
if not blender:raise SystemExit('Set BLENDER to the installed executable.')
for name in ('welcoming','explaining','thinking','delighted','concerned','surprised'):
    view='buddy-ready' if a.full_body else 'buddy-portrait'
    suffix='-pose' if a.full_body else ''
    if a.transparent:suffix+='-transparent'
    command=[blender,'--background','--python-exit-code','1','--python',str(ROOT/'blender/render_brand.py'),'--','--file',str(a.file.resolve()),'--view',view,'--expression',name,'--size',str(a.size),'--samples',str(a.samples),'--output',str(a.output_dir/f'expression-{name}{suffix}.png')]
    if a.transparent:command.append('--transparent')
    subprocess.run(command,check=True)
