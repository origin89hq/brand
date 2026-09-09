"""Rebuild native brand views and their image, guide and preview derivatives."""
import argparse,hashlib,json,os,shutil,subprocess,sys,time,runpy
from pathlib import Path
from buddy import blender,verify_base,check as check_base
from library_jobs import jobs

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
WEBSITE_BUILDERS=[REPO/'apps/website/scripts/prepare-website.mjs',REPO/'apps/website/design/react/prepare-assets.mjs']
WEBSITE_RECIPES=[*WEBSITE_BUILDERS,REPO/'apps/website/scripts/prepare-buddy-assets.mjs']
CACHE=ROOT/'.build/images';STATE=CACHE/'progress.json'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def relevant(path):return path.is_file() and not any(p in ('.build','__pycache__','node_modules') for p in path.relative_to(ROOT).parts)
def recipes():
    files=[p for p in sorted(ROOT.rglob('*')) if relevant(p) and p.suffix in ('.py','.mjs')]
    files.extend([ROOT/'buddy-source.json',*WEBSITE_RECIPES])
    return {os.path.relpath(p,ROOT):sha(p) for p in files}
def review_jobs():
    result=[]
    for name,view,layer,palette,frame in runpy.run_path(str(ROOT/'buddy/blender/review_jobs.py'))['RENDERS']:
        output=ROOT/f'buddy/renders/{name}.png'
        result.append({'name':'review-'+name,'script':str(ROOT/'buddy/blender/render_buddy.py'),'args':['--view',view,'--layer',layer,'--palette',palette,'--frame',str(frame),'--output',str(output),'--size','1200','--samples','192' if layer=='fur' else '80'],'outputs':[str(output),str(output.with_suffix('.json'))]})
    return result
def presentation_jobs():
    folder=ROOT/'buddy/presentation';plans=[]
    for look,expression,size in [('portrait',name,1920) for name in ('welcoming','playful','explaining','thinking','delighted','concerned','surprised')]+[('studio','welcoming',1600)]:
        stem=look+('' if expression=='welcoming' else '-'+expression)
        saved=expression=='welcoming'
        plans.append({'name':'presentation-'+stem,'script':str(folder/'render.py'),'args':['--look',look,'--expression',expression,'--size',str(size),'--samples','256']+(['--save'] if saved else []),'outputs':[str(folder/(stem+ext)) for ext in ('.png','.json')+(('.blend',) if saved else ())]})
    for look,expression,size in [('portrait',name,1920) for name in ('welcoming','explaining','thinking','delighted','concerned','surprised','playful')]+[('studio','welcoming',1600)]:
        stem=look+('' if expression=='welcoming' else '-'+expression)+'-transparent'
        saved=expression=='welcoming'
        plans.append({'name':'presentation-'+stem,'script':str(folder/'render_cutout.py'),'args':['--look',look,'--expression',expression,'--size',str(size),'--samples','256']+(['--save'] if saved else []),'outputs':[str(folder/(stem+ext)) for ext in ('.png','.json')+(('.blend',) if saved else ())]})
    plans.extend(avatar_jobs())
    return plans

def avatar_jobs():
    folder=ROOT/'buddy/presentation';plans=[]
    for expression in ('welcoming','explaining','thinking','delighted','concerned','surprised','playful'):
        stem='face-front'+('' if expression=='welcoming' else '-'+expression)
        plans.append({'name':'presentation-'+stem,'script':str(folder/'render_face.py'),'args':['--expression',expression,'--size','1920','--samples','256'],'outputs':[str(folder/(stem+ext)) for ext in ('.png','.json')]})
    return plans

