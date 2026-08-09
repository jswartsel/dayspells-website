# dayspells

A one-page site for the band **dayspells**. The background is a wildflower
meadow seen from above that sways in an ambient breeze, and rustles where
your cursor brushes through it.

Every pixel of the meadow is wool. Nothing is illustrated. The flowers,
grasses and ground are photographic cutouts extracted from two 1970s
crewelwork panels (`photos/`), isolated programmatically and scattered
procedurally, so the field is different on every page load.

---

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python pipeline/build.py     # assets -> assets/payload.json + dist/dayspells.html
python tools/serve.py        # -> http://localhost:8000/
```

`assets/` is committed, so you do **not** need to run the extraction to
work on the site. Edit `index.html` and reload — the page fetches
`assets/payload.json` at runtime. Re-run `build.py` only when the assets
or `pipeline/config.py` change.

### Re-running the extraction

```bash
python pipeline/extract.py all
```

Stages, runnable individually: `mask`, `blooms`, `grass`, `linen`,
`sheet`. Intermediates go to `work/` (gitignored). Always finish with
`sheet` — it renders every asset on a checkerboard, which is the only
reliable way to spot bad alpha. Read it, then edit `config.KEEP`.

Extraction is fully automatic: no frame corners and no per-flower seed
points to measure. `config.py` holds thresholds and the curation list,
nothing hand-located.

### Headless checks

```bash
pip install playwright && playwright install chromium
python tools/serve.py &
python tools/check.py --wake
```

Reports frame rate, how much of the field is actually being drawn, and
renders a heatmap of what moved under the cursor.

---

## Layout

```
photos/           the two source photographs (EXIF-rotated on read)
pipeline/
  config.py       thresholds, the colour grade, and which assets are
                  keepers. Nothing in here is hand-located.
  extract.py      photos -> isolated transparent PNGs
  build.py        PNGs -> payload.json -> single-file dist
index.html        the page. One file: markup, style, and the field engine
assets/           extracted cutouts (committed) + generated payload
dist/             self-contained build, opens from file://
tools/            dev server, headless checks
work/             intermediates and screenshots (gitignored)
```

## How the extraction works

1. **Segment.** Foreground is normalised Lab distance from the linen,
   measured on a bilateral-filtered copy so the weave doesn't register as
   signal. The linen reference is the dominant chroma mode of the whole
   panel — *not* a sample of the margins, which silently poisons the whole
   segmentation if any stitching runs to the edge, and on these panels it
   does.
2. **Sort by colour.** Split the foreground into families — dark, green,
   yellow, white, purple, pink. Chroma is what actually separates wool
   here; topology is not.
3. **Cut the blooms.** A bloom is a contiguous patch of *any* petal
   colour. Componenting a single colour shatters the white irises, whose
   petals are separated by purple outlines. Close across whatever crosses
   the bloom, then intersect back with the foreground: crossing **wool**
   is kept, in its own colour, and crossing **linen** is not. An occluding
   stem stays put and reads as a stem lying over the flower.
4. **Cut the grass.** Green stems and leaves are emitted as assets in
   their own right, so the page can scatter grass and flowers at
   independent densities. They remain part of the blooms they belong to.
5. **Ground.** Search both panels for the 512px square with the least
   stitching, inpaint out any strays, then make it tile by rolling half a
   tile and cross-fading the seam. Mirror-tiling is the obvious trick and
   it's wrong — it makes four-fold symmetric blobs that read as wallpaper.

An earlier version rectified off hand-read frame corners and isolated
flowers by eroding until the stems snapped, keeping only the blob nearest
a hand-placed seed. Both are gone. The panels are now shot square-on, so
there is nothing to rectify; and severing plants from each other is no
longer wanted, which turned the hardest stage into the simplest one and
recovered the flowers the old approach had to reject.

## How the page works

Assets are baked once at load into single sprites with their contact
shadow composited in, at the exact size they'll be drawn. Each plant is a
damped spring whose rest position is an ambient wind field (three drifting
sine waves, so gusts travel across the meadow instead of everything
wobbling on the same beat). The cursor adds impulse proportional to pointer
speed and proximity; the trailing rustle is the overshoot as each spring
settles.

Scatter is colonial, not uniform — each asset picks 2–5 patch centres and
60% of plants grow near their own kind. Random flip and lean per instance
keep 18 assets from reading as 18 assets.

A **density governor** samples frame time twice a second and thins the
field uniformly (by a stable per-plant random rank) to hold ~50–60fps.
Fast hardware draws everything; slow hardware degrades instead of
stuttering. `density()` in the console reports what's happening.

## Console handles

| | |
|---|---|
| `regrow()` | resow the field without reloading |
| `density()` | `{quality, sown, drawn}` — governor state |
| `tune(obj)` | apply a saved tuning JSON; returns the current one |

## Pages

Four pages in one document, routed on the hash so the browser's back
button works and each can be linked to directly:

| | |
|---|---|
| `#home` | the wordmark, and the four links under it |
| `#listen` | bandcamp · apple music · spotify, in a stack |
| `#shows` | "stay tuned for upcoming dates" |
| `#shop` | "coming soon" |

