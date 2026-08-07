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
python tools/serve.py        # -> http://localhost:8000/src/
```

`assets/` is committed, so you do **not** need to run the extraction to
work on the site. Edit `src/index.html` and reload — the page fetches
`assets/payload.json` at runtime. Re-run `build.py` only when the assets
or `pipeline/config.py` change.

### Re-running the extraction

```bash
python pipeline/extract.py all
```

Stages, runnable individually: `grid`, `flatten`, `flowers`, `foliage`,
`linen`, `sheet`. Intermediates go to `work/` (gitignored). Always finish
with `sheet` — it renders every asset on a checkerboard, which is the only
reliable way to spot bad alpha.

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
  config.py       every hand-measured number: frame corners, flower seed
                  points, which assets are keepers, the colour grade
  extract.py      photos -> isolated transparent PNGs
  build.py        PNGs -> payload.json -> single-file dist
src/index.html    the page. One file: markup, style, and the field engine
assets/           extracted cutouts (committed) + generated payload
dist/             self-contained build, opens from file://
tools/            dev server, headless checks
work/             intermediates and screenshots (gitignored)
```

## How the extraction works

1. **Rectify.** Perspective-warp off the frame corners so each panel is a
   flat 1300×3050 rectangle. ~87px per cm of real embroidery.
2. **Relight.** Flatten luminance against a heavy blur of itself. Only
   luminance — correcting the full colour field turns the pink irises mint.
3. **Segment.** Foreground is normalised Lab distance from a linen
   reference sampled at the panel margins, measured on a bilateral-filtered
   copy so the weave doesn't register as signal.
4. **Isolate.** The hard part. Everything connects through stems, so a
   flood fill from one flower grabs the whole plant. Erode until the stems
   snap, keep the blob nearest the seed point, reconstruct it back under
   the mask. Erosion radius must exceed half the stem width (~40px here).
   The extractor sweeps cut depth and scores each result on how much of the
   silhouette runs along the crop border — a real flower silhouette never
   does, so border contact is a reliable proxy for "grabbed the neighbours".
5. **Ground.** Search both panels for the 512px square with the least
   stitching, inpaint out any strays, then make it tile by rolling half a
   tile and cross-fading the seam. Mirror-tiling is the obvious trick and
   it's wrong — it makes four-fold symmetric blobs that read as wallpaper.

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

Keys worth tuning live at the top of their sections in `src/index.html`:
`SHRINK`, `WEIGHT`, `BRUSH`, `FORCE`, and the sowing target inside `seed()`.
