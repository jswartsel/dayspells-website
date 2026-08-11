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
- **Zones are measured off the type, not placed by constants.** Anything
  carrying `data-zone` (grass only) or `data-bare` (nothing at all)
  contributes an ellipse around its own box, so four nav links and three
  stacked links cost nothing per page and hidden pages drop out on their
  own (a `display:none` box measures 0×0). Nearly everything is a grass
  zone now, with `ZONE_GRASS` at 0.15 doing the work instead: a clearing
  keeps 15% of the grass that lands in it, which reads much as bare linen
  did but still lets a few blades through. Only the back caret is
  `data-bare`. Three things had to be right for this to hold up:
  - **The attribute goes on an inline span.** A block stretches to its
    widest sibling, so the `h1` measured the *nav row's* width and the
    wordmark got a clearing half the screen wide. An inline box is the
    union of its line boxes.
  - **The pad is additive in em, not a multiplier on the box.** A
    multiplier gives a two-line paragraph twice the margin of a one-line
    one and a four-letter word a quarter of the wordmark's.
    `ZONE_PAD_X` 0.18 / `ZONE_PAD_Y` 0.65 reproduce the old hand-tuned
    wordmark clearing (383×101 against 383×100) while transferring to
    every other piece of type.
  - **`ZONE_TOP` shortens the pad, not the semi-axis.** Scaling the axis
    means a taller block loses its top margin to its own extra height:
    "stay tuned for upcoming dates" had 7px of air above it where the
    wordmark had 31. Against the pad it is a flat 0.39em for everything,
    and `ZONE_TOP` moved 0.75 → 0.60 to keep the wordmark where it was.
- **Gaps between stacked type carry an absolute term, not just an em
  one.** Two clearings stop touching once their centres are more than
  one line-height plus 1.04em apart; past that is field, and that band
  is where flowers grow between the words. But **a sprite is a fixed
  number of pixels tall whatever the viewport** — a bloom draws 45-65px
  on a phone exactly as on a laptop — so a gap in em alone gave 48px of
  roof on a laptop and 13px on a phone, which nothing can grow in. Every
  gap is `proportional term + 48px`; measured, the band is a flat 48px
  on every stacked pair from 390px wide to 1440.
- **When a short screen can't hold both, the type gives way, not the
  roof.** Three listen links each with 48px of roof do not fit a 390px-
  tall landscape phone; capping the *gap* clipped `spotify` off the
  bottom on one attempt and merged all three clearings into one column
  on the next, which is the thing the roof exists to prevent. Capping
  the *type* instead (`--sfs`, with the gap written as
  `1.04 * --sfs + 48px`) keeps the band at 48px everywhere. The one
  place still short is the wordmark-to-nav roof on a landscape phone
  (17px), because the alternative is shrinking the wordmark.
- **Careless block edits to the stylesheet fail silently, twice now.**
  Inserting `--menu` into `:root` closed the block early and left
  `--frond-dark` and `--cream` stranded inside the following `@media`,
  where they are invalid and dropped. Nothing errored; `var(--cream)`
  simply became invalid, so the panel inherited `body`'s dark plum
  instead of cream. If a colour or a rule "just changed", read the
  computed value and check the variable actually resolves before
  touching anything else.
- **A stray `*/` silently deleted the entire `.nav` rule.** Appending a
  second comment tail to an already-closed block comment left the CSS
  parser dropping everything after it: no margin, no flex, four links
  stacked in a column on a 1440px desktop. It surfaced as a *layout*
  oddity, not as an error. When a rule seems not to apply, read the
  computed style (`getComputedStyle`) before touching the values -- that
  is what showed `margin-top: 0px` against a declaration that was right
  there in the file.
- **The nav needs a vw cap to hold one line.** At a plain ratio of the
  wordmark the four links outgrow the window below ~1150px and wrap 3+1,
  which reads like an accident. `min(--type * .54, 4.2vw)` holds one row
  through every landscape size measured; portrait goes to one per row.
- **Changing page resows.** The clearings belong to the type on screen,
  so it is the transition rather than a cost — the field grows in from
  `sizeFrom` around whatever has just arrived. Zone code reads DOM rects,
  so the view must be swapped *before* `seed()`; `getBoundingClientRect`
  forces the layout, so calling it straight after the swap is enough.
