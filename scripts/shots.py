"""Builds every catalog image: hero render (same camera for all), dimension sheet. Run: python3 shots.py [key ...]"""
import sys, os, io
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib
from render import load_stl, load_3mf
C=os.path.dirname(HERE); P=os.path.dirname(os.path.dirname(C))+'/3D Print' if False else None
P=os.path.abspath(os.path.join(C,'..'))
D=P+'/Product Displays'
BG=(0.88,0.89,0.88); BLACK=(0.16,0.16,0.17); WHITE=(0.97,0.97,0.97)
FONT=os.path.join(os.path.dirname(matplotlib.__file__),'mpl-data/fonts/ttf/DejaVuSans.ttf')
FONTB=os.path.join(os.path.dirname(matplotlib.__file__),'mpl-data/fonts/ttf/DejaVuSans-Bold.ttf')

def conv(t,up):
    if up=='x': t=np.stack([-t[...,1],t[...,0],t[...,2]],-1)
    if up=='z': t=np.stack([t[...,0],t[...,2],-t[...,1]],-1)
    return t

def raster(tris,up,azim,elev,tri_col=None,W=640,H=480,ss=2,fill=0.86):
    t=conv(tris.copy(),up); c=t.reshape(-1,3); ctr=(c.min(0)+c.max(0))/2; t=t-ctr
    ext=c.max(0)-c.min(0)
    a,e=np.radians(azim),np.radians(elev)
    Ry=np.array([[np.cos(a),0,np.sin(a)],[0,1,0],[-np.sin(a),0,np.cos(a)]])
    Rx=np.array([[1,0,0],[0,np.cos(e),-np.sin(e)],[0,np.sin(e),np.cos(e)]])
    t=t@(Rx@Ry).T
    n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]); n/=(np.linalg.norm(n,axis=1,keepdims=True)+1e-12)
    n[n[:,2]<0]*=-1
    L=np.array([-0.45,0.65,0.62]); L/=np.linalg.norm(L); sh=0.40+0.60*np.clip(n@L,0,1)
    w,h=W*ss,H*ss; xy=t[:,:,:2]; mn=xy.reshape(-1,2).min(0); mx=xy.reshape(-1,2).max(0)
    s=min(w*fill/(mx[0]-mn[0]+1e-9),h*fill/(mx[1]-mn[1]+1e-9))
    px=(xy[:,:,0]-(mn[0]+mx[0])/2)*s+w/2; py=h/2-(xy[:,:,1]-(mn[1]+mx[1])/2)*s; z=t[:,:,2]
    zb=np.full((h,w),-1e18); img=np.zeros((h,w,3)); img[:]=BG
    for i in range(len(t)):
        x0,x1=int(max(px[i].min(),0)),int(min(px[i].max()+1,w-1)); y0,y1=int(max(py[i].min(),0)),int(min(py[i].max()+1,h-1))
        if x1<=x0 or y1<=y0: continue
        (ax,ay),(bx,by),(cx,cy)=(px[i,0],py[i,0]),(px[i,1],py[i,1]),(px[i,2],py[i,2])
        d=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
        if abs(d)<1e-9: continue
        X,Y=np.meshgrid(np.arange(x0,x1+1)+0.5,np.arange(y0,y1+1)+0.5)
        l1=((by-cy)*(X-cx)+(cx-bx)*(Y-cy))/d; l2=((cy-ay)*(X-cx)+(ax-cx)*(Y-cy))/d; l3=1-l1-l2
        m=(l1>=-1e-6)&(l2>=-1e-6)&(l3>=-1e-6)
        if not m.any(): continue
        Z=l1*z[i,0]+l2*z[i,1]+l3*z[i,2]; sub=zb[y0:y1+1,x0:x1+1]; upd=m&(Z>sub); sub[upd]=Z[upd]
        img[y0:y1+1,x0:x1+1][upd]=(np.array(tri_col[i]) if tri_col is not None else np.array(BLACK))*sh[i]
    im=Image.fromarray((np.clip(img,0,1)*255).astype('uint8')).resize((W,H),Image.LANCZOS)
    box=(px.min()/ss,py.min()/ss,px.max()/ss,py.max()/ss)
    return im,box,ext

def inch(mm): return '%.2f in'%(mm/25.4)
def mmtxt(mm): return ('%.1f mm'%mm) if mm<100 else ('%d mm'%round(mm))
def dimtxt(mm): return '%s (%s)'%(inch(mm),mmtxt(mm))

def arrowline(d,p0,p1,col=(30,30,30)):
    d.line([p0,p1],fill=col,width=2)
    for p,q in ((p0,p1),(p1,p0)):
        dx,dy=q[0]-p[0],q[1]-p[1]; L=max((dx*dx+dy*dy)**.5,1); ux,uy=dx/L,dy/L
        d.polygon([p,(p[0]+ux*10-uy*4,p[1]+uy*10+ux*4),(p[0]+ux*10+uy*4,p[1]+uy*10-ux*4)],fill=col)

