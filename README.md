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

## Companion documents

| | |
|---|---|
| `CONTEXT.md` | orientation for a new session — paste it in cold |
| `CLAUDE.md` | the trap list: decisions made, and what broke |
| `GAME.md` | speculative notes on the wander clock and a game layer. Nothing in it is implemented. |

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

## The two grades

`config.GRADE` colours every plant asset; `config.GRADE_GROUND` colours
the linen tile. They were one setting until it became clear the two
materials want opposite things from it.

A flower is a saturated mid-tone with a channel down near zero — average
`[238,169,39]`, HSV saturation 0.838 — so it has room to be lifted. The
linen is a pale near-neutral whose three channels sit within ~50 of each
other, and lifting *that* just walks all three into the 255 ceiling
together. When they pin, the gap between brightest and darkest channel
collapses and the tile goes toward white, which is chroma destroyed, not
gained.

With one shared grade (`saturation 1.26, value 1.16`) the tile shipped at
`[187,198,150]`: HSV saturation 0.244 against the flower's 0.838, and
luminance 0.755, which left `bgGain` clipping from 1.23 — one hundredth
above its own 1.22 default. So the ground could never get vivid. `sat`
had almost no chroma to multiply, and `gain` actively removed what there
was.

`GRADE_GROUND` (`saturation 2.20, value 0.90, contrast 1.04`) darkens
instead of lifting, and saturates harder:

| | tile | HSV sat | luminance | max reachable runtime sat | clips from |
|---|---|---|---|---|---|
| shared grade | `[187,198,150]` | 0.244 | 0.755 | 0.584 | gain 1.23 |
| ground grade | `[140,157,86]` | 0.449 | 0.580 | **1.000** | gain 1.50 |

Measured live at `bgGain 1.22` with saturation at maximum, the ground
computes to `[143,197,0]` — fully saturated, with **no** clipped
channels — where the old tile managed `[217,254,104]` at 0.589.

**The ground defaults moved with the tile**, to `bgGain 1.65` /
`bgSat 0.38` — more gain and less saturation than before, which is the
opposite of what the pale tile wanted and exactly what a darker, more
saturated one needs. That lands the resting ground at `[223,235,188]`,
luminance 0.898, near the old resting mood, with 0 clipped channels and
the clipping onset out at 1.79. Hue is genuinely alive there now: 0° is
pale green, 90° cyan, 180° lilac, 270° pink, all four distinct.

These are the least aggressive numbers that get there. Pushing further
(2.5 / 0.86) moves the clipping onset to 1.55 but darkens the resting
ground more than the problem warranted. Saturation clipping inside the
tile is 0.72% of pixels and the weave contrast holds (V std 32.0 → 26.7),
so the texture survives; past about 2.5 it starts to flatten.

The plants are deliberately untouched — `GRADE` is exactly as it was.

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

Five pages and a visualizer in one document, routed on the hash so the browser's back
button works and each can be linked to directly:

| | |
|---|---|
| `#home` | the wordmark, and the four links under it |
| `#listen` | bandcamp · apple music · spotify, in a stack |
| `#shows` | "stay tuned for upcoming dates" |
| `#shop` | "coming soon" |
| `#viz` | the visualizer, below — also served at `/viz` |

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

## The visualizer

`#viz`, also reachable at `dayspells.com/viz`. A screen with nothing on
it, meant to be left running.

**No type.** `showView` hides every element whose `data-view` does not
match the name, and nothing claims `viz` — so a route with no view of
its own hides the lot. That is the whole implementation; `body.viz` then
hides the chrome that lives outside the views (corner links, hint, back
caret). The panel is not hidden, because it already is: `c` still opens
it, so it is opt-in rather than something on screen.

**Wander starts by itself**, deferred to the end of `boot()`. `showView`
runs before the canvas has been sized, and `setWander` samples the
canvas to pick the wordmark's contrast colour.

**0–3 glades**, random position and size, redrawn on every resow.
Grass-only, exactly like `data-zone` — there is simply no type to
measure them off, so they are invented instead. Semi-axes are 0.08–0.18
of the **short** side, so they keep their proportions on a phone rather
than stretching with the window.

