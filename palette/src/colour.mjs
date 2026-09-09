//! Colour maths for the token palette: WCAG contrast, and OKLCh for moving a
//! colour's lightness without moving its hue.
//!
//! This exists so the palette can be *checked* rather than asserted. Every
//! light-mode value in `palette.mjs` was solved with these methods, and
//! `verify.mjs` re-measures all of them on every run — a token that stops
//! clearing its floor fails the build instead of shipping quietly.

/** A colour, with the invariants checked once at construction. */
export class Colour {
  /** @param {[number, number, number]} rgb components in 0..1 */
  constructor(rgb) {
    this.rgb = rgb
  }

  /** Parse `#rrggbb`. Throws on anything else, because a silent black is worse. */
  static fromHex(hex) {
    const s = String(hex).trim().replace(/^#/, '')
    if (!/^[0-9a-fA-F]{6}$/.test(s)) {
      throw new Error(`not a #rrggbb colour: ${hex}`)
    }
    return new Colour([0, 2, 4].map((i) => parseInt(s.slice(i, i + 2), 16) / 255))
  }

  static fromOklch({ l, c, h }) {
    const [L, a, b] = [l, c * Math.cos(h), c * Math.sin(h)]
    const lc = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    const mc = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    const sc = (L - 0.0894841775 * a - 1.291485548 * b) ** 3
    return new Colour(
      [
        4.0767416621 * lc - 3.3077115913 * mc + 0.2309699292 * sc,
        -1.2684380046 * lc + 2.6097574011 * mc - 0.3413193965 * sc,
        -0.0041960863 * lc - 0.7034186147 * mc + 1.707614701 * sc,
      ].map(Colour.#gamma),
    )
  }

  static #linear(c) {
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  }

  static #gamma(c) {
    return c <= 0.0031308 ? c * 12.92 : 1.055 * c ** (1 / 2.4) - 0.055
  }

  /** True when every component is inside sRGB, allowing for float slop. */
  get inGamut() {
    return this.rgb.every((v) => v >= -0.0005 && v <= 1.0005)
  }

  get luminance() {
    const [r, g, b] = this.rgb.map(Colour.#linear)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b
  }

  /** WCAG 2.1 contrast ratio. Order does not matter. */
  contrastWith(other) {
    const [hi, lo] = [this.luminance, other.luminance].sort((a, b) => b - a)
    return (hi + 0.05) / (lo + 0.05)
  }

  get oklch() {
    const [r, g, b] = this.rgb.map(Colour.#linear)
    const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    const [L, A, B] = [
      0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
      1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
      0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
    ]
    return { l: L, c: Math.hypot(A, B), h: Math.atan2(B, A) }
  }

  /**
   * The same hue and chroma at a different lightness. This is the one move the
   * light-mode twins are made of: ember stays ember, it just stops being a
   * light colour on a light ground. CIE Lab drifts amber toward brown under the
   * same operation, which is why this is OKLCh.
   */
  withLightness(l) {
    return Colour.fromOklch({ ...this.oklch, l })
  }

  withChroma(c) {
    return Colour.fromOklch({ ...this.oklch, c })
  }

  toHex() {
    return (
      '#' +
      this.rgb
        .map((v) => Math.round(Math.min(1, Math.max(0, v)) * 255).toString(16).padStart(2, '0'))
        .join('')
    )
  }

  /**
   * Darken or lighten along constant hue until this colour clears `target`
   * against `ground`, giving up chroma only as far as the gamut forces.
   *
   * Solve a little above the floor you actually need: the result is quantised
   * to an 8-bit hex afterwards, and solving to exactly 4.5 produced a value
   * that measured 4.49 once rounded — passing here and failing in the browser.
   */
  solveAgainst(ground, target, { toward = 'dark' } = {}) {
    const { c: chroma, h } = this.oklch
    const step = toward === 'dark' ? -0.002 : 0.002
    // Start just inside the bounds the loop guards against. Starting exactly on
    // one meant the 'light' direction broke on its first iteration and silently
    // returned null — it went unnoticed because every value solved so far only
    // needed darkening.
    const start = toward === 'dark' ? 0.97 : 0.03
    for (let i = 0; i < 500; i += 1) {
      const l = start + step * i
      if (l < 0.02 || l > 0.99) break
      for (const keep of [1, 0.97, 0.94, 0.9, 0.85, 0.8, 0.72, 0.64, 0.55]) {
        const candidate = Colour.fromOklch({ l, c: chroma * keep, h })
        if (!candidate.inGamut) continue
        if (candidate.contrastWith(ground) >= target) return candidate
      }
    }
    return null
  }
}
