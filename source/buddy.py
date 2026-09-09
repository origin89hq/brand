"""Validate, render, or explicitly regenerate the single editable Buddy source."""
import argparse,hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def settings():return json.loads((ROOT/'buddy-source.json').read_text())
def source():return ROOT/settings()['source']
def blender():
    found=os.environ.get('BLENDER') or shutil.which('blender')
    default=Path('/Applications/Blender.app/Contents/MacOS/Blender')
    if not found and default.is_file():found=str(default)
    if not found:raise ValueError('Install Blender or set BLENDER to its executable.')
    return found
def native(script,args=(),label=None):
    log=ROOT/'.build'/((label or Path(script).stem)+'.log');log.parent.mkdir(parents=True,exist_ok=True)
    print('BUILD',label or Path(script).stem,flush=True)
    with log.open('w') as output:
        result=subprocess.run([blender(),'-b','--python-exit-code','1','--python',str(script),'--',*map(str,args)],stdout=output,stderr=subprocess.STDOUT)
    if result.returncode:raise ValueError(f'{script} failed; see {log}\n'+log.read_text()[-1800:])
def verify_base():
    config=settings();sha=digest(source())
    for name in config['validation']:
        report=json.loads((ROOT/name).read_text())
        if report['source_sha256']!=sha or not report['passed'] or not all(c['passed'] for c in report['checks'].values()):
            raise ValueError('Buddy needs validation. Run pnpm brand:rebuild or python3 source/buddy.py validate.')
    return sha
def check():
    sha=verify_base();config=settings();path=ROOT/config['review'];review=json.loads(path.read_text())
    if review['source_sha256']!=sha:raise ValueError('Buddy review is stale; run pnpm brand:rebuild.')
    for name,expected in review['files'].items():
        file=path.parent/name
        if not file.is_file() or digest(file)!=expected:raise ValueError(f'Buddy review needs rebuilding: {file}')
    checks=sum(len(json.loads((ROOT/name).read_text())['checks']) for name in config['validation'])
    print(f'CURRENT: Buddy the {config["species"]}; {checks} native checks; source {sha}')
    return sha
def validate():
    sha=digest(source());modules=ROOT/settings()['modules']
    for script in ('verify_buddy.py','verify_facial.py'):native(modules/script)
    if digest(source())!=sha:raise ValueError('Buddy changed during validation; rerun.')
    verify_base()
def setup():
    folder=ROOT/'.build/python'
    if not (folder/'bin/python3').exists():subprocess.run([sys.executable,'-m','venv',str(folder)],check=True)
    subprocess.run([str(folder/'bin/python3'),'-m','pip','install','-r',str(ROOT/'identity/source/requirements.txt')],check=True)
    if not shutil.which('pdftoppm'):raise ValueError('Install Poppler (macOS: brew install poppler).')
    blender();print('Brand tools ready. Run pnpm brand:rebuild.')
def render_python():
    for candidate in (os.environ.get('BRAND_PYTHON'),str(ROOT/'.build/python/bin/python3'),sys.executable):
        if not candidate or not Path(candidate).exists():continue
        result=subprocess.run([candidate,'-c','import PIL,reportlab,pypdf'],capture_output=True)
        if result.returncode==0:return candidate
    raise ValueError('Install the brand Python dependencies once: pnpm brand:setup')
def presentation():
    verify_base()
    from rebuild_images import presentation_jobs
    for job in presentation_jobs():native(Path(job['script']),job['args'],job['name'])
    export()
def avatars():
    verify_base()
    from rebuild_images import avatar_jobs
    for job in avatar_jobs():native(Path(job['script']),job['args'],job['name'])
    export()
def export():
    verify_base()
    subprocess.run([render_python(),str(ROOT/'source/rebuild_images.py'),'--compose-only'],check=True)
def model():
    backup=ROOT/'.build/buddy-before-model.blend';backup.parent.mkdir(parents=True,exist_ok=True)
    if source().exists():shutil.copy2(source(),backup)
    native(ROOT/settings()['modules']/'build_buddy.py')
    validate();print('Editable model rebuilt. Run pnpm brand:rebuild to refresh all images.')
def new_scene(name,dry_run=False):
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,63}',name):raise ValueError('Use a lowercase scene name with letters, digits and hyphens.')
    sha=verify_base();config=settings();folder=ROOT/config['situations']/name
    if folder.exists():raise ValueError(f'Scene already exists: {folder}')
    if dry_run:print(f'Would copy {source()} to {folder}/scene.blend');return
    folder.mkdir(parents=True);shutil.copy2(source(),folder/'scene.blend')
    (folder/'scene.json').write_text(json.dumps({'base':config['source'],'base_sha256':sha,'source':'scene.blend','scene':config['scene']},indent=2)+'\n')
    print('Created',folder/'scene.blend')
def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    for command in ('check','validate','render','model','setup','rebuild','export','presentation','avatars'):commands.add_parser(command)
    scene=commands.add_parser('new-scene');scene.add_argument('name');scene.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    try:
        if args.command=='check':
            from rebuild_images import check as check_images
            check_images()
        elif args.command in ('rebuild','render'):
            python=render_python();validate()
            subprocess.run([python,str(ROOT/'source/rebuild_images.py'),'--resume',*(['--review-only'] if args.command=='render' else [])],check=True)
        elif args.command=='new-scene':new_scene(args.name,args.dry_run)
        else:globals()[args.command]()
    except (ValueError,OSError,KeyError,AssertionError,subprocess.CalledProcessError) as error:parser.exit(1,str(error)+'\n')
if __name__=='__main__':main()