Zero is in the range on purpose: a sow with no clearings at all reads as
unbroken field, and glades on every single sow made them a feature of
the page rather than something that happens. An empty list is safe all
the way down — `inAny()` returns false on it and the top-up pass is
guarded by `zones.length`. Measured over 200 sows: 59 / 57 / 39 / 45 for
0 / 1 / 2 / 3, no bloom intrusions, and an empty sow still sowing its
full field.

They do not overlap, and that took more than a distance check.
Separation is tested on each glade's **largest** semi-axis, since two
ellipses clear each other only when their centres are further apart than
the sum of their bounding radii — comparing widths alone lets a tall
glade run through its neighbour. On top of that: biggest placed first
(the big one dropped into a field of small ones is the placement that
fails), and a shrink-and-retry so a run of large draws degrades in size
rather than in separation. Measured **0 overlapping pairs** in 2721 across 200 draws each at
1280×800, 390×844 and 844×390, and 0 in 174 again after the count
dropped to 0–3.

**A doodle drives the brush.** It writes `ptr.x/y` and nothing else,
which is the point: the frame loop already differences those into a
smoothed velocity, so the rustle, the brush radius and the trailing
overshoot behave exactly as they do under a real hand.

It is a **pen**, not a sequence of hops — and getting there took two
wrong versions worth recording, because each failed differently and
neither was obvious from the code.

The first moved point to point: pick a target a short hop away, ease to
it, stop, rest a second, repeat. Every ingredient was reasonable and it
read as *little isolated twitches*. What makes a doodle look human is
not where it goes but that it never stops and never travels straight.

The second fixed the stopping and not the straightness. Angular velocity
came from a damped random walk, `w += noise·dt` with a 0.90 per-frame
decay — which settles at a standard deviation of about **0.07 rad/s**,
four degrees of turn in a whole second. Measured, the path came out at a
chord-over-length of **0.99** over one-second windows: a straight line.
Getting a usable bend that way needs a noise term around 68 rad/s², at
which point the constant means nothing to anyone reading it and it is
frame-rate dependent besides.

So curvature is **set, not integrated**: three incommensurate sines
summed, with `DOODLE_CURL` as a plain "radians per second of bend".
Phases re-roll per reset so it never retraces a figure. The pull toward
its target **saturates**, because left proportional a 180° course error
asks for π·`PULL` rad/s and the pen snaps round on the spot — the one
motion a hand never makes. And it **reflects** off the edges rather than
clamping: clamping alone lets a steeply-arriving pen keep its heading
and slide along the wall, and a dead-straight run down the side of the
screen gives the whole thing away. That showed up as a 400px horizontal
line across the top of the first trace.

It is also **made to cover the screen**. Left to curl freely a random
walk loiters and a whole side goes untouched for minutes. A 6×4 grid
records when each cell was last visited and the pen re-aims at a stale
one every few seconds — picked as the oldest of five random cells, not
the oldest overall, which would turn it into a lawnmower sweeping in
order.

Measured over 45s at 1280×800: **21 of 24 cells visited**, 8.1 screen-
widths of travel, speed 90–236 px/s (it never stops), chord-over-length
0.96 / 0.88 / 0.79 over 1s / 2s / 4s windows, and **10 frames out of
2700** anywhere near an edge.

This **replaces** the `ghost` Lissajous rather than joining it. That gust
is a demo for someone who has not touched the page — it sweeps the same
figure forever, which is fine for eight seconds and obvious on a screen
left running.

The **ghost** group in the panel drives it on any page: an `enable`
checkbox and a `speed` slider. Speed scales `dt`, not `doodle.spd` — a
pure time dilation, so the pen traces the same figure sooner. Scaling
the speed alone widens every curve instead (turn radius is speed over
turn rate) and the doodles straighten out as they get faster. The
default is **2.5**: 1.0 is the pace it was first tuned at and reads as
too languid for someone playing with the page, 4 overshot. Measured
travel: 158 px/s at 1, 183 at 2.5, 644 at 4. `enable` is forced on in
the visualizer and restored on the way out; a real pointer takes the
brush back, and after `GHOST_IDLE` of stillness the hand resumes —
unless the checkbox was deliberately unchecked, which `ghostMuted` keeps
distinct from a pointer simply arriving.