`follow` is not a page — it goes straight out to Instagram. Every
external link opens in a new tab, so the field is still standing when
you come back.

Only the active page is in the flow; the rest are `[hidden]`, which is
what keeps the zones honest — a hidden box measures 0×0 and drops
out of the zone pass on its own. On the sub-pages a `<` appears top left
at the wordmark's own size. **Changing page resows the field**, which is
not a side effect to be tolerated but the transition itself: the meadow
grows in from `sizeFrom` around whatever type has just arrived.

The nav holds **one line in landscape and one link per row in portrait**.
Landscape needs a cap on the type size to manage it — the ratio alone
outgrows the window at some width whatever it is set to, and the row
wraps 3+1, which reads like an accident.

**All type that is not the wordmark is set at `--menu`**, one variable on
`:root`: the nav, the listen links, and the sub-pages' messages.
Landscape is `min(--type * .54, 4.2vw)` — the vw cap holds one line.
Portrait swaps that for a **px floor**, `max(--type * .54, 26px)`,
because `--type` is a share of the viewport and on a phone the menu was
landing at 20px while the wordmark it is measured against cannot grow
(already 72% of the screen width). A floor in landscape would push the
row off the screen, hence the split. It is one variable because these
three drifted apart twice while each rule carried its own copy.

## Scale, and a road not taken

**A sprite is a fixed number of pixels wherever it is drawn** — `P.size`
and `SHRINK` have no viewport term — while the type is set in `vw`. On a
phone that used to leave the clearings *smaller than a single bloom*, so
they did nothing: a plant was correctly excluded from a zone and still
covered the words, because only its centre is tested.

The obvious fix is to scale the plants by the same ramp the type uses,
and divide the plant count by that scale squared to hold coverage. That
was built and measured — at 390×844 it gave scale 0.418, blooms 23×25px,
4806 plants against 843, overdraw 7.2× against the laptop's 6.4× — and
then **reverted**, for two reasons worth recording:

- Many small flowers read as **visual noise** where few large ones read
  as a meadow. Proportional correctness is not the same as looking right.
- Five times the plants is five times the physics and five times the
  transforms. Fill was unchanged, but it moved the cost onto the CPU on
  exactly the weakest devices, with `autothin` off.

What carries the fix instead is the **floor on the zone semi-axes**
(below), which is a local correction rather than a global rescale. If
anyone is tempted to try the rescale again: it works, it is only a few
lines, and the reason it is not here is taste and phone CPU, not
correctness.

## Zones

Type sits badly on a bed of flowers: too much colour and too much
silhouette exactly where the eye is trying to resolve letterforms. So
every piece of type gets a clearing, in one of two kinds:

| attribute | |
|---|---|
| `data-zone` | **grass only** — no blooms, no stems, and full grass weight regardless of what the `mix` sliders say. The wordmark, the sub-pages' messages, and every menu link. |
| `data-bare` | **nothing at all**, linen showing through. Currently only the back caret. |

The attribute's **value scales the ellipse**. The four nav links carry
`1.25`, enough that in landscape their clearings overlap into one
continuous strip rather than four separate patches — at 1440px the edges
overlap by 23–38px. With `ZONE_GRASS` down at 0.15 that strip is nearly
bare anyway, so the menus read much as they did when they were literally
`data-bare`; the difference is that a few blades still come through.

**Every semi-axis is floored at `half-box + half-bloom`.** Only a
plant's *centre* is tested against a zone, so a clearing narrower than a
bloom cannot actually keep one off the type — the plant is correctly
excluded and still covers the words. The floor is measured off the
assets, so it tracks `P.size` and the meadow scale. At laptop widths the
proportional pad is already larger and the floor changes nothing.

A grass zone is not a hole in the field, it is a different planting; a
bare one is a hole, and meant to be.

There is no longer one clearing at a fixed place. **Every element
carrying either attribute measures its own box and gets its own
ellipse** — the wordmark, each nav link, each link on the listen page,
the back caret. That is what makes "one zone per link" cost nothing per
page, and `markSize` still scales the clearings because it scales the
type they are measured off.

