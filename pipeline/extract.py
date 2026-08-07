#!/usr/bin/env python3
"""
Turn photographs of crewelwork panels into isolated, transparent assets.

    python pipeline/extract.py grid      # overlay coords, to read frame corners
    python pipeline/extract.py flatten   # rectify + relight both panels
    python pipeline/extract.py flowers   # cut individual flower heads
    python pipeline/extract.py foliage   # cut individual grass blades
    python pipeline/extract.py linen     # build the seamless ground tile
    python pipeline/extract.py sheet     # contact sheet of everything, on a checkerboard
    python pipeline/extract.py all

Intermediates land in work/. Final assets land in assets/.

The hard part is step 4. Everything in a crewel panel connects through
stems, so a flood fill from one flower grabs the whole plant. The fix is
to erode until the stems snap, keep the blob nearest the seed point, then
reconstruct it back under the original mask. The erosion radius must
exceed half the stem width -- at this resolution stems are ~40px, so a
kernel below ~45 does nothing. The extractor sweeps depth and scores each
result on how much of the silhouette runs along the crop border, because
a real flower silhouette never does.
"""
import os, sys, json
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
PANELS = list(C.CORNERS.keys())

os.makedirs(WORK, exist_ok=True)
for d in ('flowers', 'grass', 'ground'):
    os.makedirs(os.path.join(ASSETS, d), exist_ok=True)


def _photo(name):
    for ext in ('.jpeg', '.jpg', '.JPG', '.JPEG', '.png'):
        p = os.path.join(PHOTOS, name + ext)
        if os.path.exists(p):
            return p
    raise SystemExit(f'missing photo: {os.path.join(PHOTOS, name)}.jpeg')


# --------------------------------------------------------------- 1. grid ---
def stage_grid():
    """Coordinate overlay for reading frame corners by eye."""
    for name in PANELS:
        im = ImageOps.exif_transpose(Image.open(_photo(name)).convert('RGB'))
        im.save(os.path.join(WORK, f'{name}_full.png'))
        s = C.GRID_SCALE
        th = np.array(im.resize((im.width // s, im.height // s)))[:, :, ::-1].copy()
        for x in range(0, th.shape[1], 50):
            cv2.line(th, (x, 0), (x, th.shape[0]), (0, 0, 255), 1)
            cv2.putText(th, str(x), (x + 2, 12), cv2.FONT_HERSHEY_PLAIN, .7, (0, 0, 255), 1)
        for y in range(0, th.shape[0], 50):
            cv2.line(th, (0, y), (th.shape[1], y), (255, 60, 0), 1)
            cv2.putText(th, str(y), (2, y + 12), cv2.FONT_HERSHEY_PLAIN, .7, (255, 60, 0), 1)
        cv2.imwrite(os.path.join(WORK, f'{name}_grid.png'), th)
        print(f'  {name}: work/{name}_grid.png  (coords are 1/{s} scale)')


# ------------------------------------------------------------ 2. flatten ---
def stage_flatten():
    """Perspective-correct off the frame corners, then flatten the lighting.

    An earlier version divided out the whole colour field and destroyed the
    pinks -- the pink irises came back mint. Correcting luminance only, and
    lifting chroma slightly, keeps the wool colour intact.
    """
    for name in PANELS:
        full = os.path.join(WORK, f'{name}_full.png')
        if not os.path.exists(full):
            im = ImageOps.exif_transpose(Image.open(_photo(name)).convert('RGB'))
            im.save(full)
        img = cv2.imread(full)
        s = C.GRID_SCALE
        src = np.float32([(x * s, y * s) for x, y in C.CORNERS[name]])
        dst = np.float32([(0, 0), (C.PANEL_W, 0), (C.PANEL_W, C.PANEL_H), (0, C.PANEL_H)])
        flat = cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst),
                                   (C.PANEL_W, C.PANEL_H), flags=cv2.INTER_AREA)
        cv2.imwrite(os.path.join(WORK, f'{name}_flat.png'), flat)

        lab = cv2.cvtColor(flat.astype(np.float32) / 255, cv2.COLOR_BGR2LAB)
        L = lab[:, :, 0]
        field = cv2.GaussianBlur(L, (0, 0), 220)
        lab[:, :, 0] = np.clip(L * (float(field.mean()) / np.maximum(field, 1e-3)), 0, 100)
        out = np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2BGR) * 255, 0, 255).astype(np.uint8)
        hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.13, 0, 255)
        out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        cv2.imwrite(os.path.join(WORK, f'{name}_even.png'), out)

        np.save(os.path.join(WORK, f'{name}_dist.npy'), foreground_distance(out))
        print(f'  {name}: flattened + evened')


