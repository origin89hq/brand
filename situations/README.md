# Buddy situations

Create each situation from [Buddy](../buddy/blender/buddy.blend):

```sh
python3 docs/brand/source/buddy.py new-scene reserve
```

This creates `scenes/reserve/scene.blend` and a source record. Add the pose, props, camera and lighting there. Keep shared character geometry, fur and rig changes in the Buddy base.

## Reserve

[App preview](app-scenes/index.html) · [Illustration](app-scenes/buddy-reserve.png) · [Editable scene](buddy-reserve.blend)

The website uses this illustration. Its metadata records the character and scene hashes used for rendering. `source/build_reserve_scene.py` contains the storage, umbrella and cloud construction and resolves the character through [buddy-source.json](../buddy-source.json).

Forecast, telemetry and proposed actions belong in application text. This illustration does not represent live controller state.
