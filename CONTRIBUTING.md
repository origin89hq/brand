# Contributing

Colour changes go in `palette/src/palette.mjs`, with the reason beside the
value. Run `npm run check`: it regenerates `tokens/` and `brand.json`, and it
fails if a value no longer clears the contrast floor it claims. Commit the
regenerated files with the change.

Logos, icons and the character are the identity itself. Fixes to a file that is
broken, mis-exported or mis-named are welcome. New marks and redesigns are not
taken from pull requests; open an issue first.

A pull request states what changed, why, and how it was checked. Keep it to one
change.