def foreground_distance(bgr):
    """Normalised Lab distance from the linen, per pixel.

    Measured on a bilateral-filtered copy: the raw weave has enough
    contrast to register as signal otherwise, and you get 70% "foreground".
    """
    sm = cv2.medianBlur(cv2.bilateralFilter(bgr, 15, 60, 15), 9)
    lab = cv2.cvtColor(sm, cv2.COLOR_BGR2LAB).astype(np.float32)
    h, w = bgr.shape[:2]
    margins = np.concatenate([
        lab[:int(h * .03)].reshape(-1, 3), lab[int(h * .97):].reshape(-1, 3),
        lab[:, :int(w * .04)].reshape(-1, 3), lab[:, int(w * .96):].reshape(-1, 3)])
    ref = np.median(margins, axis=0)
    spread = np.maximum(np.percentile(np.abs(margins - ref), 90, axis=0), 2.0)
    return np.sqrt(((lab - ref) / spread) ** 2 @ np.array([1.0, 2.2, 2.2]))


# ------------------------------------------------------- shared mask tools ---
def fill_holes(m, maxfrac=0.010):
    """Fill enclosed gaps, but only small ones -- big enclosed patches are
    usually linen showing between leaves, and should stay transparent."""
    h, w = m.shape
    pad = np.zeros((h + 4, w + 4), np.uint8); pad[2:-2, 2:-2] = m
    ff = pad.copy()
    cv2.floodFill(ff, np.zeros((h + 6, w + 6), np.uint8), (0, 0), 255)
    holes = cv2.bitwise_not(ff) & cv2.bitwise_not(pad)
    n, lab, st, _ = cv2.connectedComponentsWithStats(holes, 8)
    small = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] < maxfrac * m.size]
    return (pad | (np.isin(lab, small).astype(np.uint8) * 255))[2:-2, 2:-2]


def isolate(m, sep, cx, cy, grow=None):
    """Sever the stems, keep the blob nearest (cx,cy), grow it back."""
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), 2)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8), 1)
    m = fill_holes(m)
    seed = cv2.erode(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (sep, sep)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(seed, 8)
    if n <= 1:
        return None
    h, w = m.shape
    best, score = None, -1e18
    for i in range(1, n):
        a = st[i, cv2.CC_STAT_AREA]
        yy = st[i, cv2.CC_STAT_TOP] + st[i, cv2.CC_STAT_HEIGHT] / 2
        xx = st[i, cv2.CC_STAT_LEFT] + st[i, cv2.CC_STAT_WIDTH] / 2
        d = np.hypot((yy - cy) / h, (xx - cx) / w)
        s = a * (1.0 - min(d, 0.95))
        if s > score:
            score, best = s, i
    cur = ((lab == best) * 255).astype(np.uint8)
    for _ in range(grow if grow is not None else int(sep / 6) + 2):
        nxt = cv2.dilate(cur, np.ones((7, 7), np.uint8)) & m
        if (nxt == cur).all():
            break
        cur = nxt
    return cur


def edge_touch(a):
    """% of the crop border the mask runs along. A real silhouette: ~0."""
    return max(a[0].mean(), a[-1].mean(), a[:, 0].mean(), a[:, -1].mean()) * 100


def write_asset(path, img, m):
    ys, xs = np.where(m > 0)
    pad = 10
    y0, y1 = max(0, ys.min() - pad), min(m.shape[0], ys.max() + pad)
    x0, x1 = max(0, xs.min() - pad), min(m.shape[1], xs.max() + pad)
    crop, mm = img[y0:y1, x0:x1], m[y0:y1, x0:x1]
    a = cv2.GaussianBlur(mm.astype(np.float32), (0, 0), 1.7)
    a = np.clip((a - 40) * (255 / 175), 0, 255)
    gy = np.minimum(np.arange(mm.shape[0]), mm.shape[0] - 1 - np.arange(mm.shape[0]))
    gx = np.minimum(np.arange(mm.shape[1]), mm.shape[1] - 1 - np.arange(mm.shape[1]))
    a *= np.clip(np.minimum.outer(gy, gx) / 6.0, 0, 1)   # never a hard line at the border
    cv2.imwrite(path, np.dstack([crop, a.astype(np.uint8)]))
    return mm.shape[1], mm.shape[0], edge_touch(a > 128)


# ------------------------------------------------------------ 3. flowers ---
def stage_flowers():
    out = os.path.join(ASSETS, 'flowers')
    for name, seeds in C.FLOWER_SEEDS.items():
        img = cv2.imread(os.path.join(WORK, f'{name}_even.png'))
        full = ((np.load(os.path.join(WORK, f'{name}_dist.npy')) > C.FG_THRESHOLD) * 255).astype(np.uint8)
        H, W = full.shape
        for tag, sx, sy, sep in seeds:
            got, best = None, 1e18
            for half in (240, 320, 400):
                y0, y1 = max(0, sy - half), min(H, sy + half)
                x0, x1 = max(0, sx - half), min(W, sx + half)
                sub = full[y0:y1, x0:x1]
                for k in range(int(sep * 1.2), int(sep * 3.2), 8):
                    m = isolate(sub.copy(), k | 1, sx - x0, sy - y0)
                    if m is None or m.max() == 0:
                        continue
                    frac = (m > 0).mean()
                    if frac < 0.03 or frac > 0.55:
                        continue
                    sc = edge_touch(m > 0) - frac * 14   # cheap border, decent size
                    if sc < best:
                        best, got = sc, (m, img[y0:y1, x0:x1], k)
                if got and edge_touch(got[0] > 0) < 8:
                    break
            if not got:
                print(f'  !! {tag}: no clean cut found')
                continue
            w, h, et = write_asset(os.path.join(out, f'{tag}.png'), got[1], got[0])
            print(f'  {tag:16s} {w:4d}x{h:4d}  border={et:4.1f}%  cut={got[2]}')

    # crocuses need the near-black foliage gone before isolating
    for name, seeds in C.CROCUS_SEEDS.items():
        img = cv2.imread(os.path.join(WORK, f'{name}_even.png'))
        dist = np.load(os.path.join(WORK, f'{name}_dist.npy'))
        V = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 2]
        bright = ((dist > C.FG_THRESHOLD) & (V > C.V_GATE)).astype(np.uint8) * 255
        for tag, sx, sy in seeds:
            got, best = None, 1e18
            for half in (170, 230, 300):
                y0, y1 = max(0, sy - half), min(img.shape[0], sy + half)
                x0, x1 = max(0, sx - half), min(img.shape[1], sx + half)
                sub = bright[y0:y1, x0:x1]
                for k in range(15, 71, 6):
                    m = isolate(sub.copy(), k | 1, sx - x0, sy - y0, grow=int(k / 6) + 3)
                    if m is None or m.max() == 0:
                        continue
                    f = (m > 0).mean()
                    if f < 0.02 or f > 0.42:
                        continue
                    sc = edge_touch(m > 0) - f * 14
                    if sc < best:
                        best, got = sc, (m, img[y0:y1, x0:x1], k)
            if not got:
                print(f'  !! {tag}')
                continue
            w, h, et = write_asset(os.path.join(out, f'{tag}.png'), got[1], got[0])
            print(f'  {tag:16s} {w:4d}x{h:4d}  border={et:4.1f}%  cut={got[2]}')


