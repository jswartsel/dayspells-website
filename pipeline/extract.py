#!/usr/bin/env python3
"""
Turn photographs of crewelwork panels into isolated, transparent assets.

    python pipeline/extract.py mask     # linen model + foreground, cached
    python pipeline/extract.py blooms   # cut flower heads
    python pipeline/extract.py grass    # cut green stems and leaves
    python pipeline/extract.py linen    # build the seamless ground tile
    python pipeline/extract.py sheet    # contact sheet, on a checkerboard
    python pipeline/extract.py all

Intermediates land in work/. Final assets land in assets/.

This replaces an earlier pipeline that perspective-warped off hand-read
frame corners and isolated flowers by eroding until the stems snapped.
Both are gone:

  * The 2026 panels are shot square-on and cropped to the linen, so there
    is nothing to rectify.
  * We no longer WANT plants severed from each other. A bloom is cut by
    closing across whatever crosses it and then intersecting back with the
    foreground, so an occluding stem stays put, in its own colour. That
    turned the hardest stage into the simplest one, and it recovers the
    flowers the old erosion approach had to reject -- the ones sitting too
    deep in foliage to survive having their stems cut.
"""
import os, sys
import numpy as np
import cv2
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import config as C

PHOTOS = os.path.join(ROOT, 'photos')
WORK   = os.path.join(ROOT, 'work')
ASSETS = os.path.join(ROOT, 'assets')

os.makedirs(WORK, exist_ok=True)
for d in ('flowers', 'grass', 'ground'):
    os.makedirs(os.path.join(ASSETS, d), exist_ok=True)

# panel prefix + dominant petal family -> what to call it
SPECIES = {
    ('daf', 'yellow'): 'daffodil',   ('daf', 'white'):  'narcissus',
    ('daf', 'purple'): 'crocus',     ('daf', 'pink'):   'crocus',
    ('daf', 'maroon'): 'crocus',
    ('iri', 'yellow'): 'daffodil',   ('iri', 'white'):  'iris-white',
    ('iri', 'purple'): 'iris-purple',('iri', 'pink'):   'iris-pink',
    ('iri', 'maroon'): 'iris-purple',
}


def photo(name):
    for ext in ('.png', '.jpeg', '.jpg', '.JPG', '.JPEG', '.HEIC'):
        p = os.path.join(PHOTOS, name + ext)
        if os.path.exists(p):
            return p
    raise SystemExit(f'missing photo: {os.path.join(PHOTOS, name)}.png')


def load(name):
    """EXIF-rotated, resampled so every tuned pixel constant means the same
    thing regardless of what camera the panel was shot on."""
    im = ImageOps.exif_transpose(Image.open(photo(name)).convert('RGB'))
    bgr = np.array(im)[:, :, ::-1].copy()
    s = C.PANEL_H / bgr.shape[0]
    return cv2.resize(bgr, (round(bgr.shape[1] * s), C.PANEL_H), interpolation=cv2.INTER_AREA)


def smooth(im):
    """The raw weave has enough contrast to register as signal; bilateral
    then median knocks it down without softening the stitch boundaries."""
    return cv2.medianBlur(cv2.bilateralFilter(im, 15, 60, 15), 9)


# ---------------------------------------------------------------- 1. mask ---
def linen_distance(im):
    """Normalised Lab distance from the linen, per pixel.

    The linen reference is the dominant chroma mode of the entire panel.
    The previous version took a median of the outer 3-4% of the frame,
    which silently poisons the whole segmentation if any stitching runs to
    the edge -- and on these panels it does.
    """
    lab = cv2.cvtColor(smooth(im), cv2.COLOR_BGR2LAB).astype(np.float32)
    a, b = lab[:, :, 1], lab[:, :, 2]
    hist, ea, eb = np.histogram2d(a.ravel(), b.ravel(), bins=64, range=[[0, 255], [0, 255]])
    ia, ib = np.unravel_index(np.argmax(cv2.GaussianBlur(hist, (0, 0), 1.5)), hist.shape)
    ca, cb = (ea[ia] + ea[ia + 1]) / 2, (eb[ib] + eb[ib + 1]) / 2
    near = (np.abs(a - ca) < 6) & (np.abs(b - cb) < 6)
    ref = np.median(lab[near], axis=0)
    spread = np.maximum(np.percentile(np.abs(lab[near] - ref), 90, axis=0), 2.0)
    return np.sqrt((((lab - ref) / spread) ** 2) @ np.array([1.0, 2.2, 2.2]))


