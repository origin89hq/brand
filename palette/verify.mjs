//! The gate. Every token is re-measured against the floor it claims to clear,
//! in both themes, and the build fails if one stops clearing.
//!
//! This exists because the palette's light values were *solved* rather than
//! chosen, and a solved value is only trustworthy while somebody keeps checking
//! it. Change a hex in `palette.mjs` and this says so at the line that broke.
//!
//! Break it on purpose to see it work: set `fg-faint` back to `#67727e` and
//! watch the dark theme go red at 4.07:1. That is the value that shipped.

import { Colour } from './src/colour.mjs'
import { GROUNDS, TOKENS, HERITAGE, QUALITY } from './src/palette.mjs'

const FLOOR = { text: 4.5, ui: 3.0, legend: 4.5 }

const byName = new Map(TOKENS.map((t) => [t.name, t]))
const failures = []
const rows = []

for (const token of TOKENS) {
  if (token.check === 'none') continue

  for (const theme of ['dark', 'light']) {
    const ground = Colour.fromHex(GROUNDS[theme])
    const value = Colour.fromHex(token[theme])
    const floor = FLOOR[token.check]

    let ratio
    let against
    if (token.check === 'legend') {
      const legend = byName.get(token.legend)
      if (!legend) throw new Error(`${token.name} names a legend that does not exist: ${token.legend}`)
      ratio = value.contrastWith(Colour.fromHex(legend[theme]))
      against = `${token.legend} on it`
    } else {
      ratio = value.contrastWith(ground)
      against = `${theme} ground`
    }

    const ok = ratio >= floor
    if (!ok) failures.push({ token: token.name, theme, ratio, floor, against })
    rows.push({ token: token.name, theme, value: token[theme], ratio, floor, against, ok })
  }
}

const pad = (s, n) => String(s).padEnd(n)
const num = (n) => n.toFixed(2).padStart(5)

console.log('\nOrigin 89 tokens — contrast gate\n')
console.log(`  ${pad('token', 15)}${pad('theme', 7)}${pad('value', 10)}ratio   floor   against`)
console.log('  ' + '─'.repeat(74))
for (const r of rows) {
  console.log(
    `  ${pad(r.token, 15)}${pad(r.theme, 7)}${pad(r.value, 10)}${num(r.ratio)}   ${r.floor.toFixed(1)}     ${r.against}${r.ok ? '' : '   <-- FAILS'}`,
  )
}

// Not a pass/fail — a standing reminder of why every state carries a glyph or a
// rule as well as a hue. If these ever stop collapsing, the palette changed
// more than somebody intended.
console.log('\n  Colour is not sufficient on its own (CIEDE2000 is not needed to see it):')
const simulate = (colour, kind) => {
  const [r, g, b] = colour.rgb.map((c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  const lms = [
    17.8824 * r + 43.5161 * g + 4.11935 * b,
    3.45565 * r + 27.1554 * g + 3.86714 * b,
    0.0299566 * r + 0.184309 * g + 1.46709 * b,
  ]
  const [l, m, s] =
    kind === 'protanopia'
      ? [2.02344 * lms[1] - 2.52581 * lms[2], lms[1], lms[2]]
      : [lms[0], 0.494207 * lms[0] + 1.24827 * lms[2], lms[2]]
  return new Colour(
    [
      0.0809444479 * l - 0.130504409 * m + 0.116721066 * s,
      -0.0102485335 * l + 0.0540193266 * m - 0.113614708 * s,
      -0.000365296938 * l - 0.00412161469 * m + 0.693511405 * s,
    ].map((c) => (c <= 0.0031308 ? c * 12.92 : 1.055 * Math.max(0, c) ** (1 / 2.4) - 0.055)),
  )
}

const nominal = Colour.fromHex(byName.get('nominal').dark)
const alarm = Colour.fromHex(byName.get('alarm').dark)
for (const kind of ['protanopia', 'deuteranopia']) {
  const a = simulate(nominal, kind)
  const b = simulate(alarm, kind)
  console.log(
    `    nominal vs alarm under ${pad(kind, 14)} ${a.toHex()} vs ${b.toHex()} — this is why every state carries a glyph`,
  )
}

console.log('\n  Quality states and the channel that carries them without colour:')
for (const q of QUALITY) {
  console.log(`    ${pad(q.state, 11)}${pad('--o89-' + q.token, 18)}${q.channel}`)
}

console.log(`\n  ${TOKENS.length} tokens, ${HERITAGE.length} heritage values, ${rows.length} measurements.`)

if (failures.length) {
  console.error(`\n  ${failures.length} FAILED:`)
  for (const f of failures) {
    console.error(`    ${f.token} (${f.theme}) is ${f.ratio.toFixed(2)}:1 against ${f.against}, needs ${f.floor}`)
  }
  console.error()
  process.exit(1)
}

console.log('  All tokens clear their floor.\n')
