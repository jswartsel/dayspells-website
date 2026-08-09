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
  {k:'bgHue', step:5,    every:0.25, lo:0, hi:360, dir: 1},
  {k:'fgHue', step:5,    every:0.40, lo:0, hi:360, dir:-1},
  {k:'bgSat', step:0.06, every:0.65, lo:0, hi:2.5,  dir: 1},
  {k:'fgSat', step:0.05, every:0.75, lo:0, hi:2.5,  dir:-1}
];
```

Given a step count, each walker's value is exactly determined. Four step
counts are a complete description of the wander state. Nothing random
enters it.

### The clock is not
```js
w.t += dt;
if(w.t < w.every / P.wanderSpeed) continue;
w.t = 0;              // <- discards the overshoot
```

`w.t = 0` throws away the remainder instead of subtracting the threshold.
So a walker's real period is not `every / speed`, it is *"the first frame
on which accumulated dt crossed the threshold"* — which depends on frame
rate and on every individual hitch.

At 60fps the 0.125s ground-hue walker actually fires every **0.133s**,
6.7% slow. At 120fps it is exact. One GC pause shifts the phase
permanently. Two further sources of divergence:

- `dt` is clamped to `1/30`, so a page running at 20fps advances wander
  **slower than wall clock**.
- A backgrounded tab has rAF throttled, so wander nearly freezes.

**Consequence:** replay for three hours and you see the same *sequence*,
at different *times*. Order is fixed; the clock is not.

**The fix is one line** — `w.t -= threshold` instead of `w.t = 0`. That
makes it frame-rate independent, and it is the prerequisite for any
timecode being meaningful.

### The actual periods
At the default `wanderSpeed 2`:

| walker | steps per full cycle | wall time |
|---|---|---|
| ground hue | 144 | 18.0s |
| ground sat | 84 | 27.3s |
| plant hue | 144 | 28.8s |
| plant sat | 100 | 37.5s |

LCM ≈ **3.8 days** before the exact four-value state repeats (7.6 days at
`wanderSpeed 1`).

So the honest claim is not "you will see something new forever," it is
"you will see something new for about four days." Still far longer than
anyone will sit through, and a real number worth putting on the page.

> The comment in `index.html` claiming a beat period of "about four
> months" from primes `43×59×71×89` refers to intervals that are not in
> the code any more. It is stale — the real intervals are
> 0.25 / 0.40 / 0.65 / 0.75.

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

1. Fix the accumulator (`w.t -= threshold`). One line, and everything
   else depends on it.
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
