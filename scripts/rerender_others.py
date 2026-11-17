"""Re-render the non-angled items (lighters, battery holders, pre-roll, gift card) with the v2 renderer
(edge lines, two lights, shadow) so the whole catalog shares one look. Run: python3 rerender_others.py [key ...]"""
import sys, os, numpy as np
import stands_catalog as S
import shots
from shots import JOBS, colors, conv
from PIL import Image

AZ = {'preroll-3': 305, 'giftcard': 35, 'pricecard': 215}          # extruded 'y'/'x' models showed their back: turn 180 deg
JOBS['taco'] = (shots.P + '/TacoTray.stl', 'y', None)
JOBS['pricecard'] = (shots.P + '/_archive/GCCard2.stl', 'y', None)
KEYS = ['taco', 'pricecard', 'lighter-25', 'lighter-29', 'batt-bar', 'batt-digital', 'batt-vv', 'preroll-3', 'giftcard']

def patch_raster(cols):
    """raster2 with per-triangle albedo"""
    def r(tris, azim, elev, **kw):
        old = S.BLACK
        return S.raster2(tris, azim, elev, **kw)
    return r

if __name__ == '__main__':
    keys = sys.argv[1:] or KEYS
    for k in keys:
        path, up, mode = JOBS[k]; tris, cols = colors(path, mode)
        if k == 'pricecard':                              # one holder from the full-sheet 3MF, as printed (flat), made y-up
            import render
            pr = render.load_3mf(shots.P + '/GCCard_FullsheetPrint.3mf', parts=True)[0]
            t = np.asarray(pr[0] if isinstance(pr, tuple) else pr, float); t = t - t.reshape(-1, 3).mean(0)
            tris = np.empty_like(t); tris[..., 0] = t[..., 1]; tris[..., 1] = t[..., 2]; tris[..., 2] = t[..., 0]
        else:
            tris = conv(tris.copy(), up)                  # to y-up
        if k == 'giftcard':                               # printed on its back: stand it so the card slot opens upward
            t2 = tris.copy(); t2[..., 1] = tris[..., 2]; t2[..., 2] = -tris[..., 1]; tris = t2
        if k == 'taco':
            S.raster2.__globals__['ALB'] = (0.70, 0.08, 0.08)
        elif cols is not None:
            S.raster2.__globals__['ALB'] = cols
        else:
            S.raster2.__globals__['ALB'] = None
        az = AZ.get(k, 35); el = 28
        im, box, ext = S.raster2(tris, az, el); im.save(S.C + '/img/%s.png' % k)
        S.dimsheet2(tris, S.C + '/img/%s-dim.png' % k)
        S.raster2.__globals__['ALB'] = None
        print('ok', k, flush=True)
