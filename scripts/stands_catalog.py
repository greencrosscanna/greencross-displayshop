"""Catalog models + renders for the angled stands (Simple, Bag, Bottle, Jar) at 30 / 45 / 75 degrees.
Simple + Bag use the shared GCStands_build.py profile (same geometry as the real stands, minus the 0.5 mm fillet).
Bottle + Jar are new parametric builds (proposals until printed).
Run: python3 -I stands_catalog.py [key ...]   keys like simple-45, bag-75, bottle-4oz-30, jar-M-75
World frame of every mesh: x = width, y = up, z = toward the viewer (product face looks +z). Units mm.
"""
import sys, os, math, json, importlib.util
import numpy as np, trimesh
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import matplotlib

HERE = os.path.dirname(os.path.abspath(__file__)); C = os.path.dirname(HERE)
P = os.path.abspath(os.path.join(C, '..')); DISP = P + '/Product Displays'
spec = importlib.util.spec_from_file_location('gs', DISP + '/scripts/GCStands_build.py')
gs = importlib.util.module_from_spec(spec); spec.loader.exec_module(gs)

ANGLES = (30, 45, 75)
MIN_TILT = 15.0
BOTTLES = {'1oz': 30.0, '4oz': 50.8, '8oz': 63.5}            # diameters, mm
JARS = {'XS': 40.25, 'S': 50.0, 'M': 60.0, 'L': 70.0}

def to_world(m):                       # extrude frame (X=w, Y=h, Z=width) -> world
    v = m.vertices.copy(); W = (v[:, 2].max() + v[:, 2].min()) / 2
    nv = np.stack([v[:, 2] - W, v[:, 1], -v[:, 0]], 1)
    out = trimesh.Trimesh(nv, m.faces[:, ::-1], process=True); out.merge_vertices(digits_vertex=4); out.update_faces(out.nondegenerate_faces()); out.remove_unreferenced_vertices(); out.fix_normals()
    b = out.bounds; out.apply_translation([-(b[0][0] + b[1][0]) / 2, -b[0][1], -(b[0][2] + b[1][2]) / 2]); return out

def stand_profile_mesh(p):
    poly, g = gs.profile(p)
    m = trimesh.creation.extrude_polygon(poly, p['StandWidth'])
    return m, poly, g

def fit_base(p, step=5.0, limit=160.0):
    """grow BaseDepth (with FrontFill 14) until the stand+product tips no sooner than MIN_TILT"""
    for bd in [p['BaseDepth']] + list(np.arange(max(p['BaseDepth'], 20.0), limit, step)):
        q = dict(p); q['BaseDepth'] = float(bd)
        if bd > 0 and q['FrontFill'] == 0: q['FrontFill'] = 14.0
        poly, g = gs.profile(q); t = gs.tilt(poly, g, q)
        if min(t['back'], t['forward']) >= MIN_TILT: return q, t
    return q, t

def build_simple(a):
    p = gs.params_for('vape', 'M', angle=a)
    p, t = fit_base(p) if gs.tilt(*gs.profile(p), p) and min(gs.tilt(*gs.profile(p), p)['back'], gs.tilt(*gs.profile(p), p)['forward']) < MIN_TILT else (p, gs.tilt(*gs.profile(p), p))
    m, poly, g = stand_profile_mesh(p)
    return to_world(m), dict(p=p, tilt=t, face=a)

def build_bag(a):
    p = gs.params_for('mylar', 'M', angle=a)
    p, t = fit_base(p) if min(gs.tilt(*gs.profile(p), p)['back'], gs.tilt(*gs.profile(p), p)['forward']) < MIN_TILT else (p, gs.tilt(*gs.profile(p), p))
    m, poly, g = stand_profile_mesh(p)
    return to_world(m), dict(p=p, tilt=t, face=a)

