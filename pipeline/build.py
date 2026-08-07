#!/usr/bin/env python3
"""
Pack the curated assets into assets/payload.json, then inline that into
a single self-contained dist/dayspells.html.

    python pipeline/build.py

Run this after pipeline/extract.py, and any time you change config.KEEP.
"""
import os, sys, json, base64, re
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import config as C

ASSETS = os.path.join(ROOT, 'assets')
SRC    = os.path.join(ROOT, 'src', 'index.html')
DIST   = os.path.join(ROOT, 'dist', 'dayspells.html')


def find(name):
    for sub in ('flowers', 'grass', 'ground'):
        p = os.path.join(ASSETS, sub, name + '.png')
        if os.path.exists(p):
            return p
    raise SystemExit(f'missing asset: {name}.png -- run pipeline/extract.py first')


def main():
    out, total = [], 0
    for name, role, mx, stem in C.KEEP:
        im = cv2.imread(find(name), cv2.IMREAD_UNCHANGED)
        s = mx / max(im.shape[:2])
        im = cv2.resize(im, (max(1, round(im.shape[1] * s)), max(1, round(im.shape[0] * s))),
                        interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode('.webp', im, [cv2.IMWRITE_WEBP_QUALITY, 86])
        total += len(buf)
        out.append({'n': name, 'role': role, 'w': im.shape[1], 'h': im.shape[0], 'stem': stem,
                    'd': 'data:image/webp;base64,' + base64.b64encode(buf.tobytes()).decode()})
        print(f'  {name:16s} {role:7s} {im.shape[1]:3d}x{im.shape[0]:3d} {len(buf)/1024:5.1f} KB')

    tile = cv2.imread(os.path.join(ASSETS, 'ground', f'linen-tile-{C.LINEN_TILE}.png'))
    ok, tb = cv2.imencode('.webp', tile, [cv2.IMWRITE_WEBP_QUALITY, 90])
    total += len(tb)
    print(f'  linen tile              {tile.shape[1]}x{tile.shape[0]} {len(tb)/1024:5.1f} KB')

    payload = {'assets': out, 'linen': 'data:image/webp;base64,' + base64.b64encode(tb.tobytes()).decode()}
    pj = os.path.join(ASSETS, 'payload.json')
    json.dump(payload, open(pj, 'w'))
    print(f'\n  assets/payload.json  {os.path.getsize(pj)/1e6:.2f} MB ({total/1024:.0f} KB of image data)')

    # --- inline into a single file -------------------------------------
    # A previous version of this used index-based string slicing and one
    # slice came out empty, which turned replace('') into "insert between
    # every character" and shredded the template. Hence the assertions.
    src = open(SRC).read()
    slot = '<script id="payload" type="application/json"></script>'
    assert src.count(slot) == 1, 'payload slot missing or duplicated in src/index.html'
    doc = src.replace(slot, '<script id="payload" type="application/json">'
                      + json.dumps(payload) + '</script>')
    blocks = re.findall(r'<script>\n(.*?)\n</script>', doc, re.S)
    assert len(blocks) == 1, f'expected 1 code block, found {len(blocks)}'
    os.makedirs(os.path.dirname(DIST), exist_ok=True)
    open(DIST, 'w').write(doc)
    print(f'  dist/dayspells.html  {os.path.getsize(DIST)/1e6:.2f} MB (self-contained)')

    # --- palette, measured off the graded assets ------------------------
    try:
        from sklearn.cluster import KMeans
        px = []
        for name, role, mx, stem in C.KEEP:
            im = cv2.imread(find(name), cv2.IMREAD_UNCHANGED)
            px.append(im[:, :, :3][im[:, :, 3] > 200])
        px = np.concatenate(px)
        px = px[np.random.choice(len(px), min(30000, len(px)), replace=False)]
        km = KMeans(9, n_init=6, random_state=1).fit(px)
        pal = {}
        for i, (c, k) in enumerate(sorted(zip(km.cluster_centers_, np.bincount(km.labels_)),
                                          key=lambda t: -t[1])):
            pal[f'wool-{i+1}'] = '#%02x%02x%02x' % (int(c[2]), int(c[1]), int(c[0]))
        lin = tile.reshape(-1, 3).mean(0)
        pal['linen'] = '#%02x%02x%02x' % (int(lin[2]), int(lin[1]), int(lin[0]))
        pal['flare'] = '#f4451f'
        json.dump(pal, open(os.path.join(ASSETS, 'palette.json'), 'w'), indent=2)
        print('  assets/palette.json')
    except ImportError:
        print('  (skipped palette.json -- pip install scikit-learn)')


if __name__ == '__main__':
    main()
