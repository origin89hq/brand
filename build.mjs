//! Emits the package from the sources: `tokens/` from `palette/`; `logos/`,
//! `icons/` and `fonts/` copied out of `identity/`, which is where the kit is
//! made; and `brand.json`, which names the products, carries both colour themes
//! and the typography roles, and lists every shipped file with its SHA-256.
//!
//! The outputs are committed. Reshape this script, run it, `git diff`: an empty
//! diff proves the change was pure shape.
import { createHash } from "node:crypto";
import {
  cpSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const here = dirname(fileURLToPath(import.meta.url));
const out = process.argv[2] ? resolve(process.argv[2]) : here;
const sha256 = (path) => createHash("sha256").update(readFileSync(path)).digest("hex");
const list = (dir, keep) =>
  readdirSync(join(here, dir))
    .filter(keep)
    .sort()
    .map((f) => `${dir}/${f}`);

const copies = {
  tokens: [
    ["palette/tailwind.css", "tokens/tailwind.css"],
    ["palette/themes.css", "tokens/themes.css"],
    ["palette/src/palette.mjs", "tokens/palette.mjs"],
    ["palette/src/colour.mjs", "tokens/colour.mjs"],
  ],
  logos: list("identity/logos", (f) => f.endsWith(".svg")).map((f) => [
    f,
    f.replace(/^identity\//, ""),
  ]),
  icons: ["favicon.svg", "favicon.ico", "offgrid-flat-master.svg", "offgrid.ico"].map((f) => [
    `identity/icons/${f}`,
    `icons/${f}`,
  ]),
  fonts: list("identity/fonts", (f) => /\.(ttf|txt)$/.test(f)).map((f) => [
    f,
    f.replace(/^identity\//, ""),
  ]),
};
const shipped = {},
  manifest = {};
for (const [dir, pairs] of Object.entries(copies)) {
  rmSync(join(out, dir), { recursive: true, force: true });
  mkdirSync(join(out, dir), { recursive: true });
  shipped[dir] = [];
  manifest[dir] = [];
  for (const [from, to] of pairs) {
    cpSync(join(here, from), join(out, to));
    shipped[dir].push(to);
    manifest[dir].push({
      file: to,
      bytes: statSync(join(out, to)).size,
      sha256: sha256(join(out, to)),
      source: from,
    });
  }
}

// Buddy at web sizes. The Blender renders behind these are 66 MB of PNG, which
// no package should carry and no consumer wants; what a site actually needs is
// the largest size it displays. 1280 px for a portrait, 384 px for an avatar,
// webp because the same set as PNG is 31 MB rather than 3.
const expressions = [
  "welcoming",
  "explaining",
  "thinking",
  "delighted",
  "concerned",
  "surprised",
  "playful",
];
const stem = (e) => (e === "welcoming" ? "portrait" : `portrait-${e}`);
const situations = [
  [
    "situations/scenes/equipment-scout/buddy-equipment-scout.png",
    "art/buddy-equipment-scout-transparent.webp",
    1280,
  ],
];
const art = [
  ...expressions.flatMap((e) => [
    [`buddy/presentation/${stem(e)}.png`, `art/portrait-${e}.webp`, 1280],
    [`buddy/presentation/${stem(e)}-transparent.png`, `art/portrait-${e}-transparent.webp`, 1280],
    [`buddy/avatar/buddy-${e}.png`, `art/avatar-${e}.webp`, 384],
  ]),
  ["buddy/avatar/buddy-welcoming-round.png", "art/avatar-round.webp", 384],
  ["buddy/presentation/studio-transparent.png", "art/studio-transparent.webp", 1280],
  ...situations,
];
rmSync(join(out, "art"), { recursive: true, force: true });
mkdirSync(join(out, "art"), { recursive: true });
shipped.art = [];
manifest.art = [];
for (const [from, to, width] of art) {
  await sharp(join(here, from))
    .resize({ width, withoutEnlargement: true })
    .webp({ quality: 92, alphaQuality: 100, effort: 6 })
    .toFile(join(out, to));
  shipped.art.push(to);
  manifest.art.push({
    file: to,
    bytes: statSync(join(out, to)).size,
    sha256: sha256(join(out, to)),
    source: from,
  });
}
if (shipped.art.length !== expressions.length * 3 + 2 + situations.length)
  throw new Error("Buddy art set is incomplete");

const palette = JSON.parse(readFileSync(join(here, "identity/tokens/brand-tokens.json"), "utf8"));
const typography = {
  wordmark: {
    family: "Michroma",
    note: "The wordmark is optically weighted outlined artwork; use the logo files, typing the name does not recreate it.",
    files: ["fonts/Michroma-Regular.ttf"],
    licence: "fonts/Michroma-OFL.txt",
  },
  text: {
    family: "Inter Tight",
    weights: [400, 600, 700],
    files: [
      "fonts/InterTight-400.ttf",
      "fonts/InterTight-600.ttf",
      "fonts/InterTight-700.ttf",
      "fonts/InterTight-Variable.ttf",
    ],
    licence: "fonts/InterTight-OFL.txt",
  },
  data: {
    family: "IBM Plex Mono",
    files: ["fonts/IBMPlexMono-Regular.ttf"],
    licence: "fonts/IBMPlexMono-OFL.txt",
  },
};
for (const role of Object.values(typography))
  for (const f of [...role.files, role.licence])
    if (!shipped.fonts.includes(f)) throw new Error(`Font file not shipped: ${f}`);
if (!shipped.logos.includes("logos/plate-89-blue.svg")) throw new Error("Primary symbol missing");

const brand = {
  name: "Origin89",
  version: JSON.parse(readFileSync(join(here, "package.json"), "utf8")).version,
  names: {
    company: "Origin89",
    hardware: "Origin89 Controller",
    app: "Origin89 Offgrid",
    assistant: "Buddy",
    protocol: "KM43",
  },
  colour: {
    brand: palette.brand,
    themes: palette.themes,
    source: "palette/src/palette.mjs",
    snapshot: palette.snapshot_date,
  },
  typography,
  logos: { primarySymbol: "logos/plate-89-blue.svg", variants: shipped.logos },
  art: { expressions, portrait: 1280, avatar: 384, files: shipped.art },
  icons: { favicon: "icons/favicon.svg", offgrid: "icons/offgrid-flat-master.svg" },
  files: manifest,
  policy: "LICENSE.md",
};
writeFileSync(join(out, "brand.json"), JSON.stringify(brand, null, 2) + "\n");
console.log(
  `brand.json — ${Object.values(manifest).flat().length} files shipped, ${Object.keys(palette.themes).length} themes`,
);
