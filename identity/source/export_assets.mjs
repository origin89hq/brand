import fs from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(
  process.env.O89_NODE_MODULES ? process.env.O89_NODE_MODULES + "/" : import.meta.url,
);
const sharp = require("sharp");
const root = path.resolve(import.meta.dirname, "..");
await fs.mkdir(path.join(root, "logos/png"), { recursive: true });
for (const file of await fs.readdir(path.join(root, "logos"))) {
  if (!file.endsWith(".svg")) continue;
  const input = path.join(root, "logos", file);
  await sharp(input, { density: 300 })
    .resize({ width: 2000 })
    .png()
    .toFile(path.join(root, "logos/png", file.replace(".svg", ".png")));
}
for (const size of [16, 24, 32, 48, 64, 128, 180, 192, 256, 512, 1024]) {
  await sharp(path.join(root, "icons/offgrid-flat-master.svg"), { density: 300 })
    .resize(size, size)
    .png()
    .toFile(path.join(root, `icons/offgrid-flat-${size}.png`));
}
const cols = ["blue", "black", "white"];
let body =
  '<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="900"><rect width="1800" height="900" fill="#f4f3ef"/>';
let y = 40;
for (const kind of ["origin89-horizontal", "origin89-stacked", "origin89-offgrid"]) {
  for (let i = 0; i < 3; i++) {
    const f = await fs.readFile(path.join(root, `logos/${kind}-${cols[i]}.svg`), "utf8");
    body += `<rect x="${i * 600 + 20}" y="${y - 15}" width="560" height="260" rx="12" fill="${i === 2 ? "#07090c" : "#ffffff"}"/>`;
    body += f.replace("<svg ", `<svg x="${i * 600 + 60}" y="${y + 20}" width="480" height="180" `);
  }
  y += 290;
}
body += "</svg>";
await sharp(Buffer.from(body)).png().toFile(path.join(root, ".build/vector-proof.png"));
console.log("Vector PNGs, flat icons, and proof exported");
const plate = await fs.readFile(path.join(root, "logos/plate-89-blue.svg"), "utf8");
const favicon = plate.replace(/viewBox="[^"]+"/, 'viewBox="-9.09 -54.09 218.18 218.18"');
await fs.writeFile(path.join(root, "icons/favicon.svg"), favicon);
for (const size of [16, 32, 48])
  await sharp(Buffer.from(favicon), { density: 400 })
    .resize(size, size)
    .png()
    .toFile(path.join(root, `icons/favicon-${size}.png`));
try {
  for (const size of [32, 48, 64, 128, 180, 192, 256, 512, 1024])
    await sharp(path.join(root, "renders/icon.png"))
      .resize(size, size)
      .removeAlpha()
      .png()
      .toFile(path.join(root, `icons/offgrid-3d-${size}.png`));
} catch (e) {
  if (e.code !== "ENOENT" && !e.message.includes("missing")) throw e;
}
const logowhite = await fs.readFile(path.join(root, "logos/origin89-horizontal-white.svg"), "utf8");
const controller = await fs.readFile(
  path.join(root, "logos/origin89-controller-white.svg"),
  "utf8",
);
function nested(svg, x, y, w, h) {
  return svg.replace("<svg ", `<svg x="${x}" y="${y}" width="${w}" height="${h}" `);
}
const tile = await fs.readFile(path.join(root, "renders/tile-transparent.png"));
const cover = `<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900"><title>Origin89 social cover template</title><rect width="1600" height="900" fill="#07090c"/>${nested(logowhite, 80, 74, 560, 105)}<text x="80" y="350" fill="#e7eaee" font-family="Inter Tight,Arial,sans-serif" font-weight="600" font-size="83">Simple control.</text><text x="80" y="447" fill="#e7eaee" font-family="Inter Tight,Arial,sans-serif" font-weight="600" font-size="83">Your way.</text><text x="80" y="570" fill="#9aa5b1" font-family="Inter Tight,Arial,sans-serif" font-size="30">From the cottage to the field.</text><image href="data:image/png;base64,${tile.toString("base64")}" x="805" y="147" width="700" height="700"/><rect x="80" y="781" width="105" height="7" fill="#2b4a97"/></svg>`;
await fs.writeFile(path.join(root, "applications/social-cover.svg"), cover);
await sharp(Buffer.from(cover)).png().toFile(path.join(root, "applications/social-cover.png"));
const label = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 560"><title>Origin89 Controller brand placement study - no fabrication dimensions</title><rect width="900" height="560" rx="25" fill="#0d1116"/>${nested(controller, 84, 76, 728, 138)}<path d="M84 304H816" stroke="#3a434d"/><circle cx="93" cy="380" r="6" fill="#4c7d5f"/><text x="118" y="389" font-family="IBM Plex Mono,monospace" font-size="24" fill="#e7eaee">STATUS</text><text x="84" y="501" font-family="IBM Plex Mono,monospace" font-size="17" fill="#9aa5b1">BRAND PLACEMENT STUDY</text></svg>`;
await fs.writeFile(path.join(root, "applications/controller-label-study.svg"), label);
await sharp(Buffer.from(label), { density: 150 })
  .resize(1600)
  .png()
  .toFile(path.join(root, "applications/controller-label-study.png"));
console.log("Favicon, rendered icon sizes, social cover and label study exported");
