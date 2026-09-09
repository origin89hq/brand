//! The Origin 89 palette, and the only place its values are written down.
//!
//! Two rules shape every entry here.
//!
//! **Names are semantic, not physical.** `--o89-warning`, never `--o89-ember`.
//! A physical name cannot survive a second theme: "ink" cannot mean near-white
//! on paper. This is not a stylistic preference — ember measures 2.12:1 on the
//! light ground the docs site already ships, so light mode is not a re-tint of
//! the dark theme, it is a second set of values behind the same names.
//!
//! **Colour is never the only channel.** Nominal green and alarm red are 60
//! apart in normal vision and about 13 apart under both protanopia and
//! deuteranopia — roughly one man in twelve cannot separate "running" from
//! "something is wrong" by hue. Every state below names the non-colour channel
//! that carries it when colour does not.
//!
//! Light values were solved, not chosen: hue held in OKLCh, lightness moved
//! until the value clears its floor. See `verify.mjs`, which re-measures all of
//! them and fails the build if one stops clearing.

/** The ground each theme's text is measured against. */
export const GROUNDS = {
  dark: '#07090c',
  light: '#fbfcfa',
}

/**
 * Every token, with the floor it has to clear.
 *
 * `check` is read by `verify.mjs`:
 *   'text'   ≥ 4.5:1 against the theme's ground — body copy and labels
 *   'ui'     ≥ 3.0:1 against the theme's ground — borders, rules, dividers
 *   'legend' the named counterpart must clear 4.5:1 against this fill
 *   'none'   a ground, or a value whose contrast is carried by something else
 */