The corner links are the one exception to the ellipse: their box is a
rectangle, because two of its four edges run off the screen and it reads
as a cleared corner rather than as a rectangle cut out of a meadow.

The pad around the box is **additive in em, not a multiplier**. A
multiplier gives a two-line paragraph twice the margin of a one-line one
and a four-letter word a quarter of the wordmark's; `ZONE_PAD_X` 0.18
and `ZONE_PAD_Y` 0.65 give every piece of type the same margin in its
own type size, and reproduce the previous hand-tuned wordmark clearing
to within a pixel. `ZONE_TOP` (0.60) then shortens the pad **above** the
type so flower heads press closer from that side — the pad, not the
whole semi-axis, or a two-line paragraph loses its top margin to its own
extra height.

`data-zone` goes on an **inline span**, not on the block. A block
stretches to its widest sibling, so an `h1` measured the nav row's width
and the wordmark got a clearing half the screen wide. An inline box is
the union of its line boxes: the text and nothing else.

Space between stacked type is sized so **flowers grow between the
clearings**. Two ellipses stop touching once their centres are further
apart than the pads facing each other — one line-height plus 1.04em —
and everything past that is uncleared field. Each gap is therefore
`proportional term + 48px`, and the constant is the point: a sprite is a
fixed number of pixels tall whatever the viewport, so a gap in em alone
leaves 13px of roof on a phone and nothing can grow in it. Measured, the
band comes out at a flat 48px on every stacked pair from 390px wide to
1440.

Every zone test is done in **visual space, not anchor space**. A plant
is rooted at its foot and drawn upward, so testing where it is rooted
puts the patch a whole plant too high — grass sown along the bottom of
the zone grows out of the top of it, and blooms rooted below reach in.
The cluster decision uses the field's average rise (the asset is not
chosen yet); each plant and each companion stem then uses its own.
With that, every grass zone measures 100% grass and every bare zone
measures empty, across all four pages at laptop, phone and
landscape-phone size.

The grass clearings fill only with whatever clusters happen to centre
inside them, so a top-up pass brings them to `ZONE_GRASS` (0.15) of their
natural density — sowing single blades when the target is above 1,
thinning at random when it is below. Which zone a blade goes to is
picked by **area**, or a small ellipse would get as many blades as the
wordmark's and end up matted. Sowing needs a tighter
crowding radius, since at the default the zone is already packed and
every extra blade is refused.

## Tuning panel

Three links sit in the top-right corner, set in the wordmark's face and
colour so they read as part of the page rather than as chrome:

- **wander** — drift the colors (*"lose the hour on a trail"*). Reads
  **rest** while it is running (*"at the wishing well"*): the
  label names what the click will do, not what is happening. Because of
  that it carries no underline in that state — an underline would be
  saying "you are here" about a button that means "leave" — and instead
  pulses slowly to read as armed. Hover still underlines, and reduced
  motion gets a static dim rather than nothing. The row is anchored by
  its right edge, so the shorter word shrinks it leftward and
  `regrow` / `mod` stay put.
- **regrow** — resow the meadow
- **mod** — toggle the panel

They stay put while the panel is open, so `mod` is always there to close
it again. **Space** toggles wander, `c` toggles the panel and `Esc`
closes it; `#tune` in the URL opens it on load. The panel itself is
hidden by default.

Space is ignored while a button or slider has focus — those already
answer to space themselves, and handling it twice would toggle twice and
land back where it started.

**Wander** walks the four hue and saturation sliders on their own, each
bouncing between its bounds on its own interval — hue every 0.25s and
0.40s, saturation every 0.65s and 0.75s, all divided by `wander speed`
(2.0 by default, so twice that pace). The intervals are deliberately
unequal so the four never line up, and the combinations end up somewhere
nobody picked. Touching any of those four sliders takes back control and
stops it; toggling it off leaves the values where they landed, so you can
`copy(tune())` on a combination you like.

The wordmark doesn't cycle blindly — it **reads what is behind it**. Six
times a second wander downscales the box the wordmark occupies into a
24×12 offscreen canvas, averages it, and steers the text toward a
contrasting colour, easing rather than snapping.

Straight RGB inversion is the obvious approach and it fails: invert a
mid grey and you get a mid grey. Instead it takes the **complementary
hue** for colour separation and flips **lightness** to whichever end the
backdrop is not, for luminance separation. The second half is what keeps
it legible; the first is what makes it interesting. A pink-lilac field
gives deep green, a tan one gives blue.