**It resows itself** every 45–60s, counted in the frame loop rather than
on a timer, so a backgrounded tab does not queue up a burst of regrows
to run the moment it comes back.

Two settings are **borrowed** for the mode and restored on the way out,
since both are global and travel in `tune()`:

- **grow-in at 5s** rather than the site's 6. The ramp is the field
  arriving, not the thing you are watching — at 10s it was most of what
  you ever saw. On a 45–60s cycle it is a brief opening and then the
  better part of a minute of settled field, which is where the wander
  and the breathing actually show.
- **final size at 1.275**, a quarter under the site's 1.70. The
  visualizer is watched rather than read, and at full size the blooms
  crowd the frame; smaller ones let the scatter and the glades read as
  landscape instead of as texture. Unlike the gains this is *geometry* —
  sprites are baked at `P.size`, so `ensureBake` derives `a.dw`/`a.dh`
  from it — which is why borrowing it re-bakes the plants both ways. A
  bloom measures 46×61px here against 61×82 on the site.

`/viz` is a redirect stub at `viz/index.html`. The site is one file and
GitHub Pages has no rewrites, so a real page at that path would mean
shipping a second copy of the whole engine and keeping the two in step.
The stub costs a visible `/#viz` in the address bar afterwards.

`clearings()` in the console returns the ellipses the last sow actually
used — the one part of a sow you cannot see directly, since a bloom that
was correctly excluded and a bloom that was never sown there look the
same.

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

## Where the knobs are

Two places, and the split is deliberate.

**`DEFAULTS`**, near the top of the script, is what the panel edits and
what `tune()` reads and writes — every value with a slider, plus the few
that are live in `P` but have no control.

**`TUNING`**, immediately after it, is everything else worth adjusting:
the visualizer's cadence and borrowed sizes, the glade shape and count,
the gain-roll odds and ranges, the automated hand, breathing, and the
zone pads. These used to be scattered through the file beside the code
they govern, which reads well and adjusts badly. The values now sit
together; the reasoning for each still lives beside its code.

Changing one and reloading is the whole workflow — `index.html` is the
site, there is no build step for the page. Re-run `pipeline/build.py`
before committing so `dist/` keeps up.

Two sets stayed put on purpose: the `WANDER` table, because it carries
per-walker state as well as intervals and belongs with its stepper; and
the engine constants `SHRINK` / `WEIGHT` / `CLUSTER` / `FORCE` /
`SWING_MAX` / `BRUSH`, which shape the field itself rather than its
behaviour over time.

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
it again. **Space** toggles wander, `m` toggles the panel and `Esc`
closes it; `#tune` in the URL opens it on load. **`f` goes fullscreen**
— the Fullscreen API on `documentElement`, so the page takes the whole
screen with no tab strip or address bar, and the panel comes with it.
It has to come from a user gesture, which is why it is a key and not
something the visualizer does for itself on the way in; entering fires a
resize, which resows, exactly as dragging a window does. Not available
on iOS Safari, which only fullscreens video — the route there is Add to
Home Screen with a `display: standalone` manifest, which the site does
not have yet. `m` is the only way into
the panel in the visualizer, where the corner links are hidden. `c` and
`j` capture settings — see below. The panel itself is
hidden by default.

Space is ignored while a button or slider has focus — those already
answer to space themselves, and handling it twice would toggle twice and
land back where it started.

**Wander** walks the four hue and saturation sliders on their own, each
bouncing between its bounds on its own interval — hue every 0.1961s and
0.1333s, saturation every 1.083s and 1.000s, all divided by `wander speed`
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

### The gain roll

Ground **and** plant brightness are both re-rolled on every resow, and
only on a resow. No clock, no ramp — the field is being replaced in that
same frame, so the light snapping with it reads as one event. Easing it
instead smears one cut over five seconds and puts the light out of step
with the field it belongs to.

The ground rolls three ways, equally likely; the plants follow from that
roll rather than rolling separately:

| ground | | plants |
|---|---|---|
| **dark** | 0 | between the slider's value and full |
| **home** | whatever `ground gain` was when wander started | between the slider's value and full |
| **bright** | 80–100% of the slider's maximum | **0–5% of full** |

