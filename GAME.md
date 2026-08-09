# wanderlust — notes toward a game layer

**Status: speculative. None of this is implemented.** This is a design
document, written up from a conversation so the reasoning is not lost.
Read `CONTEXT.md` for the project and `CLAUDE.md` for what breaks.

The question that started it: *wander is deterministic, so could the page
show a timecode — and could that timecode eventually unlock things?*

---

## 1. Is wander deterministic?

Half. And the half that isn't is the interesting part.

### The state machine is deterministic
Four walkers, each with a value, a direction, and bounds it bounces off:

```js
const WANDER = [
  {k:'bgHue', step:5/3,  every:0.25/3, lo:0, hi:360, dir: 1},
  {k:'fgHue', step:5/3,  every:0.40/3, lo:0, hi:360, dir:-1},
  {k:'bgSat', step:0.06, every:1.083, lo:0, hi:2.5, dir: 1},
  {k:'fgSat', step:0.05, every:1.000, lo:0, hi:2.5, dir:-1}
];
```

Given a step count, each walker's value is exactly determined. Four step
counts are a complete description of the wander state. Nothing random
enters it.

### The clock now mostly is — this has been fixed

It used to read `w.t = 0`, which threw away the remainder instead of
subtracting the threshold, so a walker's real period was not
`every / speed` but *"the first frame on which accumulated dt crossed the
threshold"* — rounded up to a whole frame. At 60fps the 0.125s
ground-hue walker actually fired every 0.133s, 6.7% slow.

That rounding is a fixed number of milliseconds, so it costs a bigger
*share* of a short interval than a long one. Thirding the hue intervals
for granularity walked straight into it: ground hue went from 8 frames
(6.7% slow) to 3 frames (20% slow), losing 12.5% of its drift rate for
nothing. So the one-line fix got made:

```js
const thr = w.every / Math.max(0.05, P.wanderSpeed);
w.t += dt;
if(w.t < thr) continue;
w.t -= thr;                  // carry the remainder, do not discard it
if(w.t > thr) w.t = thr;     // but never bank more than one step
```

The clamp is not optional. `dt` is capped at `1/30`, so on a page running
slower than one frame per threshold the remainder would grow without
bound and the walker would fire every frame forever, then sprint once the
page recovered. Measured at `wanderSpeed 6`, where the ground-hue
threshold (13.9ms) is shorter than a frame: `w.t` parks at exactly `thr`
and stays there, 60.1fps, worst frame 19.8ms.

Measured at `wanderSpeed 2` / 60.1fps, all four walkers now run within
**0.8%** of nominal — ground hue exactly on 0.0417s against a nominal
0.0417s, where before it was 6.7% slow.

**Two sources of divergence remain**, and they are deliberate:

- `dt` is clamped to `1/30`, so a page running below 30fps still advances
  wander slower than wall clock.
- A backgrounded tab has rAF throttled, so wander nearly freezes — which
  is the *wanted* behaviour for a clock that should count watched time
  (see §2).

So the remaining gap between wander-time and wall-time is now only where
the page was not being drawn, which is exactly the semantics a timecode
would want anyway.

### The actual periods
At the default `wanderSpeed 2`:

| walker | steps per full cycle | wall time |
|---|---|---|
| ground hue | 432 | 18.0s |
| ground sat | 84 | 45.5s |
| plant hue | 432 | 28.8s |
| plant sat | 100 | 50.0s |

LCM ≈ **3.8 days** before the exact four-value state repeats (7.6 days at
`wanderSpeed 1`).

So the honest claim is not "you will see something new forever," it is
"you will see something new for about four days." Still far longer than
anyone will sit through, and a real number worth putting on the page.

> The comment in `index.html` claiming a beat period of "about four
> months" from primes `43×59×71×89` refers to intervals that are not in
> the code any more. It is stale — the real intervals are
> 0.0833 / 0.1333 / 1.083 / 1.000.

---

## 2. The timecode

Don't display elapsed wall time. Display **the clock the walkers run on**.

### The refactor that makes it worth doing
Stop stepping the walkers incrementally. Make each a **pure function of a
single accumulated `wanderClock`** — a triangle wave per walker. Three
things fall out at once:

1. **Exact determinism.** No accumulator, no drift, no frame-rate coupling.
2. **Seekability.** `wanderlust 041200` becomes something you can *type
   in* and land exactly where someone else was.
3. **A shareable coordinate.** A code under a screenshot is a location,
   not decoration.

That third one is the real payoff, and it only exists if the mapping from
code to state is exact — which is why §1 has to be fixed first.

### It should count watched time, not elapsed time
Because `dt` freezes when the tab is hidden, the clock naturally counts
*time someone actually looked at it*. Persist it in `localStorage` and it
becomes cumulative across visits: the page remembers you.