def native_jobs():
    plans=[]
    for job in jobs():
        job=dict(job);job['outputs']=[str(ROOT/f'identity/renders/{job["name"]}.{ext}') for ext in ('png','json')];plans.append(job)
    # Review the actual chat crop before the larger portraits and pose library.
    order={'expression-playful-compact-transparent':-1,'expression-welcoming-compact-transparent':0,'buddy-avatar-transparent':1,'buddy-ready-transparent':2,'buddy-portrait-transparent':3,'expression-explaining-pose-transparent':4}
    plans.sort(key=lambda job:order.get(job['name'],4))
    for view,size,alpha in [('plate',1800,False),('tile',1800,False),('signature',2000,False),('icon',1024,False),('plate',1800,True),('tile',1800,True),('signature',2000,True)]:
        name=view+('-transparent' if alpha else '')
        plans.append({'name':name,'script':str(ROOT/'identity/blender/render_brand.py'),'args':['--view',view,'--size',str(size),'--samples','96']+(['--transparent'] if alpha else []),'outputs':[str(ROOT/f'identity/renders/{name}.{ext}') for ext in ('png','json')]})
    plans.extend(review_jobs())
    plans.extend(presentation_jobs())
    plans.append({'name':'reserve','script':str(ROOT/'situations/source/build_reserve_scene.py'),'args':[],'outputs':[str(ROOT/'situations/buddy-reserve.blend'),*[str(ROOT/f'situations/app-scenes/buddy-reserve.{ext}') for ext in ('png','json')]]})
    return plans

def execute(command,name,env=None):
    log=CACHE/(name+'.log');started=time.monotonic()
    print('BUILD',name,flush=True)
    with log.open('w') as output:
        result=subprocess.run(list(map(str,command)),stdout=output,stderr=subprocess.STDOUT,env=env)
    if result.returncode:raise RuntimeError(f'{name} failed: {log}\n'+log.read_text()[-2500:])
    print(f'DONE {name} ({time.monotonic()-started:.1f}s)',flush=True)