- **Seed again on `document.fonts.ready`.** The clearings are measured
  off the type, so they are only right once the type is in the right
  face — the fallback is a different width, and without this the first
  field is sown around a wordmark nobody ends up looking at. This did not
  matter while the zone was computed from `W`/`H`.
- **`[hidden]{display:none !important}` is load-bearing.** Author styles
  beat the UA sheet, so the `display:block` on the link rule un-hid every
  view and the back caret. Views are switched by `[hidden]` and nothing
  else.
- **Blooms breathe during wander, and the coin is not 50/50.** A bloom
  eases ×1.2 up or ×0.5 down and stops there, in a band from
  `sizeFrom/size` to 1.2. `BREATHE_UP` and `BREATHE_HI` move together --
  a step that overshoots the ceiling makes the ceiling the only size a
  grown bloom can hold, and the top of the range quantises to one value.
  The two ends are lopsided on purpose: gentle growth, halving shrink,
  so the field carries small flowers throughout (measured, 11-20% of
  blooms below half size at any moment, mean holding 0.72-0.84 over
  48s). Halving is a bigger move than multiplying by
  1.5 — `ln 2` against `ln 1.5` — so a fair coin drifts the whole meadow
  downward and it settles at a fraction of its size after a couple of
  minutes, reading as the field wilting rather than breathing.
  `BREATHE_FAIR` is derived from the two step sizes so it stays right if
  they are re-tuned; `BREATHE_REVERT` pulls back toward the sown size on
  top of it. Measured: mean size holds at 0.72-0.84 across 48s while
  individual blooms span 0.13 to 1.2. It is a **draw-time scale**, like
  grow-in — one multiply on a transform already being computed — and it
  waits for the grow-in to finish, since two scale ramps at once fight
  each other. Mean sprite *area* comes out slightly below rest, so there
  is no overdraw cost: 61fps idle, 61fps breathing, headed.
- **Scaling the meadow with the type was built, measured, and reverted.**
  A sprite is a fixed number of pixels wherever it is drawn; the type is
  set in vw. So on a phone the field was full desktop size against type
  less than half as tall, and the clearings came out *smaller than a
  single bloom* — a plant was correctly excluded from a zone and still
  covered the words, because only its centre is tested. The fix that
  suggests itself is to put the plants on the same ramp `--type` uses and
  divide the count by that scale squared to hold coverage. Measured at
  390×844: scale 0.418, blooms 23×25px, 4806 plants against 843, overdraw
  7.2x against the laptop's 6.4x — proportionally correct at every width.
  It came out **the wrong look**: many small flowers read as noise where
  few large ones read as a meadow. It also moved the cost onto the CPU
  (5x the physics and transforms) on the weakest devices, with `autothin`
  off. The zone floor below is what carries the fix instead. Do not
  reach for the rescale again without knowing it was tried — it works,
  and it was rejected on taste and phone CPU, not correctness.
- **Zone semi-axes are floored at `half-box + half-bloom`.** The smallest
  ellipse that can actually keep a bloom off the type, given that only
  the centre is tested. Measured off the assets so it tracks `P.size`.
- **An equal-specificity override must come AFTER what it overrides.**
  The portrait `.stack` rule sat above the plain `.stack` rule, so it
  lost on source order and did nothing: the listen links stayed pinned to
  the landscape vw cap at 16px while the nav was 26px. It survived a
  check because that check read the first `.nav a, .stack a` match, and
  the *hidden* nav link comes first in the document — so both pages
  reported 26px. Two lessons: probe the element that is actually
  rendered (first with a non-zero rect), and prefer one variable over
  three copies. Sizes for the nav, the listen links and the sub-page
  messages drifted apart twice before they were hoisted into `--menu`.
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
- **`willReadFrequently: true` pins a canvas to CPU memory.** That is
  correct for a scratch surface you `getImageData` out of, and ruinous
  for anything drawn from afterwards. Setting it on the canvas behind
  `createPattern` — a pattern that fills the whole canvas every frame —
  took the page from **60fps to 2.3fps**, a 26x regression, with a worst
  frame of 454ms. Do the pixel work on a scratch canvas, copy into a
  clean one, and pattern from that. The same care applies to any sprite
  that ends up as a per-frame draw source.