def dimsheet(tris,up,out,tri_col=None,title=''):
    kind='z' if up=='z' else 'y'
    panels=[]
    for label,azim in (('Front',0 if kind=='z' else 90),('Side',90 if kind=='z' else 0)):
        im,box,ext=raster(tris,up,azim,0,tri_col,W=640,H=500,ss=1,fill=0.66)
        hor=ext[0] if azim==0 else ext[2]; ver=ext[1]
        panels.append((label,im,box,hor,ver))
    sheet=Image.new('RGB',(1280,560),tuple(int(v*255) for v in BG)); d=ImageDraw.Draw(sheet)
    f=ImageFont.truetype(FONT,19); fb=ImageFont.truetype(FONTB,18)
    for k,(label,im,box,hor,ver) in enumerate(panels):
        ox=k*640; sheet.paste(im,(ox,30))
        x0,y0,x1,y1=box; y0+=30;y1+=30; x0+=ox;x1+=ox
        d.text((ox+22,12),label.upper()+' VIEW',font=fb,fill=(90,98,94))
        yb=y1+34; arrowline(d,(x0,yb),(x1,yb)); 
        for x in (x0,x1): d.line([(x,y1+4),(x,yb+8)],fill=(30,30,30),width=1)
        txt=dimtxt(hor); tw=d.textlength(txt,font=f); d.text(((x0+x1)/2-tw/2,yb+10),txt,font=f,fill=(20,20,20))
        xl=x0-34; arrowline(d,(xl,y0),(xl,y1))
        for y in (y0,y1): d.line([(x0-4,y),(xl-8,y)],fill=(30,30,30),width=1)
        txt=dimtxt(ver); tw=d.textlength(txt,font=f); tmp=Image.new('RGBA',(int(tw)+8,28),(0,0,0,0)); ImageDraw.Draw(tmp).text((4,2),txt,font=f,fill=(20,20,20))
        tmp=tmp.rotate(90,expand=True); sheet.paste(tmp,(int(xl-34),int((y0+y1)/2-tmp.size[1]/2)),tmp)
    sheet.save(out)

def load(path,up):
    return load_stl(path) if path.lower().endswith('.stl') else load_3mf(path)

JOBS={
 'vape-s':(D+'/Vape Display/GCVapeStand_S_High.3mf','y',None),
 'vape-m':(D+'/Vape Display/GCVapeStand_M_High.3mf','y',None),
 'vape-top':(D+'/Vape Display/GCVapeStand_M_Top-Shelf-Vape.3mf','y',None),
 'mylar-m':(D+'/Mylar Bag Stand/GCMylarBagStand_M.3mf','y',None),
 'mylar-l':(D+'/Mylar Bag Stand/GCMylarBagStand_L.3mf','y',None),
 'mylar-xl':(D+'/Mylar Bag Stand/GCMylarBagStand_XL.3mf','y',None),
 'bottle-30':(D+'/GCBottleStand_30mm.3mf','x',None),
 'preroll-3':(D+'/GCPreRollHolder_3x22mm.3mf','x',None),
 'giftcard':(D+'/Gift Card Stand/GiftCardStand_B_HeaderPlaque_Body.3mf','y',None),
 'lighter-25':(D+'/Lighter Display/Lighter Display 25.3mf','z','parts'),
 'lighter-29':(D+'/Lighter Display/Lighter Display 29.3mf','z','parts'),
 'batt-bar':(P+'/Battery Holders/Bar/ConcealBoxStand2.stl','z','letters'),
 'batt-digital':(P+'/Battery Holders/Digital/DigiBoxStand2.stl','z','letters'),
 'batt-vv':(P+'/Battery Holders/Variable Voltage/VVBoxStand10.stl','z','letters'),
}
def colors(path,mode):
    if mode=='parts':
        parts=load_3mf(path,parts=True); tris=np.concatenate(parts)
        cols=np.zeros((len(tris),3)); cols[:]=BLACK; cols[len(parts[0]):]=WHITE; return tris,cols
    tris=load(path,None)
    if mode=='letters':
        ymin=tris[...,1].min(); cy=tris[...,1].mean(1)
        cols=np.zeros((len(tris),3)); cols[:]=BLACK; cols[cy<ymin+0.9]=WHITE; return tris,cols
    return tris,None

if __name__=='__main__':
    keys=sys.argv[1:] or list(JOBS)
    os.makedirs(C+'/img',exist_ok=True)
    for k in keys:
        path,up,mode=JOBS[k]; tris,cols=colors(path,mode)
        im,box,ext=raster(tris,up,-35,30,cols); im.save(C+'/img/%s.png'%k)
        dimsheet(tris,up,C+'/img/%s-dim.png'%k,cols); print('ok',k,np.round(ext,1).tolist(),flush=True)
