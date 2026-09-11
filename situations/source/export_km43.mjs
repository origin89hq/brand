import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const folder = new URL("../scenes/km43-canoe/", import.meta.url);
const source = fileURLToPath(new URL("km43-social.png", folder));
const target = fileURLToPath(new URL("km43-social.jpg", folder));
await sharp(source).resize(1280, 640).jpeg({ quality: 92, mozjpeg: true }).toFile(target);
const info = await sharp(target).metadata();
const bytes = readFileSync(target);
if (info.width !== 1280 || info.height !== 640 || bytes.length >= 1_000_000) {
  throw new Error("KM43 social preview must be 1280 × 640 and under 1 MB");
}
const provenancePath = new URL("scene.json", folder);
const provenance = JSON.parse(readFileSync(provenancePath, "utf8"));
provenance.files["km43-social.jpg"] = createHash("sha256").update(bytes).digest("hex");
provenance.social_export = {
  width: 1280,
  height: 640,
  format: "jpeg",
  quality: 92,
  bytes: bytes.length,
};
writeFileSync(provenancePath, JSON.stringify(provenance, null, 2) + "\n");
console.log(`KM43 social preview: ${target} (${bytes.length} bytes)`);
