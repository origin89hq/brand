"""Read-only audit of the independent plate, tile, icon and signature studio."""
from pathlib import Path
import bpy,json,hashlib
ROOT=Path(__file__).resolve().parents[1];source=ROOT/'blender/origin89-brand.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
expected={'01 | Plate studio','02 | Offgrid tile','03 | Offgrid icon master','05 | Origin89 signature'}
assert set(bpy.data.scenes.keys())==expected
assert all(scene.camera for scene in bpy.data.scenes)
assert json.loads(bpy.data.texts['geometry.json | vector source snapshot'].as_string())==json.loads((ROOT/'source/geometry.json').read_text())
assert not any(obj.type=='ARMATURE' for obj in bpy.data.objects)
external=[im.filepath for im in bpy.data.images if im.source=='FILE' and not im.packed_file]
assert not external,external
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'scenes':sorted(expected),'embedded_geometry_matches':True,'external_images':external}
(ROOT/'.build').mkdir(exist_ok=True);(ROOT/'.build/blender-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
