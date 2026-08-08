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
    # both the stems and the flowers -- see WEIGHT in src/index.html.
    # Sized 20% under the stems so a loose blade reads as undergrowth
    # rather than as another plant.
    ('blade-e',       'grass',  120,  0),
    ('blade-g',       'grass',  132,  0),
    ('blade-i',       'grass',  126,  0),
    ('blade-j',       'grass',  118,  0),
]

# Colour grade, baked into the assets so the browser does no per-frame work.
GRADE = dict(saturation=1.26, value=1.16, contrast=0.97)

LINEN_TILE = 512
