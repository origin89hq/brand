---
"@origin89/brand": minor
---

Ship the site chrome as `tokens/chrome.css`: the floating navigation bar and the footer, taken from origin89.com, which is the reference for how the chrome looks.

Both it and the dataset site carried this — sixteen shared selectors, ten identical once the two token spellings are read as the same value. How the bar collapses on a narrow window stays with each site, because the two answer it differently.

The bar's translucent ground and its hairline are mixed from `themes.css` rather than written down again: the ground is exactly halfway between `--color-page` and `--color-surface` at four fifths, which is the `rgb(10 13 17)` both sites had reached by hand. The current-page mark honours `aria-current="page"` as well as `data-current`.
