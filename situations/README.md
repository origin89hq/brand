# Buddy situations

Create each situation from [Buddy](../buddy/blender/buddy.blend):

```sh
python3 source/buddy.py new-scene reserve
```

This creates `situations/scenes/reserve/scene.blend` and a source record. Add the pose, props, camera and lighting there. Keep shared character geometry, fur and rig changes in the Buddy base.

## Equipment scout

[Data page preview](scenes/equipment-scout/index.html) · [Rebuild the editable scene](scenes/equipment-scout/README.md)

Buddy holds lowered blue binoculars and looks back toward the visitor. The
native scene includes the binoculars, a neck strap, and optional grass details.
`source/build_equipment_scout.py` builds it from the shared character and
approved presentation scene. The generated `scene.blend` is ignored by Git;
the recipe, render metadata and image exports are tracked. The package exports
`art/buddy-equipment-scout-transparent.webp`.

## KM43 canoe

[Social artwork](scenes/km43-canoe/km43-social.jpg) · [Editable scene and rebuild instructions](scenes/km43-canoe/README.md)

The green kilometre-43 marker and cottage shoreline lead the scene, with the
canonical Buddy paddling a cedar canoe farther out on the lake.
The character, canoe, paddle, life vest, lighting, and water reflection are native
Blender elements. The cottage-inspired lake and marker are a packed generated
background plate. The package exports `art/km43-social.webp`.

## Reserve

[App preview](app-scenes/index.html) · [Illustration](app-scenes/buddy-reserve.png) · [Editable scene](buddy-reserve.blend)

The website uses this illustration. Its metadata records the character and scene hashes used for rendering. `source/build_reserve_scene.py` contains the storage, umbrella and cloud construction and resolves the character through [buddy-source.json](../buddy-source.json).

Forecast, telemetry and proposed actions belong in application text. This illustration does not represent live controller state.