The cost is the readback, not the arithmetic — `getImageData` forces a
GPU-to-CPU sync. Reading 288 pixels rather than the canvas keeps one
probe at **~0.8ms**; at 12.5Hz that is **1.02% of the frame budget**,
and the text tracks its target to within 9.6° of hue on average. 60fps
with wander running, worst frame 21ms against 18 idle.

`PROBE_EVERY` (0.08s) and `MARK_EASE` (5.0) are the two knobs: how often
it looks, and how hard it chases what it sees. The corner links follow it,
so the colour it stops on is the one you copy.

### Breathing

Wander changes the blooms' **size** as well as their colour. Flowers are
picked at random — 200 a second, so about 500 of the ~1100 are moving at
any moment — and each eases to a new size and stops there. Both moves are
relative to where the plant already is: up multiplies by **1.5**, down
**halves**. A bloom at the grow-in end size blows up to 150% of it, one
sitting at 20% goes to 30%, and three or four *down* draws in a row put
it at the grow-in **start** size — the same speck the whole field begins
as on load. The band is `sizeFrom/size` to 1.5.

It is a **draw-time scale**, like grow-in and for the same reason: the
sprite is already blitted through a scaling `setTransform`, so the extra
factor costs one multiply. Measured on a real GPU, 61fps idle and 61fps
with wander and breathing both running; mean sprite area actually comes
out slightly *below* rest, so there is no overdraw cost.

**The coin is not 50/50, and that is not a style choice.** Halving is a
bigger move than multiplying by 1.5 — `ln 2` against `ln 1.5` — so a fair
coin drifts the whole meadow downward and it settles at a fraction of its
size after a couple of minutes, which reads as the field wilting rather
than breathing. `BREATHE_FAIR` (0.631) is the weighting that leaves the
walk standing still, derived from the two step sizes so it stays right if
they are re-tuned. `BREATHE_REVERT` adds a gentle pull back toward the
sown size on top. Measured, the field's mean size holds at 0.90 from 30s
to 60s while individual blooms span 0.33 to 1.5.

Breathing waits for the **grow-in** to finish — the field is already
ramping from `sizeFrom` to `size`, and a second scale animation on top of
that just fights it. A regrow resets every plant to 1 and starts the wait
again. Turning wander off eases them all home rather than snapping.

