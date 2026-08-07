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
- **Colour grade is baked into the assets** (`config.GRADE`), not applied
  as a CSS `filter` on the canvas. A compositor filter over a full-screen
  canvas costs on every frame; this costs nothing.
- **One sprite per plant, one `drawImage`.** Shadow is composited in at
  bake time. The draw loop uses a computed `setTransform` rather than
  `save/translate/rotate/scale/restore`.
- **DPR capped at 1.5.** Biggest single saving on retina; the wool sprites
  are soft enough that 2.0 buys nothing visible.
- **Density governor** rather than a fixed plant count — see README.

## Known issues, not yet fixed

1. **`GRADE` is tuned for the old, darker panels and now overshoots.** The
   2026 linen is `#e3cf86` as shot; the grade pushes the ground tile to
   `#fbdd7e`, a much brighter, more clipped yellow. The old panels' linen
   was olive `#8c762d`, so the page's whole mood has shifted paler. This
   is a look decision, not a bug — flagged with the user, not yet settled.
2. **Some blooms merge.** `daffodil-a` is a daffodil and a narcissus
   together; `iris-white-b` is a purple iris over a pink one. They're
   curated as `clump`, which is fine, but a watershed split on the
   distance transform would separate them if wanted.
3. **Faint linen fringe** survives on a few petal tips (the crocuses, and
   `iris-pink-c` which was rejected for it). Raising `FG_THRESHOLD` trades
   it against eating thin stems.
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
