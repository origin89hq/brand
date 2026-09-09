//! Emits the generated half of the package: `tokens/` from `palette/`, and
//! `brand.json`, which names the products, carries both colour themes and the
//! typography roles, and lists every shipped file with its SHA-256. The logos,
//! icons and fonts are not generated; they are the sources, shipped as they are.
//!
//! The outputs are committed. Reshape this script, run it, `git diff`: an empty
//! diff proves the change was pure shape.
import { createHash } from "node:crypto";
import { cpSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const out = process.argv[2] ? resolve(process.argv[2]) : here;
const sha256 = (path) => createHash("sha256").update(readFileSync(path)).digest("hex");
const list = (dir, keep) => readdirSync(join(here, dir)).filter(keep).sort().map((f) => `${dir}/${f}`);

rmSync(join(out, "tokens"), { recursive: true, force: true });
mkdirSync(join(out, "tokens"), { recursive: true });
for (const [from, to] of [["palette/tailwind.css", "tokens/tailwind.css"], ["palette/themes.css", "tokens/themes.css"], ["palette/src/palette.mjs", "tokens/palette.mjs"], ["palette/src/colour.mjs", "tokens/colour.mjs"]]) cpSync(join(here, from), join(out, to));

const shipped = {
  tokens: ["tokens/tailwind.css", "tokens/themes.css", "tokens/palette.mjs", "tokens/colour.mjs"],
  logos: list("logos", (f) => f.endsWith(".svg")),
  icons: list("icons", (f) => /\.(svg|ico)$/.test(f)),
  fonts: list("fonts", (f) => /\.(ttf|txt)$/.test(f)),
};
const manifest = Object.fromEntries(Object.entries(shipped).map(([dir, files]) => [dir, files.map((file) => { const path = join(dir === "tokens" ? out : here, file); return { file, bytes: statSync(path).size, sha256: sha256(path) }; })]));

const palette = JSON.parse(readFileSync(join(here, "palette/brand-tokens.json"), "utf8"));
const typography = {
  wordmark: { family: "Michroma", note: "The wordmark is optically weighted outlined artwork; use the logo files, typing the name does not recreate it.", files: ["fonts/Michroma-Regular.ttf"], licence: "fonts/Michroma-OFL.txt" },
  text: { family: "Inter Tight", weights: [400, 600, 700], files: ["fonts/InterTight-400.ttf", "fonts/InterTight-600.ttf", "fonts/InterTight-700.ttf", "fonts/InterTight-Variable.ttf"], licence: "fonts/InterTight-OFL.txt" },
  data: { family: "IBM Plex Mono", files: ["fonts/IBMPlexMono-Regular.ttf"], licence: "fonts/IBMPlexMono-OFL.txt" },
};
for (const role of Object.values(typography)) for (const f of [...role.files, role.licence]) if (!shipped.fonts.includes(f)) throw new Error(`Font file not shipped: ${f}`);
if (!shipped.logos.includes("logos/plate-89-blue.svg")) throw new Error("Primary symbol missing");

const brand = {
  name: "Origin89",
  version: JSON.parse(readFileSync(join(here, "package.json"), "utf8")).version,
  names: { company: "Origin89", hardware: "Origin89 Controller", app: "Origin89 Offgrid", assistant: "Buddy", protocol: "KM43" },
  colour: { brand: palette.brand, themes: palette.themes, source: "palette/src/palette.mjs", snapshot: palette.snapshot_date },
  typography,
  logos: { primarySymbol: "logos/plate-89-blue.svg", variants: shipped.logos },
  icons: { favicon: "icons/favicon.svg", offgrid: "icons/offgrid-flat-master.svg" },
  files: manifest,
  policy: "LICENSE.md",
};
writeFileSync(join(out, "brand.json"), JSON.stringify(brand, null, 2) + "\n");
console.log(`brand.json — ${Object.values(manifest).flat().length} files shipped, ${Object.keys(palette.themes).length} themes`);