def families(im, fg):
    """Split the foreground into colour families. Chroma, not topology, is
    what actually separates wool here."""
    hsv = cv2.cvtColor(smooth(im), cv2.COLOR_BGR2HSV)
    H, S, V = [hsv[:, :, i].astype(int) for i in range(3)]
    out = {}
    for name, r in C.FAMILIES.items():
        m = fg.copy()
        if 'v_min' in r: m &= V >= r['v_min']
        if 'v_max' in r: m &= V <  r['v_max']
        if 's_min' in r: m &= S >  r['s_min']
        if 's_max' in r: m &= S <= r['s_max']
        if 's'     in r: m &= (S > r['s'][0]) & (S <= r['s'][1])
        if 'v'     in r: m &= (V >= r['v'][0]) & (V < r['v'][1])
        if 'h'     in r: m &= (H >= r['h'][0]) & (H <= r['h'][1])
        if 'h_wrap' in r:
            lo, hi = r['h_wrap']
            m &= (H > lo) | (H < hi)
        out[name] = m
    # Deep maroon petals are dark enough to land in 'dark', which exists
    # for the brown-black foliage. Leaving them there cost every crocus
    # half its petals.
    if 'maroon' in out:
        out['dark'] = out['dark'] & ~out['maroon']
    return out


def _watershed(m, frac, min_area):
    dt = cv2.distanceTransform((m > 0).astype(np.uint8), cv2.DIST_L2, 5)
    sure = ((dt > frac * dt.max()) * 255).astype(np.uint8)
    n, mk = cv2.connectedComponents(sure)
    if n <= 2:
        return []
    ws = cv2.watershed(cv2.cvtColor(m, cv2.COLOR_GRAY2BGR), mk.copy())
    parts = []
    for i in range(1, n):
        p = (((ws == i) & (m > 0)) * 255).astype(np.uint8)
        if (p > 0).sum() >= min_area:
            parts.append(small_holes(largest(p)))
    return parts


def split_parts(m, min_area=None, min_part=None, max_parts=None, depth=2):
    """Split a mask where two heads touch, and only there.

    Two blooms that meet join at a narrow waist, so thresholding the
    distance transform leaves one marker per head; watershed then assigns
    every pixel. The threshold is swept rather than fixed, because a fixed
    one cannot fit both a pair of fat daffodil heads and a slim iris: the
    value that separated the irises shattered them into single petals,
    and the value that held the irises together left the daffodils merged.

    The accept rule is scale-free instead. A split only counts if every
    part is a substantial share of the parent -- two flowers split
    roughly in half, whereas a flower shedding one petal does not. Of the
    splits that qualify, take the most balanced.
    """
    min_area  = C.SPLIT_MIN_AREA if min_area  is None else min_area
    min_part  = C.SPLIT_MIN_PART if min_part  is None else min_part
    max_parts = C.SPLIT_MAX_PARTS if max_parts is None else max_parts
    total = (m > 0).sum()
    best, best_score = None, 0.0
    for frac in np.arange(0.26, 0.72, 0.04):
        parts = _watershed(m, float(frac), min_area)
        if not (2 <= len(parts) <= max_parts):
            continue
        areas = [(p > 0).sum() for p in parts]
        if sum(areas) < 0.72 * total:      # watershed lost too much
            continue
        share = min(areas) / total
        if share >= min_part and share > best_score:
            best, best_score = parts, share
    if best is None:
        return [m]
    # Recurse. Three flowers in a mass split two ways first, leaving one
    # half still merged; splitting again separates it without having to
    # loosen the share rule, which would start shedding single petals.
    if depth > 0:
        out = []
        for p in best:
            out.extend(split_parts(p, min_area, min_part, max_parts, depth - 1))
        return out
    return best


def stage_mask():
    for name, tag in C.PANELS:
        im = load(name)
        cv2.imwrite(os.path.join(WORK, f'{name}_flat.png'), im)
        d = linen_distance(im)
        np.save(os.path.join(WORK, f'{name}_dist.npy'), d)
        cut = im.copy(); cut[d <= C.FG_THRESHOLD] = (255, 0, 255)
        h = 900; s = h / im.shape[0]
        cv2.imwrite(os.path.join(WORK, f'{name}_maskcheck.png'), np.hstack([
            cv2.resize(im, (round(im.shape[1] * s), h), interpolation=cv2.INTER_AREA),
            cv2.resize(cut, (round(im.shape[1] * s), h), interpolation=cv2.INTER_AREA)]))
        print(f'  {name}: {100*(d>C.FG_THRESHOLD).mean():.1f}% foreground '
              f'-> work/{name}_maskcheck.png')


