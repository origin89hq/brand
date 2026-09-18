# @origin89/brand

## 0.5.0

### Minor Changes

- 7f3a3dc: Add `tokens/plate.css`: the Plate 89 geometry as CSS, so consumers stop re-deriving it.
  
  It ships the chamfer and the layout custom properties (`--o89-cut`, `--o89-ease`, `--o89-max`, `--o89-gutter`), the plate button whose rim carries the control boundary the 2.40:1 fill cannot, the content column, the framed panel, the quiet text action, and the focus indicator. It reads colour from `themes.css` and defines none of its own, sets no font family, and contains no page layout.

## 0.4.0

### Minor Changes

- 37fc8da: Add `art/buddy-social.webp`, showing Buddy explaining from a blue chat bubble. Include the editable Blender scene, native props and branding, rebuild scripts, source hashes, and a GitHub-ready JPEG.
- 6d54a26: Add KM43 social artwork centered on the green kilometre-43 marker and the cottage shoreline, with the canonical Buddy canoeing farther out on the lake. Include an editable Blender scene with a live compositor, native canoe and fitted vest recipes, the reference-based lake plate, provenance, GitHub JPEG, and `art/km43-social.webp` export.
- e8b6f4d: Add the signal colour token and record the dark web surface language in the design guide.

### Patch Changes

- 32d9a52: Format the generated palette modules consistently with their source. Token values and asset exports are unchanged.

## 0.3.1

### Patch Changes

- 7c265a6: Include a changelog in the brand package and keep its generated manifest version
  in sync through Changesets release PRs.

## 0.3.0

### Minor Changes

- Add Buddy's equipment-scout pose with blue binoculars as
  `@origin89/brand/art/buddy-equipment-scout-transparent.webp`, with a native
  scene build script, render metadata, and a preview beside the Data page copy.
- Rebuild the derived scout Blender scene locally instead of storing it in
  Git LFS. Keep the authored character inputs and image exports.

## 0.2.0

### Minor Changes

- Add Buddy portraits, expressions, and avatars at web sizes to the brand package.

### Patch Changes

- Install image-build dependencies in CI before validating or publishing the package.
