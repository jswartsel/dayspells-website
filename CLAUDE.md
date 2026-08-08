# Notes for Claude

Context carried over from the chat where this was built. Read `README.md`
first for what the project is and how to run it.

## Working agreements

- **Don't hand-illustrate the meadow.** The entire premise is that every
  pixel is photographic wool from `photos/`. If something is missing, it
  gets extracted, not drawn.
- **Verify visually before claiming it works.** `tools/check.py` renders
  screenshots and a cursor-wake heatmap. A frame that runs without console
  errors can still look wrong. Several bugs here were only visible in a
  screenshot: hard rectangular edges, a mirror-tiled ground that read as
  wallpaper, a wash behind the wordmark that looked like fog.
- **Prefer editing files over regenerating them.** An earlier version of
  the build used index-based string slicing on the HTML; one slice came out
  empty, which turned `replace('', ...)` into "insert between every
  character" and destroyed the template. `build.py` now asserts on the
  payload slot and script-block count. Keep those assertions.
- The user is comfortable with the technical detail and wants to see the
  reasoning, not just the result.

## Decisions already made, and why

- **Occluders are kept, on purpose.** The user asked for flowers cut even
  when lines break them up, "leaving whatever overlapping color exists
  there" — they like the weirdness. So a bloom is closed across whatever
  crosses it and intersected back with the foreground. Do not reintroduce
  anything that severs plants from each other.
- **A bloom is any petal colour, not one colour.** The white irises have
  purple outlines around every petal; componenting the white family alone
  shatters them into eleven fragments.
- **Linen reference is the panel's dominant chroma mode**, not a margin
  sample. Margin sampling assumes a clean unstitched border and fails
  silently — degrading the segmentation everywhere, not just at the edge.
- **Colour families are HSV gates** in `config.FAMILIES`. The green gate
  is what makes grass separable; a white-balance shift will slide greens
  out of it and grass extraction will quietly return nothing.
- **`maroon` is subtracted from `dark`.** Crocus outers and iris falls are
  deep maroon, dark enough to land in the `V < 95` gate meant for the
  brown-black foliage. While they did, every crocus came out as loose
  petals and the purple irises were missing their falls. The populations
  separate by hue: foliage H 0–30 at V 19–31, maroon petals H 125–180 at
  V 54–75. Don't merge them back.
- **Splits are accepted on a share, not a pixel count.** No fixed
  distance-transform threshold fits both a pair of fat daffodil heads and
  a slim iris — the value that separated the irises shattered them into
  single petals. So the threshold is swept and a split counts only if the
  smallest part is ≥ `SPLIT_MIN_PART` of the whole.
- **Blooms recurse, grass doesn't.** Three fused flowers split two ways
  first, leaving one half still merged, so blooms split at `depth=2`.
  Stems have no second waist to find and recursion just chops them into
  segments, so grass runs one round.
- **Colour grade is baked into the assets** (`config.GRADE`), not applied
  as a CSS `filter` on the canvas. A compositor filter over a full-screen
  canvas costs on every frame; this costs nothing.
- **One sprite per plant, one `drawImage`.** Shadow is composited in at
  bake time. The draw loop uses a computed `setTransform` rather than
  `save/translate/rotate/scale/restore`.
- **DPR capped at 1.5.** Biggest single saving on retina; the wool sprites
  are soft enough that 2.0 buys nothing visible.
- **Density governor** rather than a fixed plant count — see README. It
  eases toward its target and fades plants near the cut rather than
  stepping; a step drops a whole band of ranks between two frames, which
  the user reported as the meadow losing chunks a few seconds after load.
  It also only acts below ~33fps now. The old band (42–66fps) meant a
  machine holding a perfectly good 58fps was still being thinned.
- **Plants are sown in clusters, not one at a time.** A head with a stem
  under it, 1–3 heads to a clump, 2–4 blades to a tuft. The head is
  placed first and its companion stem skips the crowding test — put the
  stem down first and it blocks the very head it belongs to, which cut
  flowers to 8 out of 415.
