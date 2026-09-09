# Buddy presentation library

Large portraits and full-body images are transparent by default. Small avatars keep their green circular background. All versions share the approved lighting, focused eyes and original soft coat.

- `portrait-transparent.blend` / `portrait-transparent.png`: the default close portrait for websites and compositing.
- `portrait-{expression}-transparent.png`: six additional expressions with native alpha coverage.
- `studio-transparent.blend` / `studio-transparent.png`: the complete character, including antlers and feet, for scene integration.
- `face-front.blend`: the authored source for all front-facing avatars; edit its camera, lights, materials, and greeting controls directly.
- `face-front.png` / `face-front-{expression}.png`: transparent render outputs used to generate the [circular avatars](../avatar/).
- `portrait.blend` / `portrait.png`: an optional wider portrait in the green studio.
- `studio.blend` / `studio.png`: an optional composed scene with a warm background and contact shadow.

The default is a gentle smile with the tongue tucked in. The portrait intentionally crops the outer antlers; use the full-body cutout when the whole silhouette is needed. All five editable scenes derive from `../blender/buddy.blend`, the canonical character source.

`render.py` creates the approved studio scenes. `render_cutout.py` uses their materials, camera and lighting, evaluates each expression from the canonical rig, and hides the backdrop only from camera rays. Transparency comes from Cycles, including soft hair coverage; there is no background removal step.

`render_face.py` reads `face-front.blend` without saving or replacing it. The saved greeting controls are preserved; the other six expressions use canonical rig presets while retaining the authored camera, lights, materials, and head/ear pose. `face-front-source.json` records which canonical model the editable scene derives from. If that model changes, rebase the avatar scene on it and update the lineage record before rendering.

Run `pnpm brand:avatars` after saving manual edits to `face-front.blend`. It refreshes the seven avatar expressions and derivatives without overwriting the input scene. Run `pnpm brand:presentation` to rebuild all studio, transparent, and avatar outputs, then refresh their website derivatives, review and guide. Use `pnpm brand:rebuild` after editing the character, or `pnpm brand:export` after crop or document edits. Metadata records the model, recipe, source scene, expression and output hashes.

`BuddyAvatar` selects a green circle at 96 px and below and a transparent portrait above that size. `framing="scene"` explicitly requests a composed green portrait. `build_preview.py` provides responsive WebPs and a review with selectable page backgrounds. Use the editable model and adapt its lighting when placing Buddy in a new 3D scene.

To check source preservation, run Blender in background mode with `--python-exit-code 1 --python docs/brand/buddy/presentation/verify_face_source.py`. The regression renders a temporary edited copy and checks that camera, lighting, and greeting edits survive without changing either source file.
