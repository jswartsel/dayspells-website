# dayspells — orientation for a new session

Paste or attach this at the start of a fresh conversation. It is the
fastest path from cold to useful. The repo also carries:

- **`README.md`** — what the project is, how to run it, how the page works
- **`CLAUDE.md`** — the trap list: decisions already made, and what broke
- **`GAME.md`** — speculative notes on the "wanderlust" clock and where a
  game-like layer could go. Nothing in it is implemented.

Read all three once. This file is the map; `CLAUDE.md` is the minefield.

---

## 1. What this is

A site for the band **dayspells**. The background is a wildflower meadow
seen from above that sways in an ambient breeze and rustles where the
cursor brushes through it.

**The premise, which governs every decision: every pixel of the meadow is
photographic wool.** Nothing is illustrated. The flowers, grasses and
ground are cutouts extracted programmatically from photographs of 1970s
crewelwork panels, then scattered procedurally so the field is different
on every load. If something is missing from the field, it gets
*extracted*, not drawn.

Private repo, **~39 commits**, branches **`main`** (deploy) and **`dev`**
(work). `CNAME` is **dayspells.com**. Pages on a private repo needs a paid
plan — **this has never been confirmed to actually serve.** Check the real
domain before assuming a push deployed.

---

## 2. Layout

```
index.html          the entire site: markup, style, and the field engine
photos/             source photographs (55MB, committed)
pipeline/
  config.py         thresholds, colour grade, and the KEEP curation list
  extract.py        photos -> isolated transparent PNGs
  build.py          PNGs -> assets/payload.json -> single-file dist/
assets/
  flowers/ grass/   extracted cutouts (committed), 27 curated in KEEP
  ground/           the seamless linen tile
  payload.json      what the page actually fetches
dist/dayspells.html self-contained, opens from file://
tools/serve.py      dev server -> http://localhost:8000/
tools/check.py      headless screenshots + cursor-wake heatmap
work/               intermediates, contact sheets (gitignored)
```

**Run it:**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python pipeline/build.py     # assets -> payload + dist
python tools/serve.py        # -> http://localhost:8000/
```

`assets/` is committed, so you do **not** need to re-run extraction to
work on the site. Edit `index.html`, reload. Re-run `build.py` only when
assets or `config.py` change — **and after any `index.html` change**, or
`dist/` goes stale. `build.py` also rewrites `assets/palette.json` with
unseeded k-means, so `git checkout assets/palette.json` after every build
to keep the diff clean.

---

## 3. History — two eras

**Era 1 (superseded).** Built from two photographs of framed panels.
Perspective-warped off hand-read frame corners, sampled linen colour from
the outer margins, isolated each flower with hand-placed seed points plus
an erode-until-the-stems-snap sweep. About a third of the flowers had to
be **rejected** because the erosion that severed a stem also ate petals.

**Era 2 (current).** New photographs shot square-on and evenly lit.
Combined with two requests — *keep the lines that cross a flower*, and
*emit grass separately* — the whole isolation approach was deleted rather
than repaired. **The hard part was the part that got deleted:** all the
erosion machinery existed only to stop a flood fill grabbing neighbours
through stems. Once occluders were *wanted*, it went away and the
rejected-flower problem dissolved with it. Extraction is now fully
automatic — no corners, no seed points. 18 → 27 curated assets.

Ground moved again later: `IMG_1643`, a dedicated close-up of bare linen,
replaced hunting a clean square out of an embroidered panel.

---

## 4. The extraction pipeline

`python pipeline/extract.py [stage]` — `mask`, `blooms`, `grass`,
`linen`, `sheet`, or `all`. Always finish with `sheet` and look at the
contact sheet before editing `config.KEEP`; it is the only reliable way
to spot bad alpha.

Detail is in `README.md`. The four things that will bite:

- **Linen reference is the panel's dominant chroma mode**, not a margin
  sample. Margin sampling assumes a clean unstitched border and fails
  *silently*, degrading segmentation everywhere rather than at the edge.
- **A bloom is any petal colour, not one colour.** The white irises have
  purple outlines; componenting one colour shatters them.
- **`maroon` is subtracted from `dark`.** Crocus outers and iris falls are
  deep maroon and otherwise land in the foliage gate.
- **The green family gate is what makes grass separable.** A
  white-balance shift slides greens out of it and grass returns nothing.

---

## 5. The page

Single file. No build step for the page itself; `build.py` only inlines
the payload to produce `dist/`.

### Pages
Six, routed on the hash so the back button works and each is linkable:

| | |
|---|---|
| `#home` | the wordmark (links to `#about`) and four links under it |
| `#about` | who the band is, with a `mailto:` |
| `#listen` | bandcamp · apple music · spotify |
| `#shows` | "coming soon" |
| `#shop` | "coming soon" |
| `#viz` | the visualizer — no type at all. Also served at `/viz` |

