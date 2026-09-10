# Working in this repository

At the start of each new task, run `just skills-sync` from the repository root.
Read `skills/origin89-working/SKILL.md` and the relevant domain skills under the
immutable `path` printed by that command. Keep that snapshot for the task; do not
refresh it halfway through work. Read local instructions and preserve stronger
project constraints and project-specific skills.

If refresh reports cached content, continue with that verified cache and mention
that the script could not check for updates. If no cache is available or
validation fails, report the error; do not claim the shared rules loaded. Local
instructions and the user's request still apply. Do not overwrite local skill
files to fix a conflict without reconciling them.

[Origin89 engineering](https://github.com/origin89hq/engineering) owns the shared
rules. Keep only repository-specific architecture, commands, target constraints,
and exceptions below. Internal RFCs and research belong in
[internal-research](https://github.com/origin89hq/internal-research). Add documentation
only when its value and upkeep are clear; remove AI filler from every message.

## Sources and validation

Edit colour in `palette/src/`; `tokens/`, `brand.json`, and web assets are
regenerated outputs. Keep editable identity and Buddy sources in their existing
source directories. Run `just check` and review the generated diff. Never
rebuild Blender scenes as part of a documentation or package-only check.

Read `CONTRIBUTING.md` and `docs/releases.md` before changing package exports or
release automation. Preserve the trusted publisher's workflow filename.
Changes to shipped assets or package behavior need a Changeset. Use released
package exports in consumers; fixes to shared assets belong here.
