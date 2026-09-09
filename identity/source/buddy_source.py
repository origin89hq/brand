"""Resolve the single Buddy source for every scene and export in this bundle."""
import hashlib,json
from pathlib import Path
BRAND=Path(__file__).resolve().parents[2]
CONFIG=BRAND/'buddy-source.json'
def settings():
    return json.loads(CONFIG.read_text())
def master():
    path=BRAND/settings()['source']
    if not path.is_file():raise FileNotFoundError(f'Missing shared Buddy source: {path}')
    return path
def modules():return BRAND/settings()['modules']
def digest():return hashlib.sha256(master().read_bytes()).hexdigest()
def recipe_digest():
    """Include all native model/render code, so shader and camera edits invalidate PNGs."""
    paths=[CONFIG,Path(__file__),*sorted(modules().glob('*.py'))]
    paths+=sorted((BRAND/'identity/blender').glob('render_*.py'))
    h=hashlib.sha256()
    for p in paths:h.update(str(p.relative_to(BRAND)).encode());h.update(p.read_bytes())
    return h.hexdigest()
