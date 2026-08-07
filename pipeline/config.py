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
}

# --- blooms ----------------------------------------------------------------
# Bridge whatever crosses a bloom. This is the width, in px, of the widest
# stem or leaf that may pass over a flower; the closed silhouette is then
# intersected back with the foreground so crossing WOOL is kept and
# crossing LINEN is not. Occluders keep their own colour -- that is the
# point, and it is why there is no longer any erode-and-reconstruct.
FLOWER_CLOSE = 61
BLOOM_MIN_AREA = 15000

# --- grass -----------------------------------------------------------------
# Green stems and leaves are ALSO emitted on their own, so the page can
# scatter grass and flowers at independent densities. They remain part of
# the bloom cutouts they belong to.
GRASS_MIN_AREA = 9000
GRASS_MIN_HEIGHT = 200
GRASS_PER_PANEL = 12

# --- curation --------------------------------------------------------------
# Filled in from work/contact_sheet.png after a run. name -> (role, max, stem)
#   role -> how the page scatters it   (flower | clump | small | grass)
#   max  -> longest side in px in the web payload
#   stem -> virtual stem length below the sprite; the plant pivots there
# Rejected, and why:
#   daffodil-g   -- fragment, just the brown trumpet of a flower cut off-panel
#   iris-pink-b  -- a single clean petal, but it doesn't read as a flower
#   iris-pink-c  -- ditto, plus linen fringe along the top edge
#   narcissus-d  -- one petal and a bud; too ambiguous at draw size
KEEP = [
    # daffodils
    ('daffodil-b',    'flower', 168, 26),
    ('daffodil-c',    'flower', 162, 26),
    ('daffodil-d',    'flower', 158, 26),
    ('daffodil-e',    'flower', 138, 24),
    ('daffodil-a',    'clump',  180,  0),   # daffodil + narcissus together
    ('daffodil-f',    'clump',  172,  0),   # daffodil pair
    # narcissus
    ('narcissus-a',   'flower', 134, 22),
    ('narcissus-b',   'flower', 130, 22),
    ('narcissus-c',   'flower', 120, 20),
    # irises
    ('iris-white-a',  'clump',  185,  0),   # white pair, purple-outlined
    ('iris-white-b',  'clump',  178,  0),   # purple over pink
    ('iris-pink-a',   'flower', 165, 26),
    ('iris-purple-a', 'flower', 150, 26),
    ('iris-purple-b', 'flower', 145, 24),
    # crocus
    ('crocus-a',      'small',  118,  0),
    ('crocus-b',      'small',  112,  0),
    ('crocus-c',      'small',  116,  0),
    # grass -- also emitted on their own so the page can scatter them
    # at a density independent of the flowers (see WEIGHT in index.html)
    ('blade-a',       'grass',  190,  0),
    ('blade-b',       'grass',  178,  0),
    ('blade-c',       'grass',  150,  0),
    ('blade-d',       'grass',  188,  0),
    ('blade-e',       'grass',  172,  0),
    ('blade-f',       'grass',  165,  0),
    ('blade-g',       'grass',  158,  0),
    ('blade-h',       'grass',  152,  0),
    ('blade-i',       'grass',  148,  0),
    ('blade-j',       'grass',  144,  0),
]

# Colour grade, baked into the assets so the browser does no per-frame work.
GRADE = dict(saturation=1.26, value=1.16, contrast=0.97)

LINEN_TILE = 512