# ------------------------------------------------------------ 4. foliage ---
def stage_foliage():
    """Grass is found, not seeded: hue-gate the foliage, split it, keep the
    biggest elongated pieces."""
    out = os.path.join(ASSETS, 'grass')
    for name, want in C.FOLIAGE_PER_PANEL.items():
        im = cv2.imread(os.path.join(WORK, f'{name}_even.png'))
        d = np.load(os.path.join(WORK, f'{name}_dist.npy'))
        hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
        Hh, Vv = hsv[:, :, 0].astype(int), hsv[:, :, 2].astype(int)
        foliage = ((d > C.FG_THRESHOLD) & (Hh > 28) & (Hh < 95) & (Vv < 150)).astype(np.uint8) * 255
        foliage = cv2.morphologyEx(foliage, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8), 2)
        seed = cv2.erode(foliage, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
        n, lab, st, _ = cv2.connectedComponentsWithStats(seed, 8)
        cand = []
        for i in range(1, n):
            a, w, h = st[i, cv2.CC_STAT_AREA], st[i, cv2.CC_STAT_WIDTH], st[i, cv2.CC_STAT_HEIGHT]
            if a < 9000 or h < 260:
                continue
            cand.append((a, i, h / max(w, 1)))
        cand.sort(key=lambda t: -t[0] * min(t[2], 4))
        for j, (a, i, ar) in enumerate(cand[:want]):
            cur = ((lab == i) * 255).astype(np.uint8)
            for _ in range(7):
                nxt = cv2.dilate(cur, np.ones((7, 7), np.uint8)) & foliage
                if (nxt == cur).all():
                    break
                cur = nxt
            tag = f'blade-{name[-2:]}-{j}'
            w, h, et = write_asset(os.path.join(out, f'{tag}.png'), im, cur)
            print(f'  {tag:16s} {w:4d}x{h:4d}  border={et:4.1f}%  aspect={ar:.1f}')


# -------------------------------------------------------------- 5. linen ---
def stage_linen():
    """Find the cleanest bare square in either panel, scrub any stray
    stitching out of it, and make it tile.

    Mirror-tiling is the obvious trick and it's wrong: it produces
    four-fold symmetric blobs that read as wallpaper the moment they
    repeat. Rolling by half and cross-fading the seam keeps the weave
    running the same direction everywhere.
    """
    S = C.LINEN_TILE
    best = None
    for name in PANELS:
        d = np.load(os.path.join(WORK, f'{name}_dist.npy'))
        ii = cv2.integral((d > 3.0).astype(np.float32))
        for y in range(60, d.shape[0] - S - 60, 12):
            for x in range(40, d.shape[1] - S - 40, 12):
                s = ii[y + S, x + S] - ii[y, x + S] - ii[y + S, x] + ii[y, x]
                if best is None or s < best[0]:
                    best = (s, name, x, y)
    score, name, X, Y = best
    print(f'  cleanest square: {name} ({X},{Y}) -- {100*score/S**2:.2f}% stitching')

    src = cv2.imread(os.path.join(WORK, f'{name}_even.png'))
    dist = np.load(os.path.join(WORK, f'{name}_dist.npy'))
    raw = src[Y:Y + S, X:X + S].copy()
    stray = cv2.dilate((dist[Y:Y + S, X:X + S] > C.FG_THRESHOLD).astype(np.uint8), np.ones((15, 15), np.uint8))
    if stray.any():
        raw = cv2.inpaint(raw, stray, 12, cv2.INPAINT_NS)

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


def grade(im):
    """Brightness + saturation, baked in so the browser does none per frame."""
    g = C.GRADE
    a = im[:, :, 3:] if im.shape[2] == 4 else None
    hsv = cv2.cvtColor(im[:, :, :3], cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * g['saturation'], 0, 255)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * g['value'], 0, 255)
    b = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    b = np.clip((b - 128) * g['contrast'] + 128, 0, 255).astype(np.uint8)
    return np.dstack([b, a]) if a is not None else b