The split is **20 / 40 / 40** — dark is the rarest, and `home` and
`bright` stay level with each other. It is written as `SWELL_ODDS`,
three *weights* that are normalised at roll time rather than a pair of
cumulative cutoffs, so changing one does not silently resize another.
Measured over 3000 rolls: 20.8% / 39.5% / 39.7%.

The pairing is the point. Against a blown-out ground the plants go
very nearly black — measured across 60 bright rolls, 0.03% to 4.99% of
full, a peak gain of 0.10 — and the field reads as silhouettes cut out
of light;
against a dark or ordinary ground they stay the brightest thing on
screen. Rolling the two independently would give washed-out flowers on a
washed-out ground a third of the time — the one combination with nothing
to look at.

Bright lands between 80.1% and 99.8% of max. Across six live auto-resows: ground 1.76 / 1.98
with plants 0.19 / 0.29, and ground 0 / 0 / 1.22 with plants 1.72 / 1.80
/ 1.60 — the pairing holds every time.

`bright` is a range rather than the maximum because the top of the
slider clips the linen to flat white; backing off a little keeps some
weave. Both maxima are read off the sliders' own `max`, the way
`syncWanderBounds` reads the walkers' bounds, so widening a control
widens this with it.

It only rolls while wander is running — the gains are part of the drift,
not something a plain regrow should touch. `resize()` and `fonts.ready`
call `seed()` directly and are deliberately not resow triggers; a window
drag re-rolling the light would be absurd. Both gains go home when
wander stops, unlike hue and saturation, which are left where they land
so `copy(tune())` captures a look.

Both extremes stay readable with no special handling: the wordmark
derives its colour from the backdrop, so it flips light over the black
and dark over the white on its own.

> An earlier version of this was a five-phase machine on its own timer —
> wait, fall to black, hold, rise, settle home. Two phases, three timers
> and an easing function came out when it moved onto the resow.

### Breathing

Wander changes the blooms' **size** as well as their colour. Flowers are
picked at random — 200 a second, so about 500 of the ~1100 are moving at
any moment — and each eases to a new size and stops there. Both moves are
relative to where the plant already is: up multiplies by **1.2**, down
**halves**. The two ends are deliberately lopsided — growth is gentle
and capped close to the sown size while shrinking is still a halving all
the way down to the grow-in start size, so the field carries a
scattering of small flowers at any moment. `BREATHE_UP` and `BREATHE_HI`
move together: a step that overshoots the ceiling would make the ceiling
the only size a grown bloom can hold. Measured over 48s: mean holds at
0.72–0.84 with no drift, individuals span 0.13–1.2, and 11–20% of blooms
sit below half their sown size at any moment. A bloom at the grow-in end size blows up to 150% of it, one
sitting at 20% goes to 30%, and three or four *down* draws in a row put
it at the grow-in **start** size — the same speck the whole field begins
as on load. The band is `sizeFrom/size` to 1.2.

It is a **draw-time scale**, like grow-in and for the same reason: the
sprite is already blitted through a scaling `setTransform`, so the extra
factor costs one multiply. Measured on a real GPU, 61fps idle and 61fps
with wander and breathing both running; mean sprite area actually comes
out slightly *below* rest, so there is no overdraw cost.

**The coin is not 50/50, and that is not a style choice.** Halving is a
bigger move than multiplying by 1.5 — `ln 2` against `ln 1.5` — so a fair
coin drifts the whole meadow downward and it settles at a fraction of its
size after a couple of minutes, which reads as the field wilting rather
than breathing. `BREATHE_FAIR` (0.792 at the current steps) is the weighting that leaves the
walk standing still, derived from the two step sizes so it stays right if
they are re-tuned. `BREATHE_REVERT` adds a gentle pull back toward the
sown size on top. Measured, the field's mean size holds at 0.72–0.84 from 0s
to 60s while individual blooms span the full 0.13 to 1.2 band.

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
| **meadow** | ground hue, ground sat, ground gain, plant hue, plant sat, plant gain, ground zoom, density |
| **grow in** | final size, seconds |
| **ghost** | enable, speed — the automated hand, on any page |
| **plant mix** | relative amount of purple / white / yellow / pink flwrs, and grass |
| | a live fps / drawn / quality readout |