export const TOKENS = [
  {
    name: 'page',
    dark: '#07090c',
    light: '#fbfcfa',
    check: 'none',
    why: 'The page itself. Near-black with a blue cast, not neutral grey — the bias is what keeps warning reading as heat. Not named "bg", because Tailwind would then spell the utility bg-bg.',
  },
  {
    name: 'surface',
    dark: '#0d1116',
    light: '#f1f3f0',
    check: 'none',
    why: 'A section that lifts off the page. Lighter than the page in dark mode, which is why it is not called "sunk".',
  },
  {
    name: 'surface-raised',
    dark: '#12171e',
    light: '#ffffff',
    check: 'none',
    why: 'A panel above the section: cards, reading tables, the things you look into.',
  },
  {
    name: 'line',
    dark: '#1e252e',
    light: '#dfe3e6',
    check: 'none',
    why: 'The quiet rule between rows. Deliberately below the UI floor — it separates, it does not inform.',
  },
  {
    name: 'line-strong',
    dark: '#2b343f',
    light: '#c4ccd2',
    check: 'none',
    why: 'A panel edge — structural, not informational, so it is exempt from the 3:1 floor that applies to a control boundary. Never use it to show focus; that is what --o89-focus is for, and this measures 1.58:1.',
  },
  {
    name: 'focus',
    dark: '#ffffff',
    light: '#2b4a97',
    check: 'ui',
    why: 'Focus goes achromatic on dark. The site currently rings a brand-green button in brand green, so the indicator is invisible on the one control that most needs it.',
  },

  {
    name: 'fg',
    dark: '#e7eaee',
    light: '#11161a',
    check: 'text',
    why: 'Body copy, and a Counted reading — a measurement we trust needs no colour at all.',
  },
  {
    name: 'muted',
    dark: '#9aa5b1',
    light: '#4b5761',
    check: 'text',
    why: 'Secondary copy, and a Stale reading, which pairs this with a dashed rule.',
  },
  {
    name: 'faint',
    dark: '#707b87',
    light: '#69747d',
    check: 'text',
    why: 'Eyebrows, captions, and a Missing reading. Lifted from #67727e, which measured 4.07:1 on ink and failed AA while carrying the one state that must never be mistaken for a number.',
  },

  {
    name: 'action',
    dark: '#2b4a97',
    light: '#2b4a97',
    check: 'legend',
    legend: 'on-fill',
    why: 'The P-89 structure plate the product is named after. One value in both themes, which no other candidate managed. The fill is 2.40:1 on ink and does not carry its own boundary — the rim does, which makes the rim a safety element rather than styling.',
  },
  {
    name: 'action-lit',
    dark: '#3f61b3',
    light: '#3f61b3',
    check: 'ui',
    why: 'Links, hover, and the focus ring. Also the fallback resting fill if the plate reads inert on real hardware.',
  },
  {
    name: 'link',
    dark: '#6279ad',
    light: '#2b4a97',
    check: 'text',
    why: 'Body-copy links, which need 4.5:1 and not the 3:1 a control boundary gets. The plate itself is 2.40:1 on the dark ground and action-lit only 3.39:1 — both fail as running text, which is why this is its own token rather than a reuse.',
  },
  {
    name: 'on-fill',
    dark: '#ffffff',
    light: '#ffffff',
    check: 'none',
    why: "The legend on any dark filled control — the plate, and the severe end of alarm. White in both themes because both fills stay dark in both themes. This is the plate's own legend: white on blue with a thin white rim.",
  },

  {
    name: 'nominal',
    dark: '#2f9d64',
    light: '#4c7d5f',
    check: 'text',
    why: 'Healthy. Was the brand and the action colour at once, which is why the eye had nothing to triage with. Now used at most once per screen, never as a fill, and never alone — it is 12.5 from alarm under protanopia.',
  },
  {
    name: 'warning',
    dark: '#e9a13c',
    light: '#9f6601',
    check: 'text',
    why: 'Watch this. The things that make heat.',
  },
  {
    name: 'nominal-deep',
    dark: '#168c54',
    light: '#4c7d5f',
    check: 'text',
    why: 'The shaded end of nominal, for a gradient terminus or a pressed state. Collapses onto the same value as nominal on paper, because a green dark enough to clear 4.5:1 there has nowhere further to go.',
  },
  {
    name: 'warning-deep',
    dark: '#b1721f',
    light: '#a26405',
    check: 'text',
    why: 'The shaded end of warning.',
  },
  {
    name: 'alarm',
    dark: '#e05a3c',
    light: '#ca4628',
    check: 'text',
    why: 'Something is wrong. A burnt signal red kept in the warning family so the two read as one instrument; a pure red would tear a hole in this palette.',
  },
  {
    name: 'alarm-deep',
    dark: '#a63b25',
    light: '#a63b25',
    check: 'legend',
    legend: 'on-fill',
    why: 'The severe end, and a fill rather than text. Its legend is white, not the theme foreground — this entry originally named fg and the gate caught it at 2.84:1 in light mode, which is exactly the label-polarity trap it was written to warn about.',
  },
  {
    name: 'info',
    dark: '#7fb0d4',
    light: '#487899',
    check: 'text',
    why: 'Derived rather than measured: an Estimated reading, which always carries a leading ≈ as well.',
  },
]

/** Neither theme touches these. They are objects in the world, not states. */
export const HERITAGE = [
  { name: 'mtq-green', value: '#04653a', why: 'The km-43 repère kilométrique.' },
  { name: 'mtq-green-lit', value: '#0a7d49', why: 'The same plate in daylight.' },
  { name: 'mtq-blue', value: '#2b4a97', why: 'The P-89 structure plate. Same value as action, deliberately: the control is the plate.' },
]

/**
 * A reading's quality, and the channel that carries it when colour cannot.
 *
 * The glyphs are not decoration. Strip them as clutter and Estimated becomes
 * unreadable for the operators the colour already fails.
 */
export const QUALITY = [
  { state: 'counted', token: 'fg', channel: 'solid rule', note: 'Measured. Shown plainly.' },
  { state: 'estimated', token: 'info', channel: 'leading ≈', note: 'Derived. The ≈ is mandatory.' },
  { state: 'stale', token: 'muted', channel: 'dashed rule + age', note: 'Last known, and how long ago.' },
  { state: 'missing', token: 'faint', channel: 'em-dashes', note: 'Never a number. A missing probe is not 0.0 °C.' },
]