# -------------------------------------------------------------- 6. sheet ---
def stage_sheet():
    """Contact sheet on a checkerboard, so bad alpha is obvious."""
    items = []
    for sub in ('flowers', 'grass'):
        d = os.path.join(ASSETS, sub)
        for f in sorted(os.listdir(d)):
            if f.endswith('.png'):
                items.append((f[:-4], os.path.join(d, f)))
    if not items:
        return print('  nothing to show yet')
    CELL, COLS = 240, 6
    rows = (len(items) + COLS - 1) // COLS
    ck = np.indices((rows * CELL, COLS * CELL)).sum(0) // 16 % 2
    sheet = (ck * 40 + 60).astype(np.uint8)[:, :, None].repeat(3, 2)
    for i, (n, path) in enumerate(items):
        im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        s = min((CELL - 34) / im.shape[1], (CELL - 34) / im.shape[0])
        im = cv2.resize(im, (max(1, int(im.shape[1] * s)), max(1, int(im.shape[0] * s))), interpolation=cv2.INTER_AREA)
        a = im[:, :, 3:4].astype(np.float32) / 255
        r, c = divmod(i, COLS)
        y0 = r * CELL + 26 + (CELL - 34 - im.shape[0]) // 2
        x0 = c * CELL + 17 + (CELL - 34 - im.shape[1]) // 2
        reg = sheet[y0:y0 + im.shape[0], x0:x0 + im.shape[1]]
        sheet[y0:y0 + im.shape[0], x0:x0 + im.shape[1]] = (im[:, :, :3] * a + reg * (1 - a)).astype(np.uint8)
        cv2.putText(sheet, n, (c * CELL + 8, r * CELL + 18), cv2.FONT_HERSHEY_PLAIN, .85, (255, 255, 255), 1)
    cv2.imwrite(os.path.join(WORK, 'contact_sheet.png'), sheet)
    print(f'  work/contact_sheet.png  ({len(items)} assets)')


STAGES = {'grid': stage_grid, 'flatten': stage_flatten, 'flowers': stage_flowers,
          'foliage': stage_foliage, 'linen': stage_linen, 'sheet': stage_sheet}

if __name__ == '__main__':
    args = sys.argv[1:] or ['all']
    order = ['flatten', 'flowers', 'foliage', 'linen', 'sheet'] if args == ['all'] else args
    for a in order:
        if a not in STAGES:
            raise SystemExit(f'unknown stage: {a}\nstages: {", ".join(STAGES)}, all')
        print(f'[{a}]')
        STAGES[a]()