`follow` is not a page — straight out to Instagram. External links open
in a new tab. Only the active page is in the flow; the rest are
`[hidden]`, which is what keeps the zones honest (a hidden box measures
0×0 and drops out of the zone pass). A `<` appears top-left on sub-pages.
**Changing page resows the field** — that is the transition, not a cost.

### viz
A screen with nothing on it, for leaving running. No type: `showView`
hides every `[data-view]` because nothing claims the name `viz`, and
`body.viz` hides the corner links, the hint and the back caret. Wander
starts by itself (deferred to the end of `boot()` — `setWander` samples
the canvas, which has no size earlier).

- **0–3 glades**, random position and size, `ax` 0.08–0.18 of the short
  side, redrawn on every resow — zero included, so a sow can come up as
  unbroken field. Measured over 200 sows: 59 / 57 / 39 / 45. Grass-only, same as `data-zone`.
  Non-overlapping: separation is tested on each glade's **largest**
  semi-axis, biggest placed first, shrinking on failure. Measured 0
  overlapping pairs in 2721, across 1280×800, 390×844 and 844×390.
- **The hand is `ghost` in the panel** — an enable checkbox and a speed
  slider, on every page, not just the visualizer. Speed is a pure time
  dilation on the doodle (scaling `dt`), default **2.5**: 1.0 is the pace
  it was first tuned at and read as too languid, 4 overshot. Measured
  158 px/s at 1, 183 at 2.5, 644 at 4. A real pointer takes the brush back; after
  `GHOST_IDLE` of stillness the hand resumes, but only if the checkbox
  was not deliberately unchecked (`ghostMuted`).
- **A doodle drives the brush.** It writes `ptr.x/y` and nothing else,
  so the frame loop differences it into velocity and the physics cannot
  tell it from a hand. A continuously-moving pen: curvature is **set**
  from three summed sines (not integrated — a damped random walk
  settles at 0.07 rad/s and draws a straight line), the pull toward its
  target saturates, and it reflects off edges rather than sliding along
  them. A 6×4 grid drives re-aiming at stale cells so it covers the
  screen. Measured over 45s: 21/24 cells, 8.1 screen-widths, 90–236
  px/s, 10 edge frames in 2700. Replaces the `ghost` Lissajous.
- **Resows itself** every 15–20s, counted in the frame loop so a
  backgrounded tab does not bank a burst of them.
- **Grow-in is 5s here**, not the site's 6. Measured: 5s growing then
  11–13s of settled field per cycle, which is the window breathing
  gets. `P.grow` is borrowed and restored on exit.

`/viz` is a redirect stub at `viz/index.html`; GitHub Pages has no
rewrites, so the alternative was a second copy of the whole engine at
that path. Costs a visible `/#viz` in the address bar.

### Zones
Two kinds, same geometry, measured off the type itself via
`getBoundingClientRect`:

- **`data-zone`** — grass only. Wordmark, sub-page messages, and the menu
  links (nav at `1.25`, listen links at `1`).
- **`data-bare`** — nothing sown. Only the back caret, plus the
  corner-links box (a rectangle, since two edges run off-screen).

`ZONE_PAD_X 0.18` / `ZONE_PAD_Y 0.65` are **additive in em**;
`ZONE_TOP 0.60` shortens the *pad* above, not the semi-axis. Every
semi-axis is floored at `half-box + half-bloom + ZONE_CLEAR (10px)`.
`ZONE_GRASS 0.15` thins the clearings to 15% of what lands in them.
`BARE 0.80` scales the corner box. **The attribute must sit on an inline
span** — a block stretches to its widest sibling.

### Type
One variable, `--menu` on `:root`, drives the nav, the listen links and
the sub-page messages: `min(--type * .54, 4.2vw)` in landscape (the vw cap
holds four links on one line), `max(--type * .54, 26px)` in portrait (a px
floor, because `--type` is a share of the viewport and the wordmark can't
grow on a phone). `.about` is `calc(--menu * .58)`.

Gaps between stacked type are **`proportional term + 48px`** — a sprite is
a fixed pixel size at any viewport, so an em-only gap leaves no room for a
bloom on a phone. Measured: a flat 48px band on every stacked pair.

### Rendering
Sprites baked once with contact shadow composited in; one `drawImage` per
plant. `ensureBake(a)` allocates, `recolour(a, M)` does not — keep that
split. Each plant is a damped spring in a three-wave wind field. Sowing is
by cluster. A density governor (`autothin`) exists but is **off**.

