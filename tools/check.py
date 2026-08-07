#!/usr/bin/env python3
"""
Headless checks against the running dev server.

    python tools/check.py            # screenshot + fps + density
    python tools/check.py --wake     # also render the cursor-wake heatmap

Needs: pip install playwright && playwright install chromium
Assumes `python tools/serve.py` is running on :8000.

Note: frame rates from a machine without GPU acceleration are not
representative. The page has a density governor that thins the field to
hold ~50-60fps, so if `density()` reports quality < 1, that is the
governor doing its job, not a bug.
"""
import sys, os
import numpy as np

URL = os.environ.get('DAYSPELLS_URL', 'http://localhost:8000/src/')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, 'work')
os.makedirs(WORK, exist_ok=True)

FPS_JS = """()=>new Promise(r=>{let n=0;const t0=performance.now();
  (function k(){n++;performance.now()-t0<1800?requestAnimationFrame(k):r(n/((performance.now()-t0)/1000))})()})"""


def main():
    from playwright.sync_api import sync_playwright
    wake = '--wake' in sys.argv
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w, h, dpr, label in [(1440, 900, 1, 'desktop'), (390, 844, 2, 'mobile')]:
            pg = b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=dpr)
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('console', lambda m: errs.append(m.type + ': ' + m.text) if m.type == 'error' else None)
            pg.goto(URL)
            pg.wait_for_timeout(7000)          # let the governor settle
            d = pg.evaluate('density()')
            fps = pg.evaluate(FPS_JS)
            print(f'{label:8s} q={d["quality"]:<5} drawn={d["drawn"]}/{d["sown"]}  {fps:.0f} fps'
                  f'  errors={errs or "none"}')
            pg.screenshot(path=os.path.join(WORK, f'check_{label}.png'))
            pg.close()

        if wake:
            import cv2
            pg = b.new_page(viewport={'width': 1280, 'height': 800})
            pg.goto(URL); pg.wait_for_timeout(4000)
            for i in range(30):
                pg.mouse.move(120 + i * 36, 400 + 30 * np.sin(i / 4))
                pg.wait_for_timeout(14)
            pg.screenshot(path=os.path.join(WORK, 'w0.png'))
            pg.wait_for_timeout(120)
            pg.screenshot(path=os.path.join(WORK, 'w1.png'))
            a = cv2.imread(os.path.join(WORK, 'w0.png')).astype(float)
            c = cv2.imread(os.path.join(WORK, 'w1.png')).astype(float)
            diff = np.abs(a - c).mean(2)
            col = diff.mean(0); col = col / max(col.max(), 1e-6)
            print('wake by x-decile (cursor ends right):',
                  ' '.join('%.2f' % v for v in col.reshape(10, -1).mean(1)))
            cv2.imwrite(os.path.join(WORK, 'wake.png'),
                        cv2.applyColorMap(np.clip(diff * 9, 0, 255).astype(np.uint8), cv2.COLORMAP_INFERNO))
            print('  work/wake.png')
            pg.close()

        # reduced motion must be completely still
        pg = b.new_page(viewport={'width': 1280, 'height': 800}, reduced_motion='reduce')
        pg.goto(URL); pg.wait_for_timeout(3000)
        pg.screenshot(path=os.path.join(WORK, 'r0.png'))
        pg.mouse.move(400, 300); pg.mouse.move(900, 500)
        pg.wait_for_timeout(700)
        pg.screenshot(path=os.path.join(WORK, 'r1.png'))
        import cv2
        delta = np.abs(cv2.imread(os.path.join(WORK, 'r0.png')).astype(float)
                       - cv2.imread(os.path.join(WORK, 'r1.png')).astype(float)).mean()
        print(f'reduced-motion delta {delta:.4f} (should be ~0)')
        b.close()


if __name__ == '__main__':
    main()
