"""
Everything hand-measured about the two source photographs.

If you re-shoot the panels, or add new ones, this is the only file that
needs new numbers. Corners are read off a grid overlay -- run

    python pipeline/extract.py grid

and open work/<name>_grid.png to read them.
"""

# Flattened panel size, in px. ~87 px per cm of the real embroidery.
PANEL_W, PANEL_H = 1300, 3050

GRID_SCALE = 8   # the grid overlay is 1/8 scale

# Inner edge of the linen, in grid coords: top-left, top-right, bottom-right, bottom-left.
# Keep these just inside the frame bevel or you'll pull yellow paint into the ground sample.
CORNERS = {
    'IMG_1637': [(151, 49), (388, 54), (385, 635), (136, 634)],
    'IMG_1638': [(156, 69), (397, 65), (394, 627), (149, 629)],
}

# Foreground threshold: normalised Lab distance from the linen reference.
FG_THRESHOLD = 4.2

# One seed point per flower, in flattened panel coords, plus a starting
# cut depth. The extractor sweeps depth around this value and keeps
# whichever result leaves the silhouette clearest of its crop border.
#
# Cut depth is the erosion kernel used to sever stems. It must exceed the
# stem width (~40px here) or the flood will run into the whole plant.
FLOWER_SEEDS = {
    'IMG_1637': [
        ('iris-purple-a',  470,  610, 33),
        ('iris-pink-a',   1010,  745, 33),
        ('iris-purple-b',  680, 1145, 33),
        ('iris-pink-b',    960, 1400, 33),
        ('iris-white-a',   400, 1455, 27),
        ('iris-white-b',   560, 1745, 27),
        ('daffodil-a',     975, 1760, 25),
        ('daffodil-b',     905, 1960, 25),
    ],
    'IMG_1638': [
        ('daffodil-c',     357,  512, 27),
        ('daffodil-d',     290,  885, 27),
        ('daffodil-e',     780,  690, 27),
        ('daffodil-f',     440, 1250, 27),
        ('daffodil-g',     925, 1200, 27),
        ('narcissus-a',    170, 1575, 17),
        ('narcissus-b',    400, 1525, 17),
        ('narcissus-c',    300, 1790, 17),
        ('narcissus-d',    570, 1810, 17),
    ],
}

# Crocuses sit against near-black foliage. Eroding kills the flower before
# it kills its neighbours, so these get a brightness gate first: drop
# anything darker than V_GATE, then isolate what's left.
CROCUS_SEEDS = {
    'IMG_1638': [
        ('crocus-a',  700, 2320),
        ('crocus-b', 1058, 2248),
        ('crocus-c',  862, 2452),
        ('crocus-d',  790, 2400),
    ],
}
V_GATE = 96

# Grass is found automatically: hue-gated foliage mask, split into blades,
# keep the largest elongated components.
FOLIAGE_PER_PANEL = {'IMG_1637': 7, 'IMG_1638': 6}

# --- curation -------------------------------------------------------------
# Not everything the extractor produces is usable. These are the keepers.
# Rejected, and why:
#   iris-purple-b, iris-pink-b, iris-white-b, daffodil-a, daffodil-b,
#   narcissus-b/c/d  -- flower sits too deep in surrounding foliage; the
#                       erosion that severs the stems also eats the petals
#   crocus-a         -- brightness gate let bare linen through
#
# role   -> how it's scattered (see WEIGHT in the page)
# max    -> longest side, in px, in the web payload
# stem   -> virtual stem length below the sprite; the plant pivots there
KEEP = [
    ('iris-purple-a', 'flower', 168, 26),
    ('iris-pink-a',   'flower', 158, 26),
    ('iris-white-a',  'flower', 152, 24),
    ('daffodil-c',    'flower', 140, 22),
    ('daffodil-d',    'flower', 132, 22),
    ('daffodil-e',    'flower', 138, 22),
    ('daffodil-g',    'flower', 142, 22),
    ('daffodil-f',    'clump',  165,  0),
    ('narcissus-a',   'flower', 104, 18),
    ('crocus-b',      'small',   96,  0),
    ('crocus-c',      'small',  112,  0),
    ('crocus-d',      'small',  118,  0),
    ('blade-37-0',    'grass',  175,  0),
    ('blade-37-1',    'grass',  172,  0),
    ('blade-37-2',    'grass',  150,  0),
    ('blade-38-0',    'grass',  168,  0),
    ('blade-38-1',    'grass',  160,  0),
    ('blade-38-2',    'grass',  152,  0),
]

# Colour grade, baked into the assets so the browser does no per-frame work.
GRADE = dict(saturation=1.26, value=1.16, contrast=0.97)

# Where the seamless ground tile comes from. Found by searching both panels
# for the 512px square with the least stitching in it.
LINEN_TILE = 512
