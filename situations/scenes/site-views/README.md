# Site views

The three sites of [site miniatures](../site-miniatures/README.md), seen wide from
the ground instead of from above a plinth: a cottage with a solar rack, a woodshed
generator and a propane tank; a telecom shelter with a lattice tower, a genset and
a fuel tank; and a mine utility with a Quonset building, a genset container, tanks
and a battery skid. The website's `/sites/` pages use them.

[`site_scenes.py`](../../source/site_scenes.py) models the equipment; both render
scripts build from it, so the two sets always show the same site.
[`build_site_views.py`](../../source/build_site_views.py) puts each one on an open
field under a perspective camera and renders it opaque. It reads no character,
hardware or image input.

The scenes follow the same rules as the miniatures, at night:

- Dark satin materials under a cool key, a blue rim and a low fill, with AgX
  Medium High Contrast. The sky is graded from near-black overhead to a faint blue
  at the horizon, and the ground fades into that horizon with distance.
- Blue emissive signal paths on the ground lead from the equipment to the building
  that holds the Controller.
- One green status light per site, on that building. The cottage windows glow warm.
- The equipment has no logos or model names, and no scene is a real installation.
- Terrain around the equipment is scattered from a fixed seed, and never between
  the camera and the site.

## Render

From the repository root, with Blender 5.2 on a Mac with a Metal GPU (the script
selects Metal devices):

```sh
blender --background --python-exit-code 1 --python situations/source/build_site_views.py
```

This writes `site-{cottage,telecom,mine}.png` (1536 × 1024, opaque, 160 samples),
an editable `site-*.blend` for each, and `render-source.json` to the ignored
`.build/site-views/`. Pass
`--out DIR` after `--` to choose the destination, `--only cottage telecom` to
render a subset, and `--samples 32 --scale 45` for a quick test render. Each scene
renders in about ten seconds.

Each site's camera is one entry in the script's `VIEWS`: where it looks, the
bearing it looks from, its height angle, its distance and its lens. Change a view
there rather than moving the equipment, which the miniatures share.

## On the website

The renders are made locally and not committed here; the website packages them:

```sh
blender --background --python-exit-code 1 --python situations/source/build_site_views.py -- \
  --out /tmp/site-views
```

The packager (`apps/website/scripts/site-art.mjs` in origin89hq/website) encodes
each render to `src/assets/art/{cottage,mining,telecom}.webp` and records its
SHA-256 against this repository's commit and the two scripts' hashes. The website
calls the mine site "mining".

`render-source.json` carries the sha256 of `site_scenes.py` and
`build_site_views.py` as they were when the renders were made. The packager
refuses a brand checkout whose scripts differ from it, so a record cannot
attribute renders to a checkout that did not produce them. Cycles output is not
reproducible run to run, so the scripts are the only thing a later run can
compare; re-rendering always changes the image bytes.
