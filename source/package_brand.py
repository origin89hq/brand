"""Package the brand library with source paths intact; verify ZIP CRCs."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def included(path):
    return path.is_file() and not any(part in ('.build','node_modules','__pycache__') for part in path.relative_to(ROOT).parts) and path.suffix not in ('.blend1','.blend2','.pyc') and path.name!='.DS_Store'

def inventory():
    files=[]
    for folder in ('identity','buddy','situations','source'):
        files.extend(p for p in (ROOT/folder).rglob('*') if included(p))
    files.extend(ROOT/name for name in ('README.md','CLEANUP.md','.gitignore','buddy-source.json','index.html'))
    return sorted(set(files))

def package(dry_run=False):
    files=inventory();dest=ROOT/'origin89-brand-kit.zip'
    if dry_run:
        print(f'Would package {len(files)} files into {dest}');return [dest]
    kit=ROOT/'identity';assets=sorted(p for p in kit.rglob('*') if included(p) and p.name!='MANIFEST.json')
    (kit/'MANIFEST.json').write_text(json.dumps({'kit':'Origin89 / Plate 89','version':'1.0','shared_buddy':'../buddy-source.json','files':[{'path':str(p.relative_to(kit)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in assets]},indent=2)+'\n')
    temp=dest.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
        for path in inventory():bundle.write(path,str(Path('origin89-brand-kit')/path.relative_to(ROOT)))
    with zipfile.ZipFile(temp) as bundle:
        bad=bundle.testzip()
        if bad:raise RuntimeError('ZIP CRC failed: '+bad)
    temp.replace(dest);print(f'Packaged {dest} ({dest.stat().st_size} bytes)');return [dest]

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--dry-run',action='store_true')
    package(parser.parse_args().dry_run)