### wander
Four hue/sat walkers on unequal intervals, stepped rather than
continuous: `every` 0.1667 / 0.1333 (hues) and 1.083 / 1.000 (sats), divided
by `wander speed`. The two saturations were slowed on purpose — ground
sat to 0.60 of the rate it ran at, plant sat to 0.75 — via `every`, not
`step`, because `every` is the rate term `wanderSpeed` already divides.
The wordmark colour is **derived, not cycled** — a 24×12 readback of the
box behind it, steered to the complementary hue with lightness flipped.

**The gain roll** rides on the resow, not on a clock, and snaps rather
than ramping. Ground rolls dark (0) / home (the slider's value when
wander started) / bright (80–100% of max), equally likely; the plants
follow from it — 0–5% of full under a bright ground (measured 0.03–4.99%), else between
the slider's value and full. The pairing avoids washed-out flowers on a
washed-out ground. Only while wander runs; both go home when it stops.

### breathing
While wander runs, blooms change size: ×1.2 up or ×0.5 down, band
`sizeFrom/size` to 1.2, 200 blooms/sec. Draw-time scale, so ~free.
Lopsided on purpose — gentle growth, halving shrink — so the field
carries small flowers throughout. Measured over 48s: mean holds at
0.72–0.84, individuals span 0.13–1.2, 11–20% below half size.
**The coin is not 50/50** — `BREATHE_FAIR` (0.631) is derived from the two
step sizes, because halving is a bigger move than ×1.5 and a fair coin
wilts the whole meadow.

### The panel
Corner links **wander · regrow · mod**. `c` toggles, `Esc` closes,
`#tune` opens on load. Alt-click any control restores its default.

| group | |
|---|---|
| **rustle** | amount (0–8) |
| **wander** | speed |
| **meadow** | ground hue/sat/gain, plant hue/sat/gain, ground zoom, density |
| **ghost** | enable, speed — the automated hand, on any page |
| **plant mix** | purple / white / yellow / pink flwrs, grass |

Mix and density **queue a regrow 2s** after the last change.
**There is no `copy json` button** — `copy(tune())` in the console does
the same job; `tune()` with no argument returns the current set.

---

## 6. Current defaults

```json
{
  "rustle": 3, "speed": 0.7, "settle": 1.5, "radius": 150,
  "bgTint": "#ffffff", "bgGain": 1.22, "bgHue": 0, "bgSat": 0.6,
  "fgTint": "#ffffff", "fgGain": 1.35, "fgHue": 0, "fgSat": 0.8,
  "ground": 0.34, "density": 1.8,
  "sizeFrom": 0.2, "size": 1.7, "grow": 6,
  "wanderSpeed": 2, "markSize": 1.3, "markColor": "#f4451f",
  "mixPurple": 0.25, "mixWhite": 1.55, "mixYellow": 0.8,
  "mixPink": 0.65, "mixGrass": 0.2, "autothin": 0
}
```

Several of these no longer have controls but are still live and still
returned by `tune()`: `speed`, `settle`, `radius`, `bgTint`, `fgTint`,
`markSize`, `markColor`, `sizeFrom`, `size`, `grow`, `autothin`.
`bgGain` **does** have a slider now (`ground gain`, 0.2–2), which is the
one to reach for when ground hue seems unresponsive — the 1.22 default
is already past the ~1.2 where the clamp starts eating `bgHue`.

---

## 7. Measurements worth not re-deriving

- **Rustle saturates.** Peak drawn swing: 6.7° / 15.8° / 48.5° at
  settings 1 / 2 / 3, then **73.1° at 4, 5, 6 and 8**. `SWING_MAX` (1.5
  rad) clamps it. Above 4 no single plant swings further; what changes is
  how much of the field reaches that swing.
- **Breathing holds.** Mean bloom size 0.72–0.84 across 48s while
  individuals span 0.13–1.2 and 11–20% sit below half size. Mean sprite *area* comes out slightly below
  rest, so no overdraw cost. 61fps idle, 61fps breathing, headed.
- **Flower bands.** A flat 48px between every stacked pair from 390px
  wide to 1440.
- **Zone purity.** 100% grass in every grass zone, empty in every bare
  zone, across all pages at laptop / phone / landscape-phone.
- **Wander is close to wall-clock deterministic now.** The step
  accumulator subtracts rather than resetting (`GAME.md` §1 — this was
  fixed, and the clamp beside it is load-bearing). Measured at
  `wanderSpeed 2` / 60.1fps, all four walkers run within **0.8%** of
  nominal, where ground hue used to be 6.7% slow. What still diverges
  from wall time is deliberate: `dt` is clamped to 1/30, and a
  backgrounded tab throttles rAF.