- **Benchmark canvas performance with `headless=False`.** Headless
  Chromium has no GPU and rasterises in software, so it cannot see a
  change that knocks the page off the GPU path — it has no GPU path to
  fall off. It did worse than fail to catch the regression above: it
  reported the broken build as **21% faster** than the good one, and an
  A/B at identical settings agreed. Every conclusion in this file that
  rests on a software measurement is a statement about software
  rasterising, not about the machine anyone will use. `playwright
  chromium.launch(headless=False)` uses the real GPU and took ten
  seconds to settle a question two headless runs had got backwards.
- **The frame is destination-pixel bound, not source-pixel bound.**
  Measured: physics is 3.3ms of a 130ms frame (2.5%); the ground fill and
  the vignette are a few ms each; halving the plant count doubles the
  frame rate. It is sprite fill, and essentially nothing else. Cutting
  the baked sprite resolution by 39% changed the frame rate not at all.
  So the levers are, in order: **on-screen size** (area, so quadratic),
  **plant count**, and **DPR** — not asset resolution, not cleverness in
  the loop. Lowering the payload's image resolution only helps if the
  flowers get smaller with it; raise `size` to compensate and you are
  back where you started, just blurrier.
- **Overdraw is the number to watch, but the GPU has plenty of headroom.**
  At size 1.7 / density 2.5 / DPR 1.5 the field asks for 21.2 Mpx of
  alpha-blended sprite fill per frame against a 2.92 Mpx canvas — 7.3x
  overdraw; size 1.3 gives 5.3x, size 1.0 gives 4.0x. Density is a weaker
  lever than it looks, because the crowding grid absorbs some of it:
  2.5 -> 1.5 drops 38% of the plants but only 16% of the pixels. But note
  that on a real GPU the page holds a flat 60fps at density 1.3 / size
  1.7 — about 6x overdraw — with wander running and the governor idle. It
  was never the overdraw that made the page choke; it was the CPU-pinned
  pattern above. Reach for the settings only after checking on a GPU.
- **Never re-bake sprites per frame.** Wander was first written to
  re-colour continuously, which cost 15.4ms of a 16.7ms frame — an order
  of magnitude more than the synchronous timing suggested (0.47ms/sprite),
  because canvas allocation and the shadow blur bill after the call
  returns. The tell was that frame rate did *not* recover when wander was
  switched off. Fixes: step in discrete jumps a few times a second; cache
  the contact shadow, which is derived from alpha and so is
  colour-independent; reuse canvases instead of allocating; and scale
  before colouring. `ensureBake` allocates, `recolour` does not.
- **The wander accumulator subtracts, and the clamp beside it is
  load-bearing.** It used to read `w.t = 0`, which discarded the
  overshoot, so a walker's period was really "the first frame past the
  threshold" -- rounded up to a whole frame. That rounding is a fixed
  number of milliseconds, so it costs a bigger *share* of a short
  interval than a long one, and thirding the hue intervals for
  granularity walked into it: ground hue went 8 frames (6.7% slow) to 3
  frames (20% slow), losing 12.5% of its rate. Now `w.t -= thr`, and all
  four walkers measure within 0.8% of nominal. **Do not drop the
  `if(w.t > thr) w.t = thr`** -- `dt` is capped at 1/30, so on a page
  slower than one frame per threshold the remainder grows without bound
  and the walker fires every frame forever, then sprints when the page
  recovers. Verified at `wanderSpeed 6`, where the ground-hue threshold
  is 13.9ms against a 16.7ms frame: `w.t` parks at exactly `thr`, 60.1fps,
  worst frame 19.8ms.
- **Hue granularity was free, and the reason is `plantQueue`.** It RESETS
  to `ASSETS.length` on every plant step rather than accumulating, and
  `rebakeSome` drains it at a flat 2 sprites a frame off a rolling
  `bakeCursor`. So it was already saturated at the old rate -- stepping
  three times as often resets an already-full queue and changes the work
  done per frame not at all. Only the ground pays, 0.94ms three times as
  often. If anyone ever makes the drain rate track the step rate, that
  stops being true and this gets expensive.
