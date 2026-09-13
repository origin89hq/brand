import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const folder = new URL("../scenes/buddy-chat/", import.meta.url);
const source = fileURLToPath(new URL("buddy-social.png", folder));
const target = fileURLToPath(new URL("buddy-social.jpg", folder));
await sharp(source).resize(1280, 640).jpeg({ quality: 92, mozjpeg: true }).toFile(target);
const info = await sharp(target).metadata();
const bytes = readFileSync(target);
if (info.width !== 1280 || info.height !== 640 || bytes.length >= 1_000_000) {
  throw new Error("Buddy social preview must be 1280 × 640 and under 1 MB");
}
const provenancePath = new URL("scene.json", folder);
const provenance = JSON.parse(readFileSync(provenancePath, "utf8"));
provenance.social_export = {
  width: 1280,
  height: 640,
  format: "jpeg",
  quality: 92,
  bytes: bytes.length,
  sha256: createHash("sha256").update(bytes).digest("hex"),
};
provenance.source_files["situations/source/export_buddy_chat.mjs"] = createHash("sha256")
  .update(readFileSync(fileURLToPath(import.meta.url)))
  .digest("hex");
writeFileSync(provenancePath, `${JSON.stringify(provenance, null, 2)}\n`);
console.log(`Buddy social preview: ${target} (${bytes.length} bytes)`);