def load_mask(name):
    p = os.path.join(WORK, f'{name}_dist.npy')
    if not os.path.exists(p):
        stage_mask()
    return load(name), np.load(p)


# ------------------------------------------------------- shared mask tools ---
def small_holes(m, maxfrac=0.004):
    """Fill enclosed gaps, but only small ones. A big enclosed patch is
    linen showing between petals and should stay transparent."""
    h, w = m.shape
    pad = np.zeros((h + 4, w + 4), np.uint8); pad[2:-2, 2:-2] = m
    ff = pad.copy()
    cv2.floodFill(ff, np.zeros((h + 6, w + 6), np.uint8), (0, 0), 255)
    holes = cv2.bitwise_not(ff) & cv2.bitwise_not(pad)
    n, lab, st, _ = cv2.connectedComponentsWithStats(holes, 8)
    small = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] < maxfrac * m.size]
    return (pad | (np.isin(lab, small).astype(np.uint8) * 255))[2:-2, 2:-2]


def largest(m):
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return m
    return ((lab == 1 + np.argmax([st[i, cv2.CC_STAT_AREA] for i in range(1, n)])) * 255).astype(np.uint8)


def grade(im):
    g = C.GRADE
    a = im[:, :, 3:] if im.shape[2] == 4 else None
    hsv = cv2.cvtColor(im[:, :, :3], cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * g['saturation'], 0, 255)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * g['value'], 0, 255)
    b = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    b = np.clip((b - 128) * g['contrast'] + 128, 0, 255).astype(np.uint8)
    return np.dstack([b, a]) if a is not None else b


def write_asset(path, img, m, pad=12):
    ys, xs = np.where(m > 0)
    y0, y1 = max(0, ys.min() - pad), min(m.shape[0], ys.max() + pad)
    x0, x1 = max(0, xs.min() - pad), min(m.shape[1], xs.max() + pad)
    crop, mm = img[y0:y1, x0:x1], m[y0:y1, x0:x1]
    a = cv2.GaussianBlur(mm.astype(np.float32), (0, 0), 1.7)
    a = np.clip((a - 40) * (255 / 175), 0, 255)
    gy = np.minimum(np.arange(mm.shape[0]), mm.shape[0] - 1 - np.arange(mm.shape[0]))
    gx = np.minimum(np.arange(mm.shape[1]), mm.shape[1] - 1 - np.arange(mm.shape[1]))
    a *= np.clip(np.minimum.outer(gy, gx) / 6.0, 0, 1)   # never a hard line at the border
    cv2.imwrite(path, grade(np.dstack([crop, a.astype(np.uint8)])))
    return mm.shape[1], mm.shape[0]


