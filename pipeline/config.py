"""
Everything tunable about the extraction.

The 2026 re-shoot (IMG_1639/1640) is already square-on, evenly lit and
cropped to the linen, so there is nothing left to hand-measure: no frame
corners, no per-flower seed points. The panel names below and the KEEP
list at the bottom are the only things that need touching when you
re-shoot.
"""

# Source panels, and the prefix their assets get. The prefix is explicit
# rather than sliced off the filename -- the old pipeline used
# name[-2:], which is why grass was called 'blade-37-*'.
PANELS = [
    ('IMG_1640', 'daf'),   # daffodils, narcissus, crocus
    ('IMG_1639', 'iri'),   # irises + a daffodil pair
]

# Longest side the flattened panel is resampled to. Everything below is
# tuned in these pixels, so changing it means retuning FLOWER_CLOSE.
PANEL_H = 4500

# --- segmentation ----------------------------------------------------------
# Foreground is normalised Lab distance from the linen. The linen colour is
# found as the dominant chroma mode of the whole panel, so it does NOT
# depend on clean margins -- the previous version sampled the outer 3-4%
# and would have been poisoned by stitching that runs to the edge.
FG_THRESHOLD = 5.0

# Colour families, in OpenCV HSV (H is 0-179). Everything downstream is
# built from these: a bloom is contiguous non-green, non-dark foreground.
FAMILIES = {
    'dark':   dict(v_max=95),
    'green':  dict(v_min=95,  h=(33, 92),  s_min=60),
    'yellow': dict(v_min=150, h=(12, 32),  s_min=90),
    'white':  dict(v_min=165, s_max=95),
    'purple': dict(h=(125, 168), s_min=60),
    'pink':   dict(v_min=150, h_wrap=(168, 12), s=(40, 170)),
    # Deep maroon petals -- crocus outers, iris falls. These are dark
    # enough to fall in 'dark', which is meant for the brown-black
    # foliage, and losing them cut every crocus into loose petals. The two
    # populations separate cleanly by hue: foliage is H 0-30 at V 19-31,
    # maroon petals are H 125-180 at V 54-75, both heavily saturated.
    # 'maroon' is subtracted from 'dark', so these count as bloom.
    'maroon': dict(h=(125, 180), s_min=150, v=(38, 95)),
}

# --- blooms ----------------------------------------------------------------
# Bridge whatever crosses a bloom. This is the width, in px, of the widest
# stem or leaf that may pass over a flower; the closed silhouette is then
# intersected back with the foreground so crossing WOOL is kept and
# crossing LINEN is not. Occluders keep their own colour -- that is the
# point, and it is why there is no longer any erode-and-reconstruct.
FLOWER_CLOSE = 61
BLOOM_MIN_AREA = 15000

# Two flower heads that touch come out as one asset. They are separated by
# watershed on the distance transform, sweeping the threshold rather than
# fixing it -- no single value fits both a pair of fat daffodil heads and a
# slim iris.
#
# The accept rule is a share, not a pixel count, which is what makes it
# work across both: a split counts only if the smallest part is at least
# SPLIT_MIN_PART of the whole. Two flowers divide roughly in half and pass;
# a flower shedding a single petal does not.
SPLIT_MIN_AREA = 14000
SPLIT_MIN_PART = 0.18
SPLIT_MAX_PARTS = 3

# --- grass -----------------------------------------------------------------
# Green stems and leaves are ALSO emitted on their own, so the page can
# scatter grass and flowers at independent densities. They remain part of
# the bloom cutouts they belong to.
GRASS_MIN_AREA = 9000
GRASS_MIN_HEIGHT = 200
GRASS_PER_PANEL = 12
# Stems rising from a common root split like touching blooms do. Stems are
# long and thin, so their distance transform peaks are shallow -- this
# wants a lower fraction than the blooms.
GRASS_SPLIT_MIN_PART = 0.22   # stems divide less evenly than blooms

