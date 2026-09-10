//! Builds the downloadable brand kit, `dist/origin89-brand-kit.zip`: the logos
//! as SVG and PNG, the icons, the fonts with their licences, the design guide
//! and the terms. It is attached to every version release, so the website can
//! link the latest one at a URL that never changes.
import { execFileSync } from "node:child_process";
import { cpSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const brand = JSON.parse(readFileSync(join(here, "brand.json"), "utf8"));
const stage = join(here, "dist", "origin89-brand-kit"),
  dist = join(here, "dist");
rmSync(stage, { recursive: true, force: true });
mkdirSync(stage, { recursive: true });
for (const f of readdirSync(join(here, "identity/logos")).filter((f) => /\.(svg|png)$/.test(f)))
  cpSync(join(here, "identity/logos", f), join(stage, "logos", f));
for (const f of readdirSync(join(here, "identity/icons")).filter((f) => /\.(svg|png|ico)$/.test(f)))
  cpSync(join(here, "identity/icons", f), join(stage, "icons", f));
for (const f of readdirSync(join(here, "identity/fonts")).filter((f) => /\.(ttf|txt)$/.test(f)))
  cpSync(join(here, "identity/fonts", f), join(stage, "fonts", f));
cpSync(
  join(here, "identity/guide/output/pdf/origin89-design-guide.pdf"),
  join(stage, "origin89-design-guide.pdf"),
);
cpSync(join(here, "identity/tokens/brand-tokens.css"), join(stage, "tokens", "brand-tokens.css"));
cpSync(join(here, "identity/tokens/brand-tokens.json"), join(stage, "tokens", "brand-tokens.json"));
cpSync(join(here, "LICENSE.md"), join(stage, "LICENSE.md"));
writeFileSync(
  join(stage, "README.txt"),
  `Origin89 brand kit ${brand.version}\n\nlogos/   ${readdirSync(join(stage, "logos")).length} files, SVG and PNG. The primary symbol is ${brand.logos.primarySymbol.replace("logos/", "")}.\nicons/   favicon and app icons.\nfonts/   ${brand.typography.wordmark.family}, ${brand.typography.text.family}, ${brand.typography.data.family}, each with its OFL licence.\ntokens/  the colour values for both themes, as CSS and JSON.\n\nRead origin89-design-guide.pdf for clear space, minimum sizes and colour use, and LICENSE.md for what you may do with the marks.\nSource: https://github.com/origin89hq/brand\n`,
);
const zip = join(dist, "origin89-brand-kit.zip");
rmSync(zip, { force: true });
execFileSync("zip", ["-qr", "-X", zip, "origin89-brand-kit"], { cwd: dist });
rmSync(stage, { recursive: true, force: true });
console.log(
  `${zip.replace(here + "/", "")} — ${(readFileSync(zip).length / 1048576).toFixed(1)} MB`,
);