# -------------------------------------------------------------- 2. blooms ---
def stage_blooms():
    """A bloom is a contiguous patch of petal-coloured wool -- any petal
    colour. Componenting a SINGLE colour shatters the white irises, whose
    petals are separated by purple outlines.
    """
    out = os.path.join(ASSETS, 'flowers')
    counts = {}
    for name, tag in C.PANELS:
        im, d = load_mask(name)
        fg = d > C.FG_THRESHOLD
        fam = families(im, fg)
        fgm = (fg * 255).astype(np.uint8)
        bloom = fg & ~fam['green'] & ~fam['dark']
        bm = cv2.morphologyEx((bloom * 255).astype(np.uint8), cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
        bm = cv2.morphologyEx(bm, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(bm, 8)
        idx = sorted([i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= C.BLOOM_MIN_AREA],
                     key=lambda i: -st[i, cv2.CC_STAT_AREA])
        for i in idx:
            petals = ((lab == i) * 255).astype(np.uint8)
            k = C.FLOWER_CLOSE | 1
            closed = cv2.morphologyEx(petals, cv2.MORPH_CLOSE,
                                      cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
            # crossing wool is kept, crossing linen is not
            sil = largest(small_holes(closed & fgm))
            parts = split_parts(sil)
            for part in parts:
                share = {f: (fam[f] & (part > 0)).sum()
                         for f in ('yellow', 'white', 'purple', 'pink', 'maroon')}
                dom = max(share, key=share.get)
                # Pale salmon irises read as 'white' on saturation alone,
                # which named a plainly pink flower iris-white. Pink wins
                # the tie when there is a real amount of it.
                if dom == 'white' and share['pink'] >= 0.4 * share['white']:
                    dom = 'pink'
                sp = SPECIES[(tag, dom)]
                counts[sp] = counts.get(sp, 0) + 1
                tagname = f'{sp}-{chr(96 + counts[sp])}'
                w, h = write_asset(os.path.join(out, f'{tagname}.png'), im, part)
                note = f'  (1 of {len(parts)})' if len(parts) > 1 else ''
                print(f'  {tagname:16s} {w:4d}x{h:4d}{note}')


# --------------------------------------------------------------- 3. grass ---
def stage_grass():
    """Green stems and leaves, emitted on their own so the page can scatter
    grass and flowers at independent densities. They stay part of the bloom
    cutouts too -- this is an addition, not a removal."""
    out = os.path.join(ASSETS, 'grass')
    k = 0
    for name, tag in C.PANELS:
        im, d = load_mask(name)
        fam = families(im, d > C.FG_THRESHOLD)
        gm = cv2.morphologyEx((fam['green'] * 255).astype(np.uint8),
                              cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
        gm = cv2.morphologyEx(gm, cv2.MORPH_CLOSE, np.ones((13, 13), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(gm, 8)
        cand = [(st[i, cv2.CC_STAT_AREA], i) for i in range(1, n)
                if st[i, cv2.CC_STAT_AREA] >= C.GRASS_MIN_AREA
                and st[i, cv2.CC_STAT_HEIGHT] >= C.GRASS_MIN_HEIGHT]
        for a, i in sorted(cand, reverse=True)[:C.GRASS_PER_PANEL]:
            m = small_holes(((lab == i) * 255).astype(np.uint8))
            # a clump of stems rising from one root splits the same way
            # two touching blooms do
            # One round only. Stems have no second waist to find, so
            # recursing just shatters them into segments.
            for part in split_parts(m, min_area=C.GRASS_MIN_AREA,
                                    min_part=C.GRASS_SPLIT_MIN_PART,
                                    max_parts=3, depth=0):
                tagname = f'blade-{chr(97 + k)}'; k += 1
                w, h = write_asset(os.path.join(out, f'{tagname}.png'), im, part)
                print(f'  {tagname:16s} {w:4d}x{h:4d}  aspect={h/max(w,1):.1f}')


# --------------------------------------------------------------- 4. linen ---
def linen_from_photo():
    """A square of bare linen, straight from a dedicated photograph.

    Preferred over hunting a clean square out of an embroidered panel:
    there is no stitching to inpaint around, and the crop can be big
    enough to average out the lighting. LINEN_CROP is chosen so the
    downscaled tile carries about the same number of threads as the
    panel-derived one did -- ~58 at a 45px weave pitch.
    """
    S = C.LINEN_TILE
    im = ImageOps.exif_transpose(Image.open(photo(C.LINEN_PHOTO)).convert('RGB'))
    bgr = np.array(im)[:, :, ::-1].copy()
    h, w = bgr.shape[:2]
    c = min(C.LINEN_CROP, h, w)
    y, x = (h - c) // 2, (w - c) // 2
    crop = bgr[y:y + c, x:x + c]
    print(f'  {C.LINEN_PHOTO}: {w}x{h} -> centre {c}px -> {S}px tile')
    return cv2.resize(crop, (S, S), interpolation=cv2.INTER_AREA)


def linen_from_panels():
    """Fallback: the cleanest bare square in either embroidered panel."""
    S = C.LINEN_TILE
    best = None
    for name, tag in C.PANELS:
        im, d = load_mask(name)
        ii = cv2.integral((d > 3.0).astype(np.float32))
        for y in range(40, d.shape[0] - S - 40, 12):
            for x in range(30, d.shape[1] - S - 30, 12):
                s = ii[y + S, x + S] - ii[y, x + S] - ii[y + S, x] + ii[y, x]
                if best is None or s < best[0]:
                    best = (s, name, x, y)
    score, name, X, Y = best
    print(f'  cleanest square: {name} ({X},{Y}) -- {100*score/S**2:.2f}% stitching')
    im, d = load_mask(name)
    raw = im[Y:Y + S, X:X + S].copy()
    stray = cv2.dilate((d[Y:Y + S, X:X + S] > C.FG_THRESHOLD).astype(np.uint8),
                       np.ones((15, 15), np.uint8))
    if stray.any():
        raw = cv2.inpaint(raw, stray, 12, cv2.INPAINT_NS)
    return raw


def stage_linen():
    """Build the seamless ground tile.

    Mirror-tiling is the obvious trick and it's wrong: it produces
    four-fold symmetric blobs that read as wallpaper the moment they
    repeat. Rolling by half and cross-fading keeps the weave running the
    same direction everywhere.

    The high-pass below is what makes a photograph usable: it subtracts a
    heavy blur of the tile from itself, which removes the lighting
    falloff across the shot and leaves only the weave.
    """
    S = C.LINEN_TILE
    raw = linen_from_photo() if getattr(C, 'LINEN_PHOTO', None) else linen_from_panels()

    p = raw.astype(np.float32)
    p -= cv2.GaussianBlur(p, (0, 0), 80)
    p += np.median(raw.reshape(-1, 3), axis=0)

    h = S // 2
    rolled = np.roll(np.roll(p, h, 0), h, 1)
    ramp = np.clip(np.abs(np.arange(S) - h) / (S * 0.22), 0, 1)
    w = np.minimum(ramp[None, :, None], ramp[:, None, None])
    tile = np.clip(rolled * w + p * (1 - w), 0, 255).astype(np.uint8)
    m = tile.reshape(-1, 3).mean(0)
    tile = np.clip((tile.astype(np.float32) - m) * 0.82 + m, 0, 255).astype(np.uint8)

    cv2.imwrite(os.path.join(ASSETS, 'ground', f'linen-tile-{S}.png'), grade(tile))
    cv2.imwrite(os.path.join(WORK, 'linen_check.png'), cv2.resize(np.tile(tile, (3, 3, 1)), (600, 600)))
    print(f'  assets/ground/linen-tile-{S}.png  (3x3 preview in work/linen_check.png)')


# --------------------------------------------------------------- 5. sheet ---
def stage_sheet():
    """Contact sheet on a checkerboard -- the only reliable way to spot bad
    alpha. Read it before editing config.KEEP."""
    items = []
    for sub in ('flowers', 'grass'):
        d = os.path.join(ASSETS, sub)
        for f in sorted(os.listdir(d)):
            if f.endswith('.png'):
                items.append((f[:-4], os.path.join(d, f)))
    if not items:
        return print('  nothing to show yet')
    CELL, COLS = 250, 7
    rows = (len(items) + COLS - 1) // COLS
    ck = np.indices((rows * CELL, COLS * CELL)).sum(0) // 16 % 2
    sheet = (ck * 40 + 60).astype(np.uint8)[:, :, None].repeat(3, 2)
    for i, (n, path) in enumerate(items):
        im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        s = min((CELL - 36) / im.shape[1], (CELL - 36) / im.shape[0])
        im = cv2.resize(im, (max(1, int(im.shape[1] * s)), max(1, int(im.shape[0] * s))),
                        interpolation=cv2.INTER_AREA)
        a = im[:, :, 3:4].astype(np.float32) / 255
        r, c = divmod(i, COLS)
        y0 = r * CELL + 28 + (CELL - 36 - im.shape[0]) // 2
        x0 = c * CELL + 18 + (CELL - 36 - im.shape[1]) // 2
        reg = sheet[y0:y0 + im.shape[0], x0:x0 + im.shape[1]]
        sheet[y0:y0 + im.shape[0], x0:x0 + im.shape[1]] = (im[:, :, :3] * a + reg * (1 - a)).astype(np.uint8)
        cv2.putText(sheet, n, (c * CELL + 8, r * CELL + 20), cv2.FONT_HERSHEY_PLAIN, .85, (255, 255, 255), 1)
    cv2.imwrite(os.path.join(WORK, 'contact_sheet.png'), sheet)
    print(f'  work/contact_sheet.png  ({len(items)} assets)')


STAGES = {'mask': stage_mask, 'blooms': stage_blooms, 'grass': stage_grass,
          'linen': stage_linen, 'sheet': stage_sheet}

if __name__ == '__main__':
    args = sys.argv[1:] or ['all']
    order = list(STAGES) if args == ['all'] else args
    for a in order:
        if a not in STAGES:
            raise SystemExit(f'unknown stage: {a}\nstages: {", ".join(STAGES)}, all')
        print(f'[{a}]')
        STAGES[a]()