That also solves the obvious objection to any long-horizon idea — nobody
leaves a band site open for three hours. They don't have to. They leave it
open for three hours **across two months**, and a returning visitor sees a
higher number than they left on.

### Costs and frictions
- Sliders currently *take over* from wander (grabbing a hue slider stops
  it). A pure-function clock needs an offset to keep that behaviour.
- `P.markColor` persists after wander stops, so the page does not return
  to its starting colour. Fine today; a wrinkle if a code is supposed to
  reproduce a look exactly.

---

## 3. Escalation

### Continuous ramps are invisible
A palette that gets 3% more extreme per hour reads as no change at all, on
any human timescale. **Escalation has to be discrete to be perceptible** —
thresholds that flip something visible, with the drift between them being
anticipation rather than content.

### The mechanism already exists
Walker bounds are read from `CONTROLS` min/max via `syncWanderBounds()`.
**Widen the bounds at thresholds and the whole colour system escalates for
free** — same code, bigger box. The same applies to:

| knob | today | escalated |
|---|---|---|
| `BREATHE_HI` / `BREATHE_LO` | 1.5 / `sizeFrom÷size` | wider band, wilder size swings |
| `SWING_MAX` | 1.5 rad (~73°) | past ~2.5 rad plants read as falling over, not bending |
| `density`, `size` | 1.8 / 1.7 | denser, larger — watch overdraw |
| `BREATHE_RATE` | 200/s | more of the field in motion at once |

Needs an **envelope that plateaus or cycles**, not one that diverges.
Unbounded escalation ends at "everything is maximum," which is
indistinguishable from no variation at all — it destroys the thing that
made it good.

---

## 4. The game question

### What the engine already gives you
- Per-plant damped springs with a wind field
- A cursor that imparts force proportional to speed and proximity
- A spatial grid (`crowded()`) — collision queries are already cheap
- Sprite compositing with baked shadows, one `drawImage` per entity
- A stable per-plant `rank`, which is already used to thin the field
- Draw-time scaling per entity (`p.g`), already proven ~free

Mobs are genuinely not a stretch from here.

### The wool constraint is the best idea in the room
The first working agreement on this project is that **nothing is
illustrated** — every pixel is extracted from the panels. So an antagonist
cannot be drawn. It would have to be **found in the embroidery.**

There is already a butterfly in the panels; it shows up in renders. A game
whose enemies are the things that were literally stitched into a 1970s
crewelwork panel is a far stranger and better idea than a game with
sprites someone designed. **The constraint does the creative work.**
Anything added this way goes through `pipeline/extract.py` and
`config.KEEP` like every other asset, which also means it inherits the
colour grade, the shadow bake and the wander recolouring for free.

### The tonal risk is the real objection
The site's job is to make someone feel something and then click `listen`.
A game is a different job, and it can eat the first one — a visitor who is
fighting crocuses is not listening to the record.

**The moment it has a fail state it is a different website.** The safer
framing is not a mode switch with an HP bar, but *the field becoming
stranger and more responsive to you over time*: it stops being something
you brush past and starts being something that notices. That serves the
mood instead of competing with it.

### Technical frictions to design around
- **`regrow` resows.** Every page change calls `seed()` and replaces the
  `plants` array wholesale. Any persistent entity has to live outside it
  or deliberately survive it. `breathing` and `blooms` already have to be
  rebuilt on every seed for exactly this reason.
- **The density governor can thin plants out from under you** if
  `autothin` is ever turned on. An entity that matters must not be
  subject to `rank`.
- **The frame is destination-pixel bound.** ~6× overdraw at 60fps on a
  real GPU with headroom, but the levers are on-screen *size* (quadratic),
  plant *count*, and DPR — not cleverness in the loop.
- **Mobile is untested on real hardware**, and `autothin` is off. Any
  added per-frame cost lands hardest exactly where nothing has been
  measured.

---

## 5. If this were ever pursued, in order

1. ~~Fix the accumulator (`w.t -= threshold`).~~ **Done** — see §1. It
   was not done for this; it was forced by thirding the hue intervals,
   which made the rounding cost 12.5% of ground hue's rate. Everything
   below still depends on it, and it is no longer in the way.
2. Refactor the walkers to pure functions of a `wanderClock`. Verify a
   given clock value reproduces a given look exactly, twice.
3. Show the number. Persist it in `localStorage`. Ship nothing else —
   see whether a counter alone is interesting.
4. Make it seekable (typing a code jumps there). This is the point at
   which it becomes shareable.
5. Only then, one discrete threshold that widens the wander bounds. One.
   See whether anyone notices before building a second.

Steps 1–3 are small and useful on their own. Everything past 4 is a new
product, and should be decided as one.