It steps rather than glides on purpose. Re-colouring continuously cost
**15.4ms of a 16.7ms frame** — measured, and far more than the synchronous
timings implied, because allocating canvases and running the shadow blur
bill long after the call returns. Stepping, plus caching the contact
shadow (it doesn't depend on colour) and scaling before colouring rather
than after, took that to 11.9ms and removed all per-frame allocation.

> Those figures come from headless Chromium, which has **no GPU** and
> rasterises in software, so they run heavily pessimistic. On a real GPU
> the page holds a flat 60fps with wander running — measured at density
> 2.5 (4630 plants) and size 1.7, worst frame 19ms, and still 60fps with
> `wander speed` pinned at 6x, governor idle. Benchmark canvas work with
> `headless=False` — see the note in `CLAUDE.md` about a 26x regression
> that headless reported as an improvement.
>
> If it ever does get heavy, the knob is the `every` values for `fgHue`
> and `fgSat` in `WANDER`: those two re-colour 26 sprites, while the two
> ground walkers only redo one small tile. Turning **auto-thin** on also
> protects frame rate, and it is off in the current defaults.

**Alt-click any control to restore its default**, the way Logic does it.
Works on sliders, colour swatches and the checkbox.

Some settings only take effect when the field is resown, and resowing
mid-drag would be jarring and expensive. Those **queue a regrow instead**:
two quiet seconds after the last such change, whichever control it was,
the field regrows itself. Touching another one restarts the clock, so a
run of adjustments costs one resow rather than ten. The note line reads
`regrowing…` while one is pending. Hitting `regrow` yourself, or `reset`,
cancels it.

The eight that queue one: `density`, the five `mix` sliders, `size start`
and `grow seconds`. The last two only show during the grow-in ramp, which
has already finished by the time you touch them.

Changing **page** resows immediately instead of queueing — the clearings
belong to the type that is on screen, so a stale one would be a clearing
around words that are no longer there.

| group | |
|---|---|
| **rustle** | amount (0–8; the drawn swing saturates at ~73° from 4 up, see below) |
| **wander** | speed of the colour drift |
| **meadow** | ground hue, ground sat, plant hue, plant sat, plant gain, ground zoom, density |
| **plant mix** | relative amount of purple / white / yellow / pink flwrs, and grass |
| | a live fps / drawn / quality readout |

There is no `copy json` button any more — `tune()` with no argument
returns the current set, so `copy(tune())` in the console does the same
job and `JSON.stringify(tune(), null, 2)` gives it formatted. The
paste-it-back-into-`DEFAULTS` workflow is otherwise unchanged.

Several settings are live in `P` and travel in `tune()` but no longer
have controls: `speed`, `settle` and `radius` (rustle), `bgGain` and
`bgTint` (ground), `markSize` and `markColor` (the type), and `autothin`.
Reach them with `tune({…})`. Two are worth knowing about:

- **`bgGain` sits at 1.22**, just past the ~1.2 where the output clamp
  starts eating `bgHue` on pale material. If the ground hue ever seems
  unresponsive, that is why — and `tune({bgGain: 1.0})` is now the only
  way to fix it.
- **`autothin` is 0**, so the governor is off and nothing thins the
  field. `tune({autothin: 1})` turns the frame-rate protection back on.

**Rustle amount** is a gain on the drawn angle, capped by `SWING_MAX`
(1.5 rad, ~73° once the 0.85 stem factor is applied). Measured peak swing
against the setting: 6.7° at 1, 15.8° at 2, 48.5° at 3, then **73.1° at
4, 5, 6 and 8** — the raw angle keeps climbing (92.9° → 194.8°) but the
clamp takes it. So above 4 no single plant swings further; what does
still change is how *much* of the field reaches that swing, since the
impulse grows with the square of the setting. Raise `SWING_MAX` if the
top of the slider should move the peak too — but past ~2.5 rad plants
swing beyond horizontal and read as falling over rather than bending.

**Hue** is the one-slider mood control. It rotates every colour at once
and keeps the relationships between them, so the wool still reads as wool
a long way round. The ground sweeps olive → teal → periwinkle →
chartreuse across a full turn. **Sat** runs from grey to lurid.

**Gain** is brightness and **tint** is a colour cast, kept from the
earlier design. The tint is normalised to its brightest channel, so it
carries hue only and white is exactly neutral at any gain.

All four compose into a single 3×3 colour matrix, applied in one pass:
gain and tint, then hue, then saturation. At the defaults it is exactly
the identity, so nothing is touched until you move something.

> **Gain and hue fight each other.** Gain above ~1.2 pushes pale material
> out of gamut, and the clamp that brings it back flattens the hue away.
> At `bgGain 1.51` the linen computes to `[343,313,202]` — two channels
> clipped — so the ground hardly responds to hue at all. Saturated,
> mid-tone assets are fine: a purple iris at `fgGain 1.44` is
> `[216,79,230]`, nothing clipped, and rotates to a deep green at 180.
> **If you want to use hue on the ground, drop `bgGain` to about 1.0.**

**Rustle amount** is a gain on the drawn angle, not just a harder shove.
Driving it through the impulse alone doesn't work — a plant is inside the
brush for only a few frames and the spring pulls back the whole time, so
the response is either dead at the bottom or a cliff at the top. Measured
lean at the maximum setting: 1.2° / 3.5° / 10.3° / 29.4° / 69.2° across
0.5–4.

**Mix** multiplies the pool for one colour of bloom, so the colours trade
against each other rather than adding plants. It exists because role
weighting alone cannot express it — the purple and white irises are both
role `flower`. Note that the crocuses are role `small`, of which there
are only three assets, so each carries a high per-asset weight; purple
therefore starts out well ahead of white. Measured counts out of ~3200:

| purple / white | purple | white |
|---|---|---|
| 0.80 / 1.20 | 382 | 131 |
| 0.50 / 1.60 | 284 | 215 |
| 0.35 / 2.00 | 198 | 273 |

The **words** group is gone from the panel. `markSize` and `markColor`
still exist in `P` — the first scales the type and, through it, every
clearing; the second is what wander writes the colour it computes back
into — they just no longer have controls. Both still travel in
`tune()`, and `tune({markSize: …})` still works.

**Grow in** ramps the field up from `size start` to `size end` over
`seconds`, on load and on every regrow. It is a draw-time scale — sprites
are baked once at `size end` — so it costs nothing per frame.

**Copy json** puts the whole set on the clipboard. Paste it back and it
can be made the default in `DEFAULTS` at the top of the script; or apply
it at runtime with `tune({...})`, which also understands the older
`br/bg/bb` colour format.

Density needs a **regrow**; everything else applies live.

*Auto-thin* is the density governor. It samples frame time and drops
plants to hold frame rate — if the field looks like it is losing patches
a few seconds after load, that is what is doing it. Turn it off to draw
everything sown, whatever it costs.

Keys worth tuning live at the top of their sections in `index.html`:
`SHRINK`, `WEIGHT`, `BRUSH`, `FORCE`, and the sowing target inside `seed()`.
