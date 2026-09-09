"""Blender entrypoint: render the registered library in one Blender process."""
import json,runpy,sys
from pathlib import Path
plan=Path(sys.argv[sys.argv.index('--')+1]);jobs=json.loads(plan.read_text())
for i,job in enumerate(jobs,1):
    print(f'BUDDY_LIBRARY {i}/{len(jobs)} {job["name"]}',flush=True)
    sys.argv=[job['script'],'--',*job['args']]
    runpy.run_path(job['script'],run_name='__main__')