def build_bottle(size, a):
    D = BOTTLES[size]; r = D / 2 + 1.0; w = max(0.65 * D, 15.0)
    e = math.sqrt(r * r - (w / 2 - 1.2) ** 2); d = r - e
    grams = dict(zip(BOTTLES, (60, 150, 300)))[size]
    p = gs.params_for('vape', 'M', angle=a)
    p.update(BackHeight=round(2.0 * D), StandWidth=round(w, 1), PlateThk=3.34 + d, LipDepth=round(0.55 * D, 1), ProductG=grams, ProductLen=round(2.0 * D / 25.4 + 0.5, 2),
             LedgeThk=2.0, FrontFill=0.0, BaseDepth=0.0, EdgeFillet=0)
    if a > 30 or min(gs.tilt(*gs.profile(p), p)['back'], gs.tilt(*gs.profile(p), p)['forward']) < MIN_TILT:
        p['FrontFill'] = 14.0; p['BaseDepth'] = 25.0; p, t = fit_base(p)
    else:
        t = gs.tilt(*gs.profile(p), p)
    m, poly, g = stand_profile_mesh(p)
    # cradle: cylinder along the plate, axis e in front of the face
    B, v, u = g['B'], g['v'], g['u']
    L = p['BackHeight'] + 20
    cyl = trimesh.creation.cylinder(radius=r, height=L, sections=96)       # axis z
    R = trimesh.geometry.align_vectors([0, 0, 1], [v[0], v[1], 0])
    T = np.eye(4); T[:3, :3] = R[:3, :3]
    cen2 = B + e * u + (L / 2 - 6.0) * v                                    # starts 6 mm below the ledge top so the cut opens above it
    cen2 = B + e * u + (L / 2) * v
    T[:3, 3] = [cen2[0], cen2[1], p['StandWidth'] / 2]
    cyl.apply_transform(T)
    m = m.difference(cyl, engine='manifold')
    return to_world(m), dict(p=p, tilt=t, face=a, D=D, r=r, w=w, groove=d)

def build_jar(size, a):
    """Real geometry: exported from Sky's Fusion file JarHolder3 (parameters JarDia, Tilt) into models_fusion/jar-<size>-<angle>.stl.
    Fusion frame: x width, y depth (front = low y), z up. -> world (x, z, -y)."""
    m0 = trimesh.load(C + '/models_fusion/jar-%s-%d.stl' % (size, a))
    v = m0.vertices
    out = trimesh.Trimesh(np.stack([v[:, 0], v[:, 2], -v[:, 1]], 1), m0.faces, process=False)
    b = out.bounds; out.apply_translation([-(b[0][0] + b[1][0]) / 2, -b[0][1], -(b[0][2] + b[1][2]) / 2])
    return out, dict(p=dict(Dia=JARS[size], Wall=1.75), tilt=None, face=a)

def all_keys():
    k = []
    for a in ANGLES: k.append(f'simple-{a}')
    for a in ANGLES: k.append(f'bag-{a}')
    for s in BOTTLES:
        for a in ANGLES: k.append(f'bottle-{s}-{a}')
    for s in JARS:
        for a in (15, 30): k.append(f'jar-{s}-{a}')
    return k


# ---- pre-roll tube holder: n channels (1..10) x face angle. Tube 22 mm is a placeholder (from GCPreRollHolder_3x22mm).
PR_D, PR_PITCH, PR_END, PR_L, PR_LIP, PR_LIPT, PR_HF = 22.0, 26.5, 3.0, 100.0, 8.0, 3.0, 6.0
def build_preroll(n, a):
    """Real geometry: exported from Sky's Fusion file GCPreRollHolder (parameters TubeCount, Angle=90-face) into models_fusion/. Fusion frame x width, y depth, z up."""
    m0 = trimesh.load(C + '/models_fusion/preroll-%d-%d.stl' % (n, a))
    v = m0.vertices
    sgn = PR_SIGN
    out = trimesh.Trimesh(np.stack([v[:, 0], v[:, 2], sgn * v[:, 1]], 1), m0.faces if sgn < 0 else m0.faces[:, ::-1], process=False)
    b = out.bounds; out.apply_translation([-(b[0][0] + b[1][0]) / 2, -b[0][1], -(b[0][2] + b[1][2]) / 2])
    return out, dict(p=dict(n=n, tube=18.0, pitch=22.0), tilt=None, face=a)
PR_SIGN = -1

def build_key(k):
    parts = k.split('-')
    if parts[0] == 'preroll': return build_preroll(int(parts[1]), int(parts[2]))
    if parts[0] == 'simple': return build_simple(int(parts[1]))
    if parts[0] == 'bag': return build_bag(int(parts[1]))
    if parts[0] == 'bottle': return build_bottle(parts[1], int(parts[2]))
    return build_jar(parts[1], int(parts[2]))

# ------------------------------------------------------------------ renderer (v2: edge lines, two lights, ground shadow)
BG = (0.88, 0.89, 0.88); BLACK = np.array([0.34, 0.34, 0.35])
FONT = os.path.join(os.path.dirname(matplotlib.__file__), 'mpl-data/fonts/ttf/DejaVuSans.ttf')
FONTB = os.path.join(os.path.dirname(matplotlib.__file__), 'mpl-data/fonts/ttf/DejaVuSans-Bold.ttf')
ALB = None
KEY = np.array([-0.45, 0.65, 0.62]); KEY /= np.linalg.norm(KEY)
FILL = np.array([0.75, 0.15, 0.35]); FILL /= np.linalg.norm(FILL)

