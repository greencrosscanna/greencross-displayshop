# Z-buffer flat-shaded renderer (numpy only). usage: raster.py in out up=y|z azim= elev= w= h=
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
from render import load_stl, load_3mf

def raster(tris, up='y', azim=-35, elev=20, W=640, H=480, base=(0.20,0.20,0.21), ss=2, tri_col=None):
    t = tris.copy()
    if up == 'x': t = np.stack([-t[...,1], t[...,0], t[...,2]], -1)
    if up == 'z': t = np.stack([t[...,0], t[...,2], -t[...,1]], -1)
    c = t.reshape(-1,3); ctr = (c.min(0)+c.max(0))/2; t = t-ctr
    a, e = np.radians(azim), np.radians(elev)
    Ry = np.array([[np.cos(a),0,np.sin(a)],[0,1,0],[-np.sin(a),0,np.cos(a)]])
    Rx = np.array([[1,0,0],[0,np.cos(e),-np.sin(e)],[0,np.sin(e),np.cos(e)]])
    R = Rx @ Ry
    t = t @ R.T
    tc = tri_col if tri_col is not None else None
    n = np.cross(t[:,1]-t[:,0], t[:,2]-t[:,0]); n /= (np.linalg.norm(n,axis=1,keepdims=True)+1e-12)
    flip = n[:,2] < 0   # make normals face viewer (open meshes / inverted)
    n[flip] *= -1
    L = np.array([-0.45,0.65,0.62])  # key light; L /= np.linalg.norm(L)
    sh = 0.38 + 0.62*np.clip(n@L,0,1)
    w, h = W*ss, H*ss
    xy = t[:,:,:2]; mn = xy.reshape(-1,2).min(0); mx = xy.reshape(-1,2).max(0)
    s = min((w*0.86)/(mx[0]-mn[0]+1e-9), (h*0.86)/(mx[1]-mn[1]+1e-9))
    px = (xy[:,:,0]-(mn[0]+mx[0])/2)*s + w/2
    py = h/2 - (xy[:,:,1]-(mn[1]+mx[1])/2)*s
    z = t[:,:,2]
    zb = np.full((h,w), -1e18); img = np.zeros((h,w,3)); img[:] = (0.965,0.965,0.955)
    for i in range(len(t)):
        x0,x1 = int(max(px[i].min(),0)), int(min(px[i].max()+1,w-1))
        y0,y1 = int(max(py[i].min(),0)), int(min(py[i].max()+1,h-1))
        if x1<=x0 or y1<=y0: continue
        (ax,ay),(bx,by),(cx,cy) = (px[i,0],py[i,0]), (px[i,1],py[i,1]), (px[i,2],py[i,2])
        d = (by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
        if abs(d)<1e-9: continue
        X,Y = np.meshgrid(np.arange(x0,x1+1)+0.5, np.arange(y0,y1+1)+0.5)
        l1 = ((by-cy)*(X-cx)+(cx-bx)*(Y-cy))/d
        l2 = ((cy-ay)*(X-cx)+(ax-cx)*(Y-cy))/d
        l3 = 1-l1-l2
        m = (l1>=-1e-6)&(l2>=-1e-6)&(l3>=-1e-6)
        if not m.any(): continue
        Z = l1*z[i,0]+l2*z[i,1]+l3*z[i,2]
        sub = zb[y0:y1+1, x0:x1+1]
        upd = m & (Z>sub)
        sub[upd] = Z[upd]
        img[y0:y1+1, x0:x1+1][upd] = (np.array(tc[i]) if tc is not None else np.array(base))*sh[i]
    im = Image.fromarray((np.clip(img,0,1)*255).astype('uint8')).resize((W,H), Image.LANCZOS)
    return im

if __name__=='__main__':
    src,out = sys.argv[1], sys.argv[2]
    kw = dict(a.split('=') for a in sys.argv[3:])
    tris = load_stl(src) if src.lower().endswith('.stl') else load_3mf(src)
    im = raster(tris, up=kw.get('up','y'), azim=float(kw.get('azim',-35)), elev=float(kw.get('elev',20)))
    im.save(out); print('ok', os.path.basename(src), len(tris))

def lighter(src,out,**k):
    parts = load_3mf(src, parts=True)
    tris = np.concatenate(parts)
    cols = np.zeros((len(tris),3)); cols[:] = (0.20,0.20,0.21)
    i = len(parts[0]); cols[i:] = (0.97,0.97,0.97)
    raster(tris, tri_col=cols, **k).save(out); print('lighter',os.path.basename(src),[len(p) for p in parts])
