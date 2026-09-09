# Origin89 / Plate 89 identity kit

[Asset browser](index.html) · [Design guide](guide/output/pdf/origin89-design-guide.pdf) · [Editable guide](guide/design-guide.md)

Logos, typography, icons and application artwork for the first version of Origin89. [Buddy](../buddy/README.md) supplies the shared character for new illustrations.

## Identity

| Role | Name |
| --- | --- |
| Company | Origin89 |
| Hardware | Origin89 Controller |
| App | Origin89 Offgrid |
| Assistant | Buddy |
| Protocol | KM43 |

The custom 89 plate is the primary symbol. Firmware is described as Origin89 Controller firmware.

## Files

- `logos/`: 23 outlined SVGs and corresponding transparent PNGs: horizontal, stacked, symbol, wordmark and product variants. Knockout versions contain transparent numerals.
- `icons/`: unmasked flat and 3D masters, raster sizes and favicons. Prefer flat artwork at small sizes.
- `fonts/`: Michroma, Inter Tight and IBM Plex Mono, with their OFL licenses.
- `tokens/`: CSS/JSON palette values and contrast ratios. The repository palette source is `packages/tokens/src/palette.mjs`.
- `source/geometry.json`: editable plate and outlined wordmark geometry shared by SVG and Blender construction.
- `blender/origin89-brand.blend`: editable plate, tile, icon and signature studio.
- `renders/` and `applications/`: kit imagery and placement examples, with provenance where available.
- `guide/`: 20-page PDF, Markdown source and cover.
- `source/`: vector, raster, PDF, token and packaging builders.
- `MANIFEST.json`: inventory of this kit.

## Editing identity assets

`source/build_vectors.py` builds the plate, custom 89 and optically adjusted outlined Michroma wordmark. Inter Tight supplies other text. Run identity builders from this kit directory:

```sh
python3 source/build_vectors.py
node source/export_assets.mjs
python3 source/export_ico.py
```

Keep the existing logo proportions and platform icon requirements. The beveled tile is presentation art; use the unmasked icon master for app packaging. The guide contains clear-space and minimum-size specifications.

Python dependencies are listed in `source/requirements.txt`; Node dependencies are in `source/package.json`. Use `O89_NODE_MODULES` to point the exporters at an existing Sharp installation. Guide and review builders require their illustration inputs and Poppler.

## References and maintenance

The [editable logo geometry](source/geometry.json) defines the plate and outlined wordmark. Character construction and references are documented in [Buddy](../buddy/README.md). Run `pnpm brand:rebuild` from the repository root to rebuild the complete shared library and website assets.

Keep font licenses with redistributed binaries. Temporary work belongs in ignored `.build/` folders. Extend the shared [Buddy source](../buddy/blender/buddy.blend) for character work.
