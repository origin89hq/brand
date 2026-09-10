import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const root = path.resolve(import.meta.dirname, "..");
const repo = path.resolve(root, "..");
const { TOKENS } = await import(pathToFileURL(path.join(repo, "palette/src/palette.mjs")));
const { Colour } = await import(pathToFileURL(path.join(repo, "palette/src/colour.mjs")));
const snapshot = {
  version: "1.0",
  source: "palette/src/palette.mjs",
  snapshot_date: "2026-09-06",
  brand: { blue: "#2b4a97", ink: "#07090c", chalk: "#e7eaee", paper: "#f4f3ef" },
  typography: {
    wordmark: "Michroma, optically weighted outlined artwork",
    body: "Inter Tight",
    data: "IBM Plex Mono",
  },
  themes: Object.fromEntries(
    ["dark", "light"].map((t) => [t, Object.fromEntries(TOKENS.map((v) => [v.name, v[t]]))]),
  ),
};
snapshot.materials_3d = {
  shell: "#172c50",
  ceramic: "#eadfcf",
  buddy: "#594132",
  buddy_belly: "#b29879",
  buddy_muzzle: "#281c17",
  buddy_beard: "#493022",
  buddy_hoof: "#352b24",
  buddy_antler: "#927a57",
};
await fs.writeFile(
  path.join(root, "tokens/brand-tokens.json"),
  JSON.stringify(snapshot, null, 2) + "\n",
);
let css =
  '/* Origin89 Plate 89 kit v1.0. Snapshot: 2026-09-06. Product source: palette/src/palette.mjs */\n:root {\n --brand-blue: #2b4a97;\n --brand-ink: #07090c;\n --brand-chalk: #e7eaee;\n --brand-paper: #f4f3ef;\n --font-display: "Michroma", sans-serif;\n --font-body: "Inter Tight", sans-serif;\n --font-data: "IBM Plex Mono", monospace;\n}\n';
for (const theme of ["light", "dark"])
  css += `[data-theme="${theme}"] {\n${TOKENS.map((t) => ` --o89-${t.name}: ${t[theme]};`).join("\n")}\n}\n`;
css +=
  "\n/* Studio materials; flat brand colors above remain unchanged. */\n:root { " +
  Object.entries(snapshot.materials_3d)
    .map(([key, value]) => `--material-${key.replaceAll("_", "-")}: ${value};`)
    .join(" ") +
  " }\n";
await fs.writeFile(path.join(root, "tokens/brand-tokens.css"), css);
const pairs = [
  ["White on bridge blue", "#ffffff", "#2b4a97"],
  ["Chalk on bridge blue", "#e7eaee", "#2b4a97"],
  ["Bridge blue on paper", "#2b4a97", "#f4f3ef"],
  ["Chalk on ink", "#e7eaee", "#07090c"],
  ["Bridge blue on ink", "#2b4a97", "#07090c"],
  ["Dark link on ink", "#6279ad", "#07090c"],
];
const contrast = pairs.map(([label, fg, bg]) => ({
  label,
  fg,
  bg,
  ratio: Colour.fromHex(fg).contrastWith(Colour.fromHex(bg)),
}));
await fs.writeFile(
  path.join(root, "tokens/contrast-report.json"),
  JSON.stringify(contrast, null, 2) + "\n",
);
console.log(contrast.map((r) => `${r.label}: ${r.ratio.toFixed(2)}:1`).join("\n"));
