# Buddy equipment scout

Buddy has lowered compact blue binoculars and turned back toward the visitor.
His face remains visible, both hooves support the barrels, and two small grass
tufts suggest the field. Made for the Data page's “You don’t need to know where
to look” section.

- [Preview in the Data section](index.html)
- Editable Blender scene: `scene.blend`, generated locally by the command below
- [Transparent 1600 px PNG](buddy-equipment-scout.png)
- [Packaged 1280 px WebP](../../../art/buddy-equipment-scout-transparent.webp)
- [Source and render metadata](scene.json)

The scene derives from `buddy/blender/buddy.blend` and the approved materials
and lights in `buddy/presentation/face-front.blend`. Their hashes are checked
before and after rendering. Both inputs are preserved and tracked through Git
LFS. The generated `scene.blend` is ignored by Git. Its hash in `scene.json`
records which generated scene produced the committed render; package builds
consume the PNG and do not require that local Blender file.

## Rebuild

From the repository root:

```sh
# Fetch the two authored inputs if this clone skipped Git LFS downloads.
git lfs pull --include="buddy/blender/buddy.blend,buddy/presentation/face-front.blend" --exclude=""
blender -b --python-exit-code 1 --python situations/source/build_equipment_scout.py -- --size 1600 --samples 192
pnpm run build
pnpm run verify
```

For a quick review, append `--draft --size 720 --samples 32`; the outputs go to
ignored `.build/equipment-scout/`.

`scene.blend` has named binocular parts, a pose-control empty, flat woven strap
meshes, the Buddy armature, and an optional field-details collection containing
grass. It is a static pose. The animation
between scouting and greeting has not been authored.

The build recipe recreates this derivative. Put persistent pose or prop edits
in `situations/source/build_equipment_scout.py`. If you edit in Blender, save
that work as a separately named, tracked authored scene before rebuilding;
changes made only to the ignored `scene.blend` will not reach Git.
Shared changes to Buddy's geometry, rig and fur belong
in the canonical character source. The preview's copy and colors remain HTML
and CSS; no equipment records or words are baked into the illustration.

Use `@origin89/brand/art/buddy-equipment-scout-transparent.webp` in a consumer.
The package manifest records the rendered source and output hash.
