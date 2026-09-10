# Changesets

Run `pnpm changeset` when a change should reach package consumers. Choose the
affected package, a patch/minor/major bump, and describe the result for users.
Include the generated Markdown file in the same pull request as the change.

Changesets collects these files into a release PR after they reach `main`.
Merging that PR publishes the package, changelog, and brand kit.

See [the Origin89 release standard](../docs/releases.md) for bump guidelines,
repository setup, and recovery instructions.