# --- curation --------------------------------------------------------------
# Filled in from work/contact_sheet.png after a run. name -> (role, max, stem)
#   role -> how the page scatters it   (flower | clump | small | grass)
#   max  -> longest side in px in the web payload
#   stem -> virtual stem length below the sprite; the plant pivots there
# Rejected, and why:
#   iris-pink-a          -- top half of a bloom, cut flat across the bottom
#   iris-pink-c/d        -- single petals; don't read as flowers
#   iris-purple-b        -- a purple iris with someone else's petal attached
#   iris-purple-c/d/e    -- single petals
#   narcissus-d/e/f      -- incomplete; a petal and a bud
#   blade-h/k/l/m/n/o/p  -- sparse fragments, nothing to draw
KEEP = [
    # --- daffodils
    ('daffodil-a',    'flower', 160, 26),
    ('daffodil-b',    'flower', 170, 26),
    ('daffodil-c',    'flower', 164, 26),
    ('daffodil-d',    'flower', 158, 26),
    ('daffodil-e',    'flower', 134, 24),   # profile view
    ('daffodil-f',    'flower', 150, 24),   # was one asset with -g
    ('daffodil-g',    'flower', 148, 24),
    # --- narcissus
    ('narcissus-a',   'flower', 134, 22),   # was one asset with daffodil-a
    ('narcissus-b',   'flower', 132, 22),
    ('narcissus-c',   'flower', 128, 22),
    # --- irises
    ('iris-white-a',  'flower', 162, 26),   # was one asset, split in two
    ('iris-white-b',  'flower', 160, 26),
    ('iris-pink-b',   'flower', 165, 26),
    ('iris-purple-a', 'flower', 158, 26),
    # --- crocus
    ('crocus-a',      'small',  118,  0),
    ('crocus-b',      'small',  116,  0),
    ('crocus-c',      'small',  112,  0),
    # --- stems: structural, several blades rising from one root
    ('blade-a',       'stem',   195,  0),
    ('blade-b',       'stem',   180,  0),
    ('blade-c',       'stem',   175,  0),
    ('blade-d',       'stem',   168,  0),
    ('blade-f',       'stem',   190,  0),
    # --- single blades, for tufts. Scattered at a density independent of
    # both the stems and the flowers -- see WEIGHT in index.html.
    # Sized 20% under the stems so a loose blade reads as undergrowth
    # rather than as another plant.
    ('blade-e',       'grass',  120,  0),
    ('blade-g',       'grass',  132,  0),
    ('blade-i',       'grass',  126,  0),
    ('blade-j',       'grass',  118,  0),
]

# Colour grade, baked into the assets so the browser does no per-frame work.
GRADE = dict(saturation=1.26, value=1.16, contrast=0.97)

# The ground gets its own grade, because the linen and the wool want
# opposite things from one. A flower is a saturated mid-tone with a
# channel down near zero, so it has room to be lifted; the linen is a
# pale near-neutral whose three channels sit within ~50 of each other,
# and lifting THAT just walks all three into the 255 ceiling together.
# When they pin, the gap between brightest and darkest channel collapses
# and the tile goes white -- which is chroma destroyed, not gained.
#
# Concretely, with one shared grade the shipped tile came out at
# [187,198,150]: HSV saturation 0.244 against a flower's 0.838, and
# luminance 0.755, which left the runtime bgGain slider clipping from
# 1.23 up -- barely above its own 1.22 default. So the ground could
# never get vivid: `sat` had almost no chroma to multiply, and `gain`
# actively removed what there was.
#
# So this one darkens instead of lifting, and saturates harder. Lower
# value buys headroom before the runtime gain clips; higher saturation
# gives the runtime sat slider something to work with. Measured on the
# tile, shipped values against these:
#
#                       tile HSV sat   tile lum   max reachable   clips
#                                                 runtime sat     from
#   sat 1.26 val 1.16       0.244        0.755        0.584        1.23
#   sat 2.20 val 0.90       0.454        0.580        1.000        1.50
#
# The ground can now actually reach full saturation, and the default
# bgGain of 1.22 no longer sits one hundredth below the clipping onset.
# These are the least aggressive numbers that get there: pushing further
# (2.5 / 0.86) buys headroom to 1.55 but darkens the resting ground more
# than the complaint warranted. Saturation clipping in the tile is 0.72%
# of pixels and the weave contrast holds (V std 32.0 -> 26.7), so the
# texture survives; past about 2.5 it starts to flatten.
GRADE_GROUND = dict(saturation=2.20, value=0.90, contrast=1.04)

# --- ground ----------------------------------------------------------------
# The tile comes from a dedicated photograph of bare linen rather than the
# cleanest square hunted out of an embroidered panel: nothing to inpaint
# around, and a big enough crop to average the lighting out. Set
# LINEN_PHOTO to None to fall back to searching the panels.
LINEN_PHOTO = 'IMG_1643'
# Centred crop of the source, in source px, before the downscale to
# LINEN_TILE. At this photo's 45px weave pitch, 2600 puts ~58 threads in
# the tile, which is the density the panel-derived tile had.
LINEN_CROP = 2600
LINEN_TILE = 512
