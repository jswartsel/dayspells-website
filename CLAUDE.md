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

- **Luminance-only relight.** Correcting the full colour field neutralised
  the linen but turned the pink irises mint. Don't "improve" this.
- **Erode-and-reconstruct isolation.** Cut depth must exceed half the stem
  width. A first attempt at ~16px radius did nothing; the working range is
  a swept 15–103px kernel, scored on crop-border contact.
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

The user has said there are glitches they want to circle back to. These are
the ones already identified:

1. **Crocus cutouts carry faint linen fringe** at the petal edges. The
   brightness gate (`config.V_GATE`) that saves them from the near-black
   foliage also lets some ground through.
2. **Rejected assets.** `iris-purple-b`, `iris-pink-b`, `iris-white-b`,
   `daffodil-a`, `daffodil-b`, `narcissus-b/c/d`, `crocus-a` all failed
   extraction — the flower sits too deep in surrounding foliage, so the
   erosion that severs the stems also eats the petals. Worth another pass
   with a different approach; the palette is currently short on pink and
   white irises as a result.
3. **The clearing behind the wordmark can read as a bald patch** on some
   seeds. It's density thinning (an ellipse in `seed()`), not a wash.
4. **Faint vertical slub in the ground tile** repeats at 512px. It's real
   fabric texture, but visible on narrow viewports.
5. **Only 18 assets** — colonies help disguise it, but repeats are findable.

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