## Capture: `c` and `j`

The old `copy json` button is now two keys, and the difference that
matters is that captures form a **list**.

| | |
|---|---|
| `c` | snapshot the current settings onto a running list |
| `j` | copy the whole list to the clipboard as JSON |

Wander walks the colours somewhere good and then keeps walking, so by
the time you have decided you liked it, it is gone. Tapping `c` costs
nothing and can be done on the way past; choosing between the captures
happens later, in a text editor, instead of racing a moving field. Both
keys work on every page, including the visualizer — where `c` is the
only feedback you get, since the corner links are hidden.

A brief line confirms each one (*"3 drawn from the well"*, *"the json of
your dreams has been copied from the well"*). It is transient, so it
does not put standing text on a page whose whole point is having none.

The payload is a JSON **object**, so it can say what it is:

```json
{ "captured": "2026-08-11T…", "count": 3, "captures": [ { … }, { … } ] }
```

Each entry is the same shape `tune()` returns and accepts, so any one of
them pastes straight back into `tune({…})` or into `DEFAULTS`.

**Captures see through the visualizer's borrows.** `#viz` swaps
`P.grow`, `P.size` and `P.ghostOn` for its own values, so a raw snapshot
taken there would record 5 / 1.275 / 1 — the visualizer's settings, not
yours. Since captures exist to be pasted back into `DEFAULTS`, a paste
that silently moved the site's grow-in and plant size to the
visualizer's would be a trap. Everything genuinely live is captured
as-is: the wander colours, the gains rolled at the last resow, the mix.
`tune()` is deliberately unchanged and still reports live `P`, borrows
included — its job is what the field is doing now, not what you would
want to return to.

The clipboard write can fail (an insecure origin, a stale gesture, a
denied permission), so the confirmation waits on the promise rather than
claiming success; on failure it says so and leaves the JSON in the
console. Console handles: `captures()`, `capturesJSON()`,
`clearCaptures()`. Reloading empties the list.

**`c` no longer opens the panel** — `m` does, as does the corner link
and `#tune` in the URL. `Cmd`/`Ctrl` held down is ignored by both keys,
so the browser's own copy still works.

Several settings are live in `P` and travel in `tune()` but no longer
have controls: `speed`, `settle` and `radius` (rustle), `bgTint` and
`fgTint`, `markSize` and `markColor` (the type), `sizeFrom` (the
grow-in's start size), and `autothin`.
Reach them with `tune({…})`. One is worth knowing about:

- **`autothin` is 0**, so the governor is off and nothing thins the
  field. `tune({autothin: 1})` turns the frame-rate protection back on.

**`ground gain` does have a slider now**, sitting with `ground hue` and
`ground sat` and mirroring `plant gain`. It is the slider to reach for
when the ground hue seems unresponsive: the default 1.22 already sits
above the ~1.2 where the output clamp starts eating `bgHue` on pale
material, and pulling it toward 1.0 gives the hue its travel back. The
tile measures `[181,188,156]` at gain 1.0 and `[221,229,191]` at 1.22;
by 1.6 two channels are pinned at 255 and by 2.0 the linen is white.

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

> **Gain clips a pale material toward white, and that destroys chroma.**
> Vivid means a big gap between the brightest and darkest channel. A
> flower has a channel down near zero, so the gap survives any gain; a
> near-neutral linen has all three within ~50 of each other, so gain
> walks them into the 255 ceiling together and the gap collapses. On the
> old tile at max saturation the ground reached 0.589 at gain 1.0 and
> 1.22, then fell to 0.463 at 1.6 and 0.328 at 2.0 — and at gain 2.0
> with saturation at rest it computed to exactly `[255,255,255]`, white.
>
> Saturation compounds it, because `out = lum + s·(in − lum)` scales a
> pixel's distance from its own grey and a near-neutral has almost none
> to scale. The old tile started at HSV saturation 0.244 against a purple
> iris's 0.838 — the flowers began 3.4× more saturated.
>
> **That is fixed at the source** — see `GRADE_GROUND` below. The tile is
> darker and far more saturated, so both runtime sliders have something
> to work with. The rule still holds for any tile though: past the
> clipping onset, gain takes colour away rather than adding it.

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
