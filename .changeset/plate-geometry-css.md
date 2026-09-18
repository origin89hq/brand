---
"@origin89/brand": minor
---

Add `tokens/plate.css`: the Plate 89 geometry as CSS, so consumers stop re-deriving it.

It ships the chamfer and the layout custom properties (`--o89-cut`, `--o89-ease`, `--o89-max`, `--o89-gutter`), the plate button whose rim carries the control boundary the 2.40:1 fill cannot, the content column, the framed panel, the quiet text action, and the focus indicator. It reads colour from `themes.css` and defines none of its own, sets no font family, and contains no page layout.
