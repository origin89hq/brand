# @origin89/tokens

The palette, in one place, for all three surfaces: the controller UI, the
marketing site and the docs.

```
src/palette.mjs   the values, and why each one exists — the only source of truth
src/colour.mjs    WCAG contrast and OKLCh, so values can be solved and checked
build.mjs         emits tokens.css
verify.mjs        re-measures every token against the floor it claims
tokens.css        generated, committed, imported directly by an Astro site
```

```bash
node build.mjs && node verify.mjs
```

## Why the names are semantic

`--o89-warning`, never `--o89-ember`. A physical name cannot survive a second
theme — "ink" cannot mean near-white on paper.

This is not a style preference. Ember measures **2.12:1** on the light ground
the docs site already ships, and frost **2.25:1**. Neither survives a bright
background, so light mode is not a re-tint of the dark theme: it is a second set
of values behind the same names. Each light value was solved rather than chosen
— hue held in OKLCh, lightness moved until it cleared 4.5:1.

## Why colour is never the only channel

Nominal green and alarm red are ΔE 60 apart in normal vision and about **13**
apart under both protanopia and deuteranopia. For roughly one man in twelve,
"running" and "something is wrong" are the same colour.

So every reading state pairs its hue with something that survives that:

| State | Token | Non-colour channel |
|---|---|---|
| Counted | `--o89-fg` | solid rule |
| Estimated | `--o89-info` | leading `≈`, mandatory |
| Stale | `--o89-fg-muted` | dashed rule, and the age |
| Missing | `--o89-fg-faint` | em-dashes — **never a number** |

The `≈` and the dashes are part of the state. Strip them as clutter and
Estimated becomes unreadable for exactly the people the colour already fails.

## The plate

`--o89-action` is `#2b4a97`, the P-89 structure plate the product is named
after. Its fill is **2.40:1** against ink and deliberately does not carry its own
boundary — `--o89-action-rim` does. **The rim is a safety element, not
styling.** A control whose edge disappears is a control nobody presses.

The same value works in both themes, at 8.07:1 on paper, which no other
candidate managed without inventing a fourth value.

## Two constraints worth knowing before editing

**No `color-mix()`.** Tailwind 4's Lightning CSS pass silently mangles it when
an argument is a `var()` — it rewrote `color-mix(in srgb, var(--lens) 82%,
#ffffff)` down to `var(--lens)` and dropped the surrounding declarations
outright. Values here are literal for that reason.

**`verify.mjs` is the gate, and it has been watched failing.** Set `fg-faint`
back to `#67727e` — the value the site shipped — and it exits 1 at 4.07:1. If a
change here does not move that output, it did not do what you think.

`tokens.css` is generated and committed, so the generator has the acceptance
test this repo relies on elsewhere: reshape the code, run it, `git diff`. An
empty diff proves the change was pure shape.
