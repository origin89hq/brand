# Site miniatures

Three generic sites on dark plinths for the website's homepage: a cottage with a
solar rack, a woodshed generator and a propane tank; a telecom shelter with a
lattice tower, a genset and a fuel tank; and a mine utility with a Quonset
building, a genset container, tanks and a battery skid.
[`site_scenes.py`](../../source/site_scenes.py) models each scene from primitives
in an empty Blender file and
[`build_site_miniatures.py`](../../source/build_site_miniatures.py) renders it.
Neither reads character, hardware or image input.
[Site views](../site-views/README.md) render the same models wide, from the
ground, for the website's `/sites/` pages.

The scenes follow the design guide's product studio and site miniatures rules
([`identity/guide/design-guide.md`](../../../identity/guide/design-guide.md)):

- Dark satin materials on a charcoal plinth, under a soft warm key, a blue rim and
  a fill, with an orthographic camera and AgX Medium High Contrast.
- Blue emissive signal paths on the ground lead from the equipment to the
  building that holds the Controller.
- One green status light per site, on that building. The cottage windows glow
  warm.
- The equipment has no logos or model names.

## Render

From the repository root, with Blender 5.2 on a Mac with a Metal GPU (the
script selects Metal devices):

```sh
blender --background --python-exit-code 1 --python situations/source/build_site_miniatures.py
```

This writes `audience-{cottage,telecom,mine}.png` (1400 × 1100, transparent,
128 samples), `audience-*-signals.json` and an editable `audience-*.blend` for
each to the ignored `.build/site-miniatures/`. The JSON holds every signal path
projected through the render camera, in the render's pixels, ordered from the
equipment to the building. Pass `--out DIR` after `--` to choose the
destination, `--only cottage telecom` to render a subset and `--samples 32` for a
quick test render. Each scene renders in seconds.

## On the website

The renders are made locally and not committed here; the website packages them.
Render into the directory its packager reads, beside the Controller renders from
origin89hq/hardware:

```sh
blender --background --python-exit-code 1 --python situations/source/build_site_miniatures.py -- \
  --out /tmp/home-media/dioramas
```

The packager (`apps/website/scripts/package-home-media.mjs` in origin89hq/website)
crops each render to its alpha bounds (alpha > 8) plus 30 px, clamped to the
frame, writes `audience-3d-{cottage,telecom,mine}.webp` with the signal paths
shifted into the crop (`audience-3d-*-signals.json`), and records each file's
SHA-256 with this script as its source. The homepage runs light pulses along
those paths over the image. Its `--only dioramas` option repackages
the miniatures without the Controller renders.