- **Rank is shared by a head and its own stem, and nothing else.** Share
  it across a whole cluster and the governor drops entire clumps at once.
- **Rustle amount is a gain on the drawn angle**, not only a bigger
  impulse. Two attempts at driving it through the impulse alone both
  failed: squared reached 21° at the maximum setting, cubed went
  3°/7°/11°/52° — dead at the bottom, a cliff at the top. A plant is
  inside the brush for a handful of frames and the spring pulls back the
  whole time, so impulse alone cannot reach a wide swing without
  destroying the low end. The spring stays clamped at 0.5 where it always
  was; `P.rustle` scales what that bend is worth on screen, capped by
  `SWING_MAX`. Measured: 1.2°/3.5°/10.3°/29.4°/69.2° across 0.5–4.
- **Grow-in is a draw-time scale.** Sprites are baked at `size end` and
  drawn scaled up from `size start`. Re-baking 26 assets every frame for
  eight seconds would be absurd.
- **Never re-bake sprites per frame.** Wander was first written to
  re-colour continuously, which cost 15.4ms of a 16.7ms frame — an order
  of magnitude more than the synchronous timing suggested (0.47ms/sprite),
  because canvas allocation and the shadow blur bill after the call
  returns. The tell was that frame rate did *not* recover when wander was
  switched off. Fixes: step in discrete jumps a few times a second; cache
  the contact shadow, which is derived from alpha and so is
  colour-independent; reuse canvases instead of allocating; and scale
  before colouring. `ensureBake` allocates, `recolour` does not.
- **Colour is one 3×3 matrix**, composed from gain+tint, hue and
  saturation and applied in a single pass over the pixels. It is exactly
  the identity at the defaults, so the untouched case costs nothing. Use
  the sRGB luminance coefficients (0.213/0.715/0.072) the SVG filter spec
  uses, or hue rotation stops holding its brightness.
- **Gain above ~1.2 eats the hue control.** Bright material goes out of
  gamut and the output clamp flattens the difference: at `bgGain 1.51`
  the linen computes to `[343,313,202]`, two channels clipped, and the
  ground barely responds to `bgHue`. This is gamut, not a bug — no colour
  space fixes it. Mid-tone assets are unaffected. If someone reports the
  hue slider "not doing anything", check their gain first.

## Known issues, not yet fixed

1. **`GRADE` is tuned for the old, darker panels and now overshoots.** The
   2026 linen is `#e3cf86` as shot; the grade pushes the ground tile to
   `#fbdd7e`, a much brighter, more clipped yellow. The old panels' linen
   was olive `#8c762d`, so the page's whole mood has shifted paler. This
   is a look decision, not a bug — flagged with the user, not yet settled.
2. **Faint linen fringe** survives on a few petal tips. Raising
   `FG_THRESHOLD` trades it against eating thin stems.
3. **`daffodil-a` carries a small white scrap** at its base, left behind
   when the narcissus it was fused to was split off.
4. **The clearing behind the wordmark can read as a bald patch** on some
   seeds. It's density thinning (an ellipse in `seed()`), not a wash.
5. **Faint vertical slub in the ground tile** repeats at 512px. It's real
   fabric texture, but visible on narrow viewports.

Fixed since the first pass: the crocus linen fringe is much reduced, and
the "rejected assets" list is gone entirely — the flowers that sat too
deep in foliage now extract fine, because nothing severs stems any more.
27 assets in the payload, up from 18.

## Environment gotchas

- The chat container had **no GPU**, so all frame rates measured during
  development came from a software rasteriser and are pessimistic. On
  GPU-accelerated Chrome each sprite blit is roughly 10× cheaper. If
  `density()` reports `quality < 1` on a real machine, re-check the
  governor thresholds in `govern()` before assuming the page is too heavy.
- The page loads **Space Mono from Google Fonts**. In a sandbox without
  network this 403s harmlessly and falls back to a system mono.
- `photos/` are large JPEGs committed to the repo so the extraction is
  reproducible. If repo size becomes a problem, that's the thing to move.
