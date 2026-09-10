# Buddy situations

Create each situation from [Buddy](../buddy/blender/buddy.blend):

```sh
python3 source/buddy.py new-scene reserve
```

This creates `situations/scenes/reserve/scene.blend` and a source record. Add the pose, props, camera and lighting there. Keep shared character geometry, fur and rig changes in the Buddy base.

## Equipment scout

[Data page preview](scenes/equipment-scout/index.html) · [Editable scene](scenes/equipment-scout/scene.blend) · [Rebuild instructions](scenes/equipment-scout/README.md)

Buddy holds lowered blue binoculars and looks back toward the visitor. The
native scene includes the binoculars, a neck strap, and optional grass details.
`source/build_equipment_scout.py` builds it from the shared character and
approved presentation scene. The package exports
`art/buddy-equipment-scout-transparent.webp`.

## Reserve

[App preview](app-scenes/index.html) · [Illustration](app-scenes/buddy-reserve.png) · [Editable scene](buddy-reserve.blend)

The website uses this illustration. Its metadata records the character and scene hashes used for rendering. `source/build_reserve_scene.py` contains the storage, umbrella and cloud construction and resolves the character through [buddy-source.json](../buddy-source.json).

Forecast, telemetry and proposed actions belong in application text. This illustration does not represent live controller state.
