import json,base64,os,io
from PIL import Image
C=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d=json.load(open(C+'/catalog.json')); d['plates']=json.load(open(C+'/plates.json'))
keys=set()
for p in d['products']:
    for v in p['variants']:
        for k in ('img','dim'):
            if v.get(k): keys.add(v[k])
        keys.update(v.get('extra',[]))
img={}
for k in sorted(keys):
    f=None
    for ext in ('.png','.jpg'):
        if os.path.exists(C+'/img/'+k+ext): f=C+'/img/'+k+ext
    if not f: print('MISSING',k); continue
    im=Image.open(f).convert('RGB'); im.thumbnail((1280 if k.endswith('-dim') else 760,760))
    b=io.BytesIO(); im.save(b,'JPEG',quality=82,optimize=True); img[k]='data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()
font=open(C+'/gotham-black.b64').read().strip()
t=open(C+'/template.html').read().replace('__DATA__',json.dumps(d)).replace('__IMG__',json.dumps(img)).replace('__FONT__',font)
# index.html IS the app (GitHub Pages serves it). Always rebuild after editing template/catalog/plates.
open(C+'/index.html','w').write(t); print('built index.html',len(t)//1024,'KB',len(img),'images')