def raster2(tris, azim, elev, W=640, H=480, ss=2, fill=0.80, edges=True, shadow=True):
    t = tris.copy(); c = t.reshape(-1, 3); ctr = (c.min(0) + c.max(0)) / 2; t = t - ctr; ext = c.max(0) - c.min(0)
    a, e = np.radians(azim), np.radians(elev)
    Ry = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
    Rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    t = t @ (Rx @ Ry).T
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]); n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12); n[n[:, 2] < 0] *= -1
    sh = 0.20 + 0.62 * np.clip(n @ KEY, 0, 1) + 0.20 * np.clip(n @ FILL, 0, 1)
    w, h = W * ss, H * ss; xy = t[:, :, :2]; mn = xy.reshape(-1, 2).min(0); mx = xy.reshape(-1, 2).max(0)
    s = min(w * fill / (mx[0] - mn[0] + 1e-9), h * fill / (mx[1] - mn[1] + 1e-9))
    px = (xy[:, :, 0] - (mn[0] + mx[0]) / 2) * s + w / 2; py = h / 2 - (xy[:, :, 1] - (mn[1] + mx[1]) / 2) * s; z = t[:, :, 2]
    zb = np.full((h, w), -1e18); img = np.zeros((h, w, 3)); nb = np.zeros((h, w, 3))
    for i in range(len(t)):
        x0, x1 = int(max(px[i].min(), 0)), int(min(px[i].max() + 1, w - 1)); y0, y1 = int(max(py[i].min(), 0)), int(min(py[i].max() + 1, h - 1))
        if x1 <= x0 or y1 <= y0: continue
        (ax, ay), (bx, by), (cx, cy) = (px[i, 0], py[i, 0]), (px[i, 1], py[i, 1]), (px[i, 2], py[i, 2])
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-9: continue
        X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / d; l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / d; l3 = 1 - l1 - l2
        m = (l1 >= -4e-3) & (l2 >= -4e-3) & (l3 >= -4e-3)
        if not m.any(): continue
        Z = l1 * z[i, 0] + l2 * z[i, 1] + l3 * z[i, 2]; sub = zb[y0:y1 + 1, x0:x1 + 1]; upd = m & (Z > sub); sub[upd] = Z[upd]
        img[y0:y1 + 1, x0:x1 + 1][upd] = (np.array(ALB) if isinstance(ALB, tuple) else (BLACK if (ALB is None or ALB[i][0] < 0.5) else np.array([0.97, 0.97, 0.97]))) * sh[i]; nb[y0:y1 + 1, x0:x1 + 1][upd] = n[i]
    mask = zb > -1e17
    if edges:                                           # light crease lines where the surface turns > ~25 deg
        crease = np.zeros_like(mask)
        for dy, dx in ((0, 1), (1, 0), (1, 1)):
            a1 = nb[:h - dy, :w - dx]; a2 = nb[dy:, dx:]; mm = mask[:h - dy, :w - dx] & mask[dy:, dx:]
            dot = (a1 * a2).sum(-1); crease[:h - dy, :w - dx] |= mm & (dot < 0.90)
        zj = np.zeros_like(mask); dz = np.abs(zb[:, 1:] - zb[:, :-1]); zj[:, :-1] |= mask[:, 1:] & mask[:, :-1] & (dz > 1.2 * (mx - mn).max() / 100)
        dz2 = np.abs(zb[1:, :] - zb[:-1, :]); zj[:-1, :] |= mask[1:, :] & mask[:-1, :] & (dz2 > 1.2 * (mx - mn).max() / 100)
        line = crease | zj
        from scipy.ndimage import binary_dilation
        line = binary_dilation(line, iterations=1) & mask
        img[line] = np.clip(img[line] + 0.20, 0, 1)
    bg = np.zeros((h, w, 3)); bg[:] = BG
    if shadow:
        sy = int(py.max() - 3 * ss); sx = int((px.min() + px.max()) / 2); rx = int((px.max() - px.min()) * 0.50 + 8 * ss); ry = int(7 * ss + (px.max() - px.min()) * 0.03)
        sm = Image.new('L', (w, h), 0); ImageDraw.Draw(sm).ellipse([sx - rx, sy - ry, sx + rx, sy + ry], fill=120)
        sm = np.asarray(sm.filter(ImageFilter.GaussianBlur(8 * ss)), dtype=float) / 255
        bg = bg * (1 - 0.45 * sm[..., None])
    out = np.where(mask[..., None], img, bg)
    im = Image.fromarray((np.clip(out, 0, 1) * 255).astype('uint8')).resize((W, H), Image.LANCZOS)
    return im, (px.min() / ss, py.min() / ss, px.max() / ss, py.max() / ss), ext

