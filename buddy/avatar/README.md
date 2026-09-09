# Buddy small avatars

Small avatars use front-facing native alpha renders composited on green and displayed in a circle. The default has a gentle smile with the tongue tucked in.

`build_avatar.py` reads all seven expressions from `../presentation/`, checks their source hashes and exports square 512 px PNGs, circular PNGs for the guide, and small responsive WebP previews. The manifest records the native source, crop and output hashes. There is no separate illustrated character.

Edit and save `../presentation/face-front.blend`, then run `pnpm brand:avatars` to render its camera, lighting, materials, and greeting changes. The command reads the edited scene and never overwrites it. Run `pnpm brand:export` after changing avatar composition, then `pnpm web:build` to refresh the website and Storybook.

The shared `BuddyAvatar` component selects the closer crop and a circle at 96 px and below. Larger images use the transparent portrait. The green background is reserved for avatars or an explicitly requested studio scene. Set `shape="circle"` or `shape="rounded"` explicitly when needed. `framing="avatar"` selects the close crop at another size.

App and Apple icons use the green portrait with a platform-applied mask. Browser favicons use the circular PNG artwork. All seven expressions remain available through the component's `expression` prop.
