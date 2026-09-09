//! Rebuilds into a temporary directory and compares the generated files byte for
//! byte with what is committed, then checks that every file `brand.json` lists is
//! present with the hash it claims. A package whose manifest and files disagree
//! is refused.
import { createHash } from "node:crypto";
import { mkdtempSync, readdirSync, readFileSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const scratch = mkdtempSync(join(tmpdir(), "origin89-brand-"));
try {
  execFileSync(process.execPath, [join(here, "build.mjs"), scratch], { stdio: "ignore" });
  const walk = (root, dir) => readdirSync(join(root, dir)).flatMap((f) => (statSync(join(root, dir, f)).isDirectory() ? walk(root, join(dir, f)) : [join(dir, f)]));
  for (const name of ["brand.json", ...["tokens", "logos", "icons", "fonts", "art"].flatMap((d) => walk(scratch, d))]) {
    if (!readFileSync(join(here, name)).equals(readFileSync(join(scratch, name)))) throw new Error(`Committed ${name} differs from a fresh build; run build.mjs and commit`);
  }
  for (const d of ["tokens", "logos", "icons", "fonts", "art"]) if (walk(here, d).length !== walk(scratch, d).length) throw new Error(`Committed ${d}/ has files a fresh build does not`);
  const brand = JSON.parse(readFileSync(join(here, "brand.json"), "utf8"));
  let checked = 0;
  for (const entry of Object.values(brand.files).flat()) {
    const digest = createHash("sha256").update(readFileSync(join(here, entry.file))).digest("hex");
    if (digest !== entry.sha256) throw new Error(`${entry.file}: hash differs from brand.json`);
    checked++;
  }
  for (const role of Object.values(brand.typography)) for (const f of [...role.files, role.licence]) readFileSync(join(here, f));
  console.log(`  brand.json agrees with ${checked} shipped files and a fresh build.`);
} finally { rmSync(scratch, { recursive: true, force: true }); }