def check():
    check_base();record=json.loads((ROOT/'images.json').read_text())
    assert record['buddy_source_sha256']==verify_base(),'Character changed; rebuild images'
    assert record['recipes']==recipes(),'Image builders changed; rebuild images'
    for name,expected in record['outputs'].items():
        path=ROOT/name;assert path.is_file() and sha(path)==expected,f'Image derivative needs rebuilding: {name}'
    for name,expected in record.get('website_outputs',{}).items():
        path=REPO/name;assert path.is_file() and sha(path)==expected,f'Website Buddy asset needs rebuilding: {name}'
    assert record.get('website_outputs'),'Website export record missing; run pnpm brand:rebuild'
    print(f'CURRENT: {len(record["outputs"])} brand files and {len(record["website_outputs"])} website files match their rebuild record.')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--resume',action='store_true');parser.add_argument('--check',action='store_true');parser.add_argument('--native-only',action='store_true');parser.add_argument('--review-only',action='store_true');parser.add_argument('--compose-only',action='store_true',help='Refresh derivatives from existing native images after checking their source hashes.');args=parser.parse_args()
    if args.check:return check()
    CACHE.mkdir(parents=True,exist_ok=True);(ROOT/'identity/.build').mkdir(exist_ok=True)
    execute([blender(),'-b','--python-exit-code','1','--python',ROOT/'identity/blender/verify_scene.py'],'verify-identity')
    source_hash=verify_base();recipe=recipes()
    # Manual avatar-scene edits invalidate resumed avatar renders without making
    # review-only rebuilding depend on the presentation family.
    avatar_scene_sha=None if args.review_only else sha(ROOT/'buddy/presentation/face-front.blend')
    signature=hashlib.sha256(json.dumps({'source':source_hash,'identity':sha(ROOT/'identity/blender/origin89-brand.blend'),'recipes':recipe,'avatar_scene':avatar_scene_sha},sort_keys=True).encode()).hexdigest()
    state=json.loads(STATE.read_text()) if args.resume and STATE.exists() else {}
    if state.get('signature')!=signature:state={'signature':signature,'completed':{}}
    plans=review_jobs() if args.review_only else native_jobs()
    for i,job in enumerate([] if args.compose_only else plans,1):
        previous=state['completed'].get(job['name']);outputs=list(map(Path,job['outputs']))
        if previous and all(p.is_file() and previous.get(str(p.relative_to(ROOT)))==sha(p) for p in outputs):
            print(f'CURRENT {i}/{len(plans)} {job["name"]}',flush=True);continue
        execute([blender(),'-b','--python-exit-code','1','--python',job['script'],'--',*job['args']],f'{i:02}-{job["name"]}')
        assert verify_base()==source_hash,'Character changed during rebuild'
        state['completed'][job['name']]={str(p.relative_to(ROOT)):sha(p) for p in outputs}
        STATE.write_text(json.dumps(state,indent=2)+'\n')
    if args.native_only:return
    if not args.review_only:
        execute([sys.executable,ROOT/'buddy/avatar/build_avatar.py'],'buddy-avatars')
        execute([sys.executable,ROOT/'buddy/presentation/build_preview.py'],'buddy-presentation-review')
    execute([sys.executable,ROOT/'buddy/blender/compose_review.py'],'buddy-review')
    if args.review_only:return check_base()
    # Composition-only is useful after a targeted camera re-render. Preserve each
    # image's actual recipe metadata, and require every image to use this base.
    for job in native_jobs():
        for value in job['outputs']:
            output=Path(value)
            assert output.is_file(),f'Missing native output: {output}'
            if output.suffix!='.png':continue
            meta=json.loads(output.with_suffix('.json').read_text())
            expected=sha(ROOT/'identity/blender/origin89-brand.blend') if job['name'] in ('plate','tile','signature','icon','plate-transparent','tile-transparent','signature-transparent') else source_hash
            assert meta.get('source_sha256',meta.get('buddy_source_sha256'))==expected,f'Stale native image: {output}'
            if job['name'].startswith('presentation-'):
                assert meta['recipe_sha256']==sha(Path(job['script'])),f'Stale presentation recipe: {output}'
                assert meta['render_sha256']==sha(output),f'Presentation image changed: {output}'
                if 'scene_source_sha256' in meta:
                    assert meta['scene_source_sha256']==sha(ROOT/meta['scene_source']),f'Stale presentation source scene: {output}'
                if 'scene_sha256' in meta:
                    assert meta['scene_sha256']==sha(output.with_suffix('.blend')),f'Presentation scene changed: {output}'
    env=os.environ.copy();env.setdefault('O89_NODE_MODULES',str(ROOT.parents[1]/'apps/website/node_modules'))
    node=os.environ.get('NODE') or shutil.which('node')
    if not node:raise RuntimeError('Node.js is required for logo and icon PNG exports')
    execute([node,ROOT/'identity/source/export_tokens.mjs'],'tokens',env)
    execute([node,ROOT/'identity/source/export_assets.mjs'],'vector-images',env)
    for script,extra,name in [('export_ico.py',[],'icons'),('build_expression_board.py',[],'expression-sheet'),('build_expression_board.py',['--poses'],'pose-sheet'),('build_review.py',[],'character-board'),('build_guide.py',[],'guide')]:
        execute([sys.executable,ROOT/'identity/source'/script,*extra],name,env)
    execute([sys.executable,ROOT/'situations/source/build_preview.py'],'app-preview',env)
    execute([sys.executable,ROOT/'identity/source/verify_kit.py'],'verify-kit',env)
    for script in WEBSITE_BUILDERS:execute([node,script],'website-'+script.stem,env)
    check_base();assert recipes()==recipe,'Builders changed during rebuild'
    files=[p for folder in ('identity','buddy','situations/app-scenes') for p in (ROOT/folder).rglob('*') if relevant(p) and p.suffix in ('.png','.svg','.webp','.ico','.pdf','.json','.html','.md') and p.name!='MANIFEST.json']
    files.extend([ROOT/'situations/buddy-reserve.blend'])
    files.extend((ROOT/'buddy/presentation').glob('*.blend'))
    website_files=[REPO/'apps/website/src/react/generated/buddy.webp',*sorted((REPO/'apps/website/src/react/generated').glob('buddy-*')),REPO/'apps/website/design/generated/buddy.webp',*sorted((REPO/'apps/website/public/brand').glob('*'))]
    website_outputs={str(p.relative_to(REPO)):sha(p) for p in website_files if p.is_file()}
    (ROOT/'images.json').write_text(json.dumps({'schema':2,'website_outputs':website_outputs,'buddy_source_sha256':source_hash,'identity_source_sha256':sha(ROOT/'identity/blender/origin89-brand.blend'),'recipes':recipe,'outputs':{str(p.relative_to(ROOT)):sha(p) for p in sorted(set(files))}},indent=2)+'\n')
    from package_brand import included
    kit=ROOT/'identity';files=sorted(p for p in kit.rglob('*') if included(p) and p.name!='MANIFEST.json')
    (kit/'MANIFEST.json').write_text(json.dumps({'kit':'Origin89 / Plate 89','version':'1.0','shared_buddy':'../buddy-source.json','files':[{'path':str(p.relative_to(kit)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]},indent=2)+'\n')
    check()

if __name__=='__main__':main()