- **Granularity and rate are separate knobs, and `step` alone is the
  wrong one.** Thirding `step` by itself is three times *slower*, not
  three times *finer*. Both terms move together -- `step:5/3` with
  `every:X/3` -- which is why they are written as divisions in the table
  rather than as decimals. The corollary is the other direction:
  **ground hue was halved by doubling `every` alone** (0.25 -> 0.50,
  keeping the 5/3 step), so it drifts through the same hues at half the
  pace rather than in coarser jumps. Measured A/B, 40.1 deg/s -> 20.0,
  a ratio of 0.498, with plant hue untouched at 0.999. Its cycle went
  18s -> 36s, and a later 15% took it to 42.4s (measured 20.09 deg/s
  -> 17.02, a ratio of 0.847). The four-walker repeat used to be a tidy
  ~3.8 days and is now far longer and not worth quoting -- 720/17 shares
  almost nothing with the other three cycles, so the figure swings on
  the last digit of the intervals.
- **Read a slider's value BEFORE calling `setWander(false)`.** The
  takeover in the `input` handler stops wander, `setWander(false)` calls
  `syncWanderInputs()`, and that writes `P` back into the very elements
  being dragged. So reading `el.value` afterwards hands back the
  wander's value and discards the input that just arrived. This hid for
  a long time because a drag fires `input` many times and only the first
  is eaten — but a single **click on the slider track** was silently
  ignored outright. It predates the gain swell and applied to all four
  walker sliders; adding `bgGain` to the takeover is what surfaced it.
  The handler now captures `v` first and assigns after.
- **The gain roll hangs off the RESOW, not a clock, and it snaps.** It
  was once a five-phase machine on its own timer (wait, fall, hold,
  rise, settle) and moving it onto the resow deleted two phases, three
  timers and an easing function. The field is replaced in that same
  frame, so the light changing with it reads as one event; easing it
  smears one cut over five seconds and puts the light out of step with
  the field. Four things to keep:
  - **The plants follow the ground's roll, they do not roll
    separately.** Bright ground pairs with near-black plants
    (silhouettes); dark or ordinary ground pairs with bright plants.
    Independent rolls give washed-out flowers on a washed-out ground a
    third of the time, which is the one combination with nothing in it.
  - **Both gains go home when wander stops; hue and sat do not.** Those
    are left where they landed so `copy(tune())` captures a look. A
    transient that stranded the ground at black is just a bug.
  - **`resetSwell()` has to run wherever something else rewrites `P`** —
    `setWander(true)`, the reset button, `tune()`. Otherwise the next
    roll returns the gains to bases that have since been replaced.
  - **Only the deliberate resow paths call `rollSwell()`.** `resize()`
    and `fonts.ready` call `seed()` directly and are deliberately not in
    that list -- a window drag re-rolling the light would be absurd.
- **Deleting a block can take a shared helper with it, and the page will
  still load.** Rewriting the swell removed `const smooth` along with
  the phase machine that happened to host it. Nothing referenced it
  until a roll actually started a ramp, so page load was clean, the
  console was clean, and every check passed -- then the first resow
  threw `smooth is not defined` inside `stepSwell` and killed the rAF
  loop for good. A dead render loop looks exactly like a still frame.
  After removing a block, grep for what it defined, and exercise the
  code path rather than trusting a quiet load.
- **`#viz` is a route with no view element, and that is the mechanism,
  not an omission.** `showView` hides everything whose `data-view` does
  not match the name, so a name nothing claims hides every page at once.
  Do not "fix" it by adding a `data-view="viz"` element -- that would put
  a box back on screen and give the zone pass something to measure.
- **A capture is `settingsNow()`, not `{...P}`.** The visualizer borrows
  `P.grow`, `P.size` and `P.ghostOn`, so a raw spread taken in `#viz`
  records the visualizer's geometry. Captures are meant to be pasted
  back into `DEFAULTS`, so that would be a trap. `settingsNow()` loops
  over `vizWas` and restores anything on loan -- which is why the borrow
  bookkeeping is ONE table rather than three separate lets: add a fourth
  borrow and capture follows it for free instead of silently going
  stale. It must also stay a COPY; `P` is mutated in place by every
  walker, so pushing `P` itself gives a list of N identical objects all
  tracking the live field.
- **A fixed block with `left:50%` and no `right` shrink-wraps to HALF
  the screen.** The used width is shrink-to-fit against the space
  remaining to its right, so `max-width` never gets a say -- the toast
  wrapped to three lines on a 382px viewport before this was fixed with
  `left:0; right:0`. The `.hint` gets away with the same pattern only
  because it is three short words.
