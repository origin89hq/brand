# Contributing

Colour changes go in `palette/src/palette.mjs`, with the reason beside the
value. Run `pnpm check`: it regenerates `tokens/` and `brand.json`, and it
fails if a value no longer clears the contrast floor it claims. Commit the
regenerated files with the change.

Logos, icons and the character are the identity itself. Fixes to a file that is
broken, mis-exported or mis-named are welcome. New marks and redesigns are not
taken from pull requests; open an issue first.

A pull request states what changed, why, and how it was checked. Keep it to one
change.

## Development setup

Follow the [Origin89 engineering standards](https://github.com/origin89hq/engineering)
for working practices, tests, writing, and commits. `AGENTS.md` loads shared
skills at the start of a task; `just skills-sync` refreshes them from engineering.
Keep local constraints and domain-specific checks alongside those shared rules.

Track confirmed problems left outside the current fix using the
[shared issue rule](https://github.com/origin89hq/engineering/blob/main/skills/origin89-working/SKILL.md#track-unfinished-work).
Use `gh` to find or create the issue, verify it, and return its URL.

Install just 1.58.0 and Python 3.9+ for the skill bootstrap. Run `just --list`
for repository commands and `just check` before opening a pull request.

Use Node 24 LTS and the pnpm version in `package.json`. Install dependencies
with `pnpm install --frozen-lockfile`. Biome checks authored JavaScript and
TypeScript; generated assets keep their existing validators.

Biome covers the authored package/build JavaScript and its configuration. Python
renderers own the generated preview HTML, provenance JSON, token CSS, and SVG
assets; do not reformat those outputs independently of their generators.
