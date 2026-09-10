# Origin89 release standard

This is the reference setup for Origin89's public npm packages, starting with
`@origin89/brand`. Each repository releases independently. The same contributor
workflow can extend to workspaces; Rust crates, firmware, and hardware need
their own publishing integration before adopting it.

## Contributing a release

1. Make the change and regenerate any committed outputs with `pnpm check`.
2. Run `pnpm changeset`. Select the affected package, bump type, and write a
   short note explaining what changes for its users.
3. Include the generated `.changeset/*.md` file in the same PR as the change.
4. Merge the reviewed PR to `main`. Changesets opens or updates one release PR.
5. Review that release PR's versions and changelog, then merge it when ready
   to publish. CI builds, validates, packs, publishes, and creates the release.

Version numbers and `CHANGELOG.md` are generated from changesets. Normal feature
PRs do not bump versions or edit the changelog. Multiple changesets can collect
in one release PR, so every merged feature does not immediately become a release.

| Bump | Use when | Brand example |
| --- | --- | --- |
| Patch | Fix an existing contract or ship a compatible correction | Correct an export or manifest entry |
| Minor | Add something consumers can adopt without migration | Add a Buddy pose, token, or asset |
| Major | Require consumers to migrate | Remove or rename an export or token |

These bump choices are explicit, including before 1.0. Choose `major` for a
breaking change; Changesets takes 0.x to 1.0. Documentation, tests, or internal
tooling changes that do not affect the shipped package need no changeset.
Explain that in the PR. CI validates changeset syntax without requiring a
release for every change.

Example:

```markdown
---
"@origin89/brand": minor
---

Add Buddy's equipment-scout pose for equipment discovery pages.
```

## Shared setup

Use Node 24 in CI, a pinned package manager, an exact Changesets CLI version,
and a committed lockfile. This repo uses Changesets 3.0.2 and its compatible
GitHub Action 2.1.2, pinned by commit.

Keep these commands consistent across Origin89 package repositories:

| Command | Purpose |
| --- | --- |
| `pnpm changeset` | Add a user-facing release note and bump choice |
| `pnpm changeset status` | Inspect the pending release plan |
| `pnpm release:version` | Apply changesets, regenerate versioned outputs, and validate |
| `pnpm release:publish` | Run Changesets publication; normally CI handles this |

Copy `.changeset/config.json` with `baseBranch: main`, `commit: false`, public
access for public packages, and independent versions by default. Review package
visibility before adopting public access in another repository. Private packages
are excluded. In a workspace, mark only the root manifest private and keep the
publishable packages public. Introduce `fixed` or `linked` groups only when
packages need coordinated versions.

For a package without generated outputs, `release:version` can be
`changeset version && pnpm check`, where `check` runs that repo's validation.
Brand's `check` rebuilds the exports and copies `package.json.version` to
`brand.json`, verifies a fresh build, and creates the kit. Those tracked
outputs are included in the release PR.

The workflow uses Changesets' standard select-mode, version, pack, and publish
actions. Only the publish job has npm OIDC permission, and it consumes the
package and brand kit prepared by the validation job. Release notes come from
the generated changelog.

## GitHub and npm setup

Before enabling the workflow on `main`:

- In GitHub Settings → Actions → General, enable **Allow GitHub Actions to
  create and approve pull requests**. Without it, release PR creation fails.
- Configure npm trusted publishing for the repository and workflow filename.
  Brand retains `publish-brand.yml`, matching its existing trusted publisher.
  A new package may need its initial publication and publisher setup first.
- The default `GITHUB_TOKEN` can open the release PR but does not trigger its
  PR workflows. Run **check → Run workflow** on `changeset-release/main`
  before merging it (especially when `package` is a required check).
  The version action also runs `pnpm check` before writing the release PR.
  For fully automatic PR checks across Origin89, configure an Origin89 GitHub
  App with contents and pull-request write access and pass its installation
  token to the version action's `github-token` input.
- Keep automatic merging disabled: a maintainer chooses when the release PR
  is ready. Do not include `[skip ci]` in release commits or merge messages.

The workflow runs on `main` pushes. **publish-brand → Run workflow** on
`main` can reconcile the current state; selecting another branch is skipped.
There is no tag-triggered publisher alongside it.

## Brand migration

The baseline is 0.3.0, including the equipment-scout artwork. Complete its
existing release repair before merging this workflow. The initial patch
changeset then prepares 0.3.1 with the packaged changelog.

New single-package releases use Changesets' `v<version>` tags, beginning with
`v0.3.1`. Existing `brand-v<version>` tags and releases are preserved.
Workspace packages use Changesets' `<package-name>@<version>` convention.

Every new brand GitHub release keeps these asset names:

- `origin89-brand-kit.zip`
- `origin89-design-guide.pdf`

The website's `releases/latest/download/<filename>` links therefore continue
to work with the new tag convention.

## Failed releases

Check the failed job before choosing a recovery step:

- **Versioning or validation failed:** fix the source or generated outputs in
  a PR. A rerun uses the original commit, so it cannot pick up a new fix.
- **npm rejected publication:** fix the publisher configuration or permission
  issue, then rerun the failed job for the same release commit. Keep the
  prepared artifact; do not invent a new version for a transient failure.
- **Only kit attachment failed:** rerun the failed publish job. It downloads
  the same validated kit artifact and uploads the files again. Already-published
  npm versions are not replaced.
- **npm succeeded but tag or GitHub release creation failed:** inspect the
  registry, tag, and release separately. Restore the missing tag or release
  at the original release commit using that version's changelog, then restore
  its kit assets. Do not move a published tag or republish different content
  under the same version.
- **A published package is wrong:** add a corrective changeset and ship a new
  version.

Sources: [Changesets automation](https://changesets.dev/guide/automating),
[configuration](https://changesets.dev/guide/config),
[CLI commands](https://changesets.dev/guide/cli), and
[npm trusted publishing](https://docs.npmjs.com/trusted-publishers/).