- **Never claim the clipboard worked before the promise settles.**
  `navigator.clipboard.writeText` rejects on an insecure origin, a
  denied permission, or a gesture the browser considers stale -- and a
  synthetic `KeyboardEvent` carries no user activation at all, so it
  fails under test while a real keypress succeeds. The toast waits on
  the promise and the failure path leaves the JSON in the console.
- **Adjustable numbers go in `TUNING`, not beside their code.** The
  block sits right after `DEFAULTS`. Values live there; the reasoning
  stays with the code it constrains. Two sets are deliberately out:
  `WANDER` (it carries per-walker `t`/`dir` state, so it belongs with
  its stepper) and the engine constants SHRINK / WEIGHT / CLUSTER /
  FORCE / SWING_MAX / BRUSH.
- **A 0-size viewport at load used to freeze the meadow for good.** A
  0x0 canvas makes a 0x0 vignette, `drawImage` throws
  InvalidStateError, and that throw lands inside `frame()` BEFORE its
  `requestAnimationFrame` -- so the loop stops permanently and never
  recovers even once a real size arrives. Observed exactly that way in
  an embedding pane that had not been sized yet. `resize()` now floors
  W/H and the canvas at 1, and the vignette blit checks its dimensions.
  The general lesson is the one that keeps recurring here: anything that
  can throw inside `frame()` does not cost a frame, it costs the page.
- **The visualizer BORROWS globals, it does not own them.** `P.grow`,
  `P.size` and `P.ghostOn` are all saved on the way into `#viz` and put
  back on the way out, each behind a `viz*Was === null` guard so
  re-entering cannot save a borrowed value over the real one. The
  consequence to remember: a slider dragged while in the visualizer is
  discarded when you leave, because the restore wins. That is the
  contract, not a bug.
- **`P.size` is geometry, and borrowing it has to re-bake.** Unlike the
  gains, which are colour, `ensureBake` derives `a.dw`/`a.dh`/`a.stem`
  from `SHRINK * P.size`, so changing it without `rebakePlants()` leaves
  every sprite at the old dimensions. It also feeds the zone floor and
  the crowding grid, which is why its panel control carries `rg:1` as
  well as `cost:'plants'` -- the sprites re-bake immediately and the
  field resows a beat later.
- **`P.ghostOn` is flipped through `setGhost()` and nowhere else.** Four
  things want to change it -- the checkbox, a real pointer arriving, the
  idle timer, and the visualizer borrowing it -- and they will disagree
  if any of them assigns directly. Assigning also skips the part that
  matters: `setGhost(true)` re-centres the doodle and marks the pointer
  live, so a bare `P.ghostOn = 1` sets a flag and wakes nothing.
- **Unchecking `enable` must not be undone by the idle timer.** A
  pointer taking the brush is temporary; unchecking the box is a
  decision. Without `ghostMuted` telling those apart, unchecking it in
  the visualizer is reversed 3.2 seconds later and the checkbox looks
  broken.
- **`ghostSpeed` scales `dt`, not `doodle.spd`.** It is a pure time
  dilation, so the pen traces the same figure sooner. Scaling the speed
  alone widens every curve instead -- turn radius is speed over turn
  rate -- and the doodles straighten out as they get faster.
- **A doodling hand is a PEN, not a sequence of hops, and its curvature
  must be SET rather than integrated.** Two wrong versions: point-to-
  point with rests read as isolated twitches (what makes a doodle human
  is that it never stops and never goes straight); then a damped random
  walk on angular velocity, `w += noise*dt` with 0.90 per-frame decay,
  which settles at a standard deviation of ~0.07 rad/s -- four degrees
  of turn per second, measured as a chord-over-length of 0.99, i.e. a
  straight line. Three summed sines instead, so `DOODLE_CURL` is a plain
  rad/s and is frame-rate independent. Two more traps in the same
  function: the target pull must SATURATE, or a 180-degree course error
  asks for pi*PULL rad/s and the pen spins on the spot; and the edges
  must REFLECT, not clamp, or a steeply-arriving pen keeps its heading
  and slides along the wall -- a 400px straight line across the top of
  the screen, which is the one shape that gives it away as a machine.
