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

## Grass zones

The wordmark sits in a patch where **only grass is sown**, and the
corner links sit in one where **nothing is sown at all** — bare linen.
For the wordmark, — that means no blooms, no stems, and full grass weight
regardless of what the `mix` sliders say. For the links it means exactly
nothing: two of that box's four edges run off the screen, so it reads as
a cleared corner rather than a rectangle cut out of a meadow. Type reads badly over a bed
of flowers: too much colour and too much silhouette exactly where the
eye is trying to resolve letterforms. It is not a hole in the field, it
is a different planting.

Every zone test is done in **visual space, not anchor space**. A plant
is rooted at its foot and drawn upward, so testing where it is rooted
puts the patch a whole plant too high — grass sown along the bottom of
the zone grows out of the top of it, and blooms rooted below reach in.
The cluster decision uses the field's average rise (the asset is not
chosen yet); each plant and each companion stem then uses its own.
With that, the zones measure 100% grass.

The zone is wider than it is tall — `ZONE_X` 1.44 against `ZONE_Y` 1.25
— because the wordmark is a long word. It is also cut short above the
type (`ZONE_TOP` 0.75) so flower heads come closer from above, and left
full below.

The clearing fills only with whatever clusters happen to centre inside
it, which leaves it thinner than the field around it, so a top-up pass
brings the clearing to `ZONE_GRASS` (0.84) of its natural density —
sowing single blades when the target is above 1, thinning at random
when it is below. Sowing needs a tighter crowding radius, since at the
default the zone is already packed and every extra blade is refused.

## Tuning panel

Three links sit in the top-right corner, set in the wordmark's face and
colour so they read as part of the page rather than as chrome:

- **wander** — drift the colors (toggle)
- **regrow** — resow the field
- **tweak** — toggle the panel

They stay put while the panel is open, so `tweak` is always there to
close it again. `c` toggles and `Esc` closes as well, and `#tune` in the
URL opens it on load. The panel itself is hidden by default.

**Wander** walks the four hue and saturation sliders on their own, each
bouncing between its bounds on its own interval — hue every 0.25s and
0.40s, saturation every 0.65s and 0.75s, all divided by `wander speed`
(2.0 by default, so twice that pace). The intervals are deliberately
unequal so the four never line up, and the combinations end up somewhere
nobody picked. Touching any of those four sliders takes back control and
stops it; toggling it off leaves the values where they landed, so you can
`copy json` a combination you like.

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
it looks, and how hard it chases what it sees. The corner links follow it, and the swatch
keeps up, so the colour it stops on is the one you copy.

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
four quiet seconds after the last such change, whichever control it was,
the field regrows itself. Touching another one restarts the clock, so a
run of adjustments costs one resow rather than ten. The note line reads
`regrowing…` while one is pending. Hitting `regrow` yourself, or `reset`,
cancels it.

The eight that queue one: `density`, the five `mix` sliders, `size start`
and `grow seconds`. The last two only show during the grow-in ramp, which
has already finished by the time you touch them.

`words size` deliberately does **not**. It scales the clearing sown
around the name as well as the type, but the type resizes instantly and
having the field re-scatter underneath it a few seconds later is worse
than a stale clearing. The clearing catches up on the next regrow.

| group | |
|---|---|
| **rustle** | amount, speed, duration, radius |
| **wander** | speed of the colour drift |
| **ground color** | hue, sat, gain, tint |
| **plant color** | hue, sat, gain, tint |
| **words** | size and colour of the name |
| **mix** | relative amount of purple, white, yellow, pink, grass |
| **field** | ground zoom, density |
| **grow in** | size start, size end, seconds |
| | auto-thin, and a live fps / drawn / quality readout |

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

**Words size** also widens the clearing that gets sown around the
name, so a bigger wordmark doesn't end up sitting in undergrowth. That
part lives in `seed()`, so it takes a **regrow** to show.

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