def inch(mm): return '%.2f in' % (mm / 25.4)
def mmtxt(mm): return ('%.1f mm' % mm) if mm < 100 else ('%d mm' % round(mm))
def dimtxt(mm): return '%s (%s)' % (inch(mm), mmtxt(mm))

def arrowline(d, p0, p1, col=(30, 30, 30)):
    d.line([p0, p1], fill=col, width=2)
    for p, q in ((p0, p1), (p1, p0)):
        dx, dy = q[0] - p[0], q[1] - p[1]; L = max((dx * dx + dy * dy) ** .5, 1); ux, uy = dx / L, dy / L
        d.polygon([p, (p[0] + ux * 10 - uy * 4, p[1] + uy * 10 + ux * 4), (p[0] + ux * 10 + uy * 4, p[1] + uy * 10 - ux * 4)], fill=col)

def dimsheet2(tris, out, face_deg=None, title=''):
    panels = []
    for label, azim, elev in (('Front', 0, 0), ('Side', 90, 0)):
        im, box, ext = raster2(tris, azim, elev, W=640, H=500, ss=1, fill=0.66, shadow=False)
        hor = ext[0] if azim == 0 else ext[2]; ver = ext[1]; panels.append((label, im, box, hor, ver))
    sheet = Image.new('RGB', (1280, 560), tuple(int(v * 255) for v in BG)); d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(FONT, 19); fb = ImageFont.truetype(FONTB, 18)
    for k, (label, im, box, hor, ver) in enumerate(panels):
        ox = k * 640; sheet.paste(im, (ox, 30)); x0, y0, x1, y1 = box; y0 += 30; y1 += 30; x0 += ox; x1 += ox
        head = label.upper() + ' VIEW' + ('   (product face %d deg to the table)' % face_deg if (face_deg and label == 'Side') else '')
        d.text((ox + 22, 12), head, font=fb, fill=(90, 98, 94))
        yb = y1 + 34; arrowline(d, (x0, yb), (x1, yb))
        for x in (x0, x1): d.line([(x, y1 + 4), (x, yb + 8)], fill=(30, 30, 30), width=1)
        txt = dimtxt(hor); tw = d.textlength(txt, font=f); d.text(((x0 + x1) / 2 - tw / 2, yb + 10), txt, font=f, fill=(20, 20, 20))
        xl = x0 - 34; arrowline(d, (xl, y0), (xl, y1))
        for y in (y0, y1): d.line([(x0 - 4, y), (xl - 8, y)], fill=(30, 30, 30), width=1)
        txt = dimtxt(ver); tw = d.textlength(txt, font=f); tmp = Image.new('RGBA', (int(tw) + 8, 28), (0, 0, 0, 0)); ImageDraw.Draw(tmp).text((4, 2), txt, font=f, fill=(20, 20, 20))
        tmp = tmp.rotate(90, expand=True); sheet.paste(tmp, (int(xl - 34), int((y0 + y1) / 2 - tmp.size[1] / 2)), tmp)
    sheet.save(out)

AZ = float(os.environ.get('HERO_AZ', 35))
if __name__ == '__main__':
    keys = sys.argv[1:] or all_keys()
    os.makedirs(C + '/img', exist_ok=True); os.makedirs(C + '/models', exist_ok=True)
    meta = {}
    for k in keys:
        mesh, info = build_key(k)
        assert mesh.is_watertight, k + ' not watertight'
        mesh.export(C + '/models/%s.stl' % k)
        tris = mesh.triangles
        im, box, ext = raster2(tris, AZ, 28); im.save(C + '/img/%s.png' % k)
        dimsheet2(tris, C + '/img/%s-dim.png' % k, face_deg=info.get('face'))
        meta[k] = dict(ext=[round(float(x), 2) for x in ext], tilt=info.get('tilt'), p={a: (round(b, 2) if isinstance(b, float) else b) for a, b in info['p'].items() if isinstance(b, (int, float))},
                       **{x: round(float(info[x]), 2) for x in ('D', 'r', 'w', 'groove') if x in info})
        json.dump({k: meta[k]}, open(C + '/models/meta_%s.json' % k, 'w'), indent=1)
        print('ok', k, meta[k]['ext'], info.get('tilt'), flush=True)
