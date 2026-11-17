import sys, os, zipfile, struct, re, io
import numpy as np
import xml.etree.ElementTree as ET
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

def load_stl(path):
    data=open(path,'rb').read()
    if data[:5]==b'solid' and b'facet' in data[:400]:
        txt=data.decode('latin1'); v=re.findall(r'vertex\s+(\S+)\s+(\S+)\s+(\S+)',txt)
        a=np.array(v,dtype=float).reshape(-1,3,3); return a
    n=struct.unpack('<I',data[80:84])[0]
    dt=np.dtype([('n','<3f4'),('v','<9f4'),('a','<u2')])
    arr=np.frombuffer(data,dtype=dt,count=n,offset=84)
    return arr['v'].reshape(-1,3,3).astype(float)

def parse_tf(s):
    if not s: return np.eye(4)
    m=np.array([float(x) for x in s.split()]).reshape(4,3)
    T=np.eye(4); T[:3,:3]=m[:3].T; T[:3,3]=m[3]; return T

def load_3mf(path, parts=False):
    z=zipfile.ZipFile(path)
    models={n:ET.fromstring(z.read(n)) for n in z.namelist() if n.endswith('.model')}
    def ln(t): return t.split('}')[-1]
    objs={}
    for fn,root in models.items():
        for o in root.iter():
            if ln(o.tag)=='object':
                objs[(fn,o.get('id'))]=(fn,o)
    def mesh_tris(o):
        for m in o:
            if ln(m.tag)=='mesh':
                V=[];T=[]
                for c in m:
                    if ln(c.tag)=='vertices':
                        V=np.array([[float(v.get(k)) for k in 'xyz'] for v in c])
                    if ln(c.tag)=='triangles':
                        T=np.array([[int(t.get(k)) for k in ('v1','v2','v3')] for t in c])
                return V[T] if len(T) else None
        return None
    def resolve(fn,o,T,out):
        mt=mesh_tris(o)
        if mt is not None:
            h=np.concatenate([mt.reshape(-1,3),np.ones((mt.shape[0]*3,1))],1)@T.T
            out.append(h[:,:3].reshape(-1,3,3))
        for c in o:
            if ln(c.tag)=='components':
                for comp in c:
                    p=None
                    for k,v in comp.attrib.items():
                        if k.endswith('path'): p=v.lstrip('/')
                    f2=p if p else fn
                    key=(f2,comp.get('objectid'))
                    if key in objs:
                        resolve(f2,objs[key][1],T@parse_tf(comp.get('transform')),out)
    out=[]
    main='3D/3dmodel.model'
    root=models.get(main)
    items=[i for i in root.iter() if ln(i.tag)=='item'] if root is not None else []
    for it in items:
        key=(main,it.get('objectid'))
        if key in objs: resolve(main,objs[key][1],parse_tf(it.get('transform')),out)
    if not out:
        for key,(fn,o) in objs.items(): resolve(fn,o,np.eye(4),out)
    if parts: return out
    return np.concatenate(out) if out else None

def render(tris,outp,size=(640,480),elev=28,azim=-52,color=(0.12,0.55,0.32),bg=(0.965,0.965,0.955)):
    c=tris.reshape(-1,3); mn,mx=c.min(0),c.max(0); ctr=(mn+mx)/2; ext=(mx-mn).max()
    t=(tris-ctr)/ext
    n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]); n/=np.linalg.norm(n,axis=1,keepdims=True)+1e-12
    L=np.array([0.4,-0.5,0.8]); L/=np.linalg.norm(L)
    sh=np.clip(n@L,0,1)*0.7+0.3
    cols=np.array(color)[None,:]*sh[:,None]
    fig=plt.figure(figsize=(size[0]/100,size[1]/100),dpi=100,facecolor=bg)
    ax=fig.add_axes([0,0,1,1],projection='3d'); ax.set_facecolor(bg)
    pc=Poly3DCollection(t,facecolors=cols,edgecolors='none',linewidths=0); ax.add_collection3d(pc)
    h=0.5; ax.set_xlim(-h,h);ax.set_ylim(-h,h);ax.set_zlim(-h,h)
    ext3=(mx-mn)/ext; ax.set_box_aspect(tuple(np.maximum(ext3,0.05)))
    ax.set_xlim(-ext3[0]/2,ext3[0]/2);ax.set_ylim(-ext3[1]/2,ext3[1]/2);ax.set_zlim(-ext3[2]/2,ext3[2]/2)
    ax.view_init(elev=elev,azim=azim); ax.set_axis_off()
    fig.savefig(outp,dpi=100,facecolor=bg); plt.close(fig)

if __name__=='__main__':
    src,outp=sys.argv[1],sys.argv[2]
    kw={}
    for a in sys.argv[3:]:
        k,v=a.split('='); kw[k]=float(v) if k in('elev','azim') else v
    tris=load_stl(src) if src.lower().endswith('.stl') else load_3mf(src)
    if tris is None: print('NO MESH',src); sys.exit(1)
    c=tris.reshape(-1,3); print(os.path.basename(src),len(tris),'tris','extent mm',np.round(c.max(0)-c.min(0),1).tolist())
    render(tris,outp,**kw)