- **The visualizer's hand writes `ptr.x/y` and nothing else.** The frame
  loop differences those into a smoothed velocity, so rustle, brush
  radius and trailing overshoot all behave exactly as under a real hand.
  Do not reach into the spring code to fake motion. It also has to WIN
  over `ghost` in the frame loop rather than relying on `resetViz`
  clearing `ghost.on` -- the 3.2s no-pointer timeout can set that flag
  afterwards.
- **Glade separation is tested on the largest semi-axis, not the
  width.** Two ellipses clear each other when their centres are further
  apart than the sum of their bounding radii; comparing `ax` alone lets
  a tall glade run straight through its neighbour. Biggest is placed
  first (a big glade dropped into a field of small ones is the placement
  that fails) and shrinks on failure, so a run of large draws degrades
  in size rather than in separation. Measured 0 overlapping pairs in
  2721 across three viewports. An earlier version only forbade
  coincidence and all four still stacked into one hole in the middle.
- **`toolBox` has to check for an empty rect.** A `display:none` box
  measures 0x0 at the origin, and the margin around it is absolute -- so
  hiding the corner links (which the visualizer does) did not remove the
  bare patch, it moved it to a 79x70 square pinned to the top-left
  corner. The `[data-zone]` loop was already safe because it tests for
  an empty rect; this branch was not.
- **Anything that measures the page must be checked against the pane's
  REAL surface.** A run of screenshots showed the meadow painting only a
  ~380px corner of a 1440x900 viewport. The page was fine --
  `getImageData` over the canvas showed 2156x1348 of 2160x1350 painted
  -- and the browser pane was emulating the viewport in layout while
  compositing at its true ~382px width. Measure the canvas before
  believing a screenshot that looks structurally broken.
- **Colour is one 3×3 matrix**, composed from gain+tint, hue and
  saturation and applied in a single pass over the pixels. It is exactly
  the identity at the defaults, so the untouched case costs nothing. Use
  the sRGB luminance coefficients (0.213/0.715/0.072) the SVG filter spec
  uses, or hue rotation stops holding its brightness.
- **Gain clips a PALE material toward white, which destroys chroma.**
  Neon is a big gap between the brightest and darkest channel. The linen
  is a near-neutral whose three channels sit within ~50 of each other,
  so gain walks all three into the 255 ceiling at nearly the same moment
  and the gap collapses; a flower has a channel down near zero, so its
  gap survives. That is why the ground looked washed out at settings
  that made the flowers neon, and why turning ground gain UP made it
  worse rather than better. Measured on the old tile at max saturation:
  0.589 output saturation at gain 1.0 and 1.22, 0.463 at 1.6, 0.328 at
  2.0, and at gain 2.0 / sat 1.0 exactly `[255,255,255]` — white.
  Saturation compounds it: `out = lum + s*(in - lum)` scales a pixel's
  distance from its own grey, and a near-neutral has almost none to
  scale. The old tile started at HSV saturation 0.244 against a purple
  iris's 0.838.
  **This is fixed at the source now, not at runtime** — see
  `GRADE_GROUND` in `config.py`. The tile is darker and far more
  saturated, so the runtime sliders have both headroom and chroma to
  work with. If someone still reports hue or sat "not doing anything",
  check the gain: past the clipping onset the same collapse applies to
  any tile.

## Known issues, not yet fixed

1. **Faint linen fringe** survives on a few petal tips. Raising
   `FG_THRESHOLD` trades it against eating thin stems.
2. **`daffodil-a` carries a small white scrap** at its base, left behind
   when the narcissus it was fused to was split off.
3. **The clearing behind the wordmark can read as a bald patch** on some
   seeds. It's density thinning (an ellipse in `seed()`), not a wash.
4. **Faint vertical slub in the ground tile** repeats at 512px. It's real
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

- **The wordmark's colour is derived from the canvas, not cycled.** During
  wander a 24×12 downscale of the box behind the wordmark is read back
  6.7 times a second and the text steers to the complementary hue with
  lightness flipped to the opposite end. Two things to preserve if this
  is ever touched: plain RGB inversion does not work (invert mid grey,
  get mid grey — the lightness flip is what buys legibility), and the
  readback must stay tiny. `getImageData` forces a GPU-to-CPU sync;
  288 pixels costs 0.73ms, the full canvas would not be affordable.
