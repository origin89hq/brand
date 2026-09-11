# @origin89/brand

## 0.4.0

### Minor Changes

- 6d54a26: Add KM43 social artwork centered on the green kilometre-43 marker and the cottage shoreline, with the canonical Buddy canoeing farther out on the lake. Include an editable Blender scene with a live compositor, native canoe and fitted vest recipes, the reference-based lake plate, provenance, GitHub JPEG, and `art/km43-social.webp` export.

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