- **Walker cycles at `wanderSpeed 2`:** ground hue 36s, ground sat 45.5s,
  plant hue 28.8s, plant sat 50.0s; full state repeats every **~3.8
  days**. The hue cycles are unchanged by the granularity change — step
  and interval were both divided by 3, so only the grain moved. (A
  comment in the file claiming "four months" is stale.)
- **Hue granularity is free; only the ground pays.** `plantQueue` resets
  rather than accumulating and drains at a flat 2 sprites/frame, so it
  was already saturated — stepping 3x as often changes the plant work
  per frame not at all. Ground re-bake is 0.94ms and now runs 3x as
  often, 0.12ms/frame amortised becoming 0.31ms. Measured 60.1fps before
  and after; at `wanderSpeed 6`, where the ground-hue threshold is
  shorter than a frame, still 60.1fps and worst frame 19.8ms.

---

## 8. Working preferences (observed)

- Wants the reasoning, not just the result. Comfortable with technical
  depth, and reacts well to being told a request's premise is off.
- Iterates visually and fast; checks things in a real browser himself.
- Will sometimes say **"don't validate, just make the change"** to save
  tokens — respect it, but say plainly that it wasn't verified.
- Prefers work on `dev`, then a fast-forward merge to `main`. Asks
  explicitly when he wants it pushed; don't push unasked.
- **Has been right every time he pushed back.** When he said the listen
  links looked smaller than the nav links, a computed-style check said
  they matched — the check was wrong (it read the first selector match,
  which was a *hidden* element). If he says something looks off and the
  measurement disagrees, distrust the measurement first.

---

## 9. Hard-won lessons

Full list in `CLAUDE.md`. The five that cost the most:

1. **`willReadFrequently: true` pins a canvas to CPU memory.** Correct for
   a scratch surface you `getImageData` from, ruinous for anything drawn
   from afterwards. Took the page 60fps → 2.3fps.
2. **Benchmark canvas work with `headless=False`.** Headless Chromium has
   no GPU and reported the broken build above as *21% faster*.
3. **Zone tests must be in visual space, not anchor space.** A plant is
   rooted at its foot and drawn upward.
4. **Never re-bake sprites per frame.** Canvas allocation and shadow blur
   bill after the call returns, so synchronous timing lies.
5. **Careless stylesheet block edits fail silently, twice now.** A stray
   `*/` deleted the entire `.nav` rule; closing `:root` early stranded
   `--cream` inside a media query and the panel silently inherited dark
   plum. Read the computed value before touching anything else.

---

## 10. Open items

- **`autothin` is 0.** No frame-rate protection on anything slower than
  the dev Mac. Worth reconsidering before this gets real traffic.
- **Mobile has never been tested on real hardware.** Everything has been
  measured at phone *viewports* in desktop Chromium, which is not the same
  thing — different DPR, touch instead of cursor, and the phantom-gust
  fallback rather than a pointer.
- **`shows` and `shop` are identical** ("coming soon"), distinguishable
  only by URL.
- **The about paragraph's corners sit outside its ellipse.** Seven lines
  is far taller relative to width than anything else here, so a bloom
  lands on the first and last lines. A rounded-rect test for multi-line
  blocks is the real fix.
- **`.mark` overhangs the viewport by ~6px** below 900px wide in
  landscape. Empty padding only; type keeps 39–48px of clearance.
- **`GRADE` is tuned for the old darker panels and overshoots.** The 2026
  linen is `#e3cf86` as shot; the grade pushes the tile to `#fbdd7e`.
  A look decision, flagged and not settled.
- **No favicon** — a stray `/favicon.ico` 404.
- **`photos/` is 55MB**, committed so extraction is reproducible. First
  thing to move if repo size bites.
- **`assets/palette.json` churns on every build.** Nothing reads it at
  runtime; seed the k-means if the noise annoys.
- **GitHub Pages not confirmed live.**

---

## 11. Fast orientation

1. Read `CLAUDE.md`. It is the trap list and it is current.
2. `python tools/serve.py`, open the page, press `c`.
3. To change the field's look: it is almost always `DEFAULTS` or
   `pipeline/config.py::KEEP`, not engine code.
4. To change extraction: `config.py` first; `extract.py` only if the
   algorithm itself is wrong. Finish with the `sheet` stage.
5. **Before claiming a performance result, use a headed browser and check
   the battery.** At ~7% charge the Mac throttled to exactly 30.0fps in
   every configuration.
