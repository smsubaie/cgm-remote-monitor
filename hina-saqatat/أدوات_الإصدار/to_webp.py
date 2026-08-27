# تحويل PNG إلى WebP بارتفاع صفحة موحد وخلفية الورق
import sys, os
from PIL import Image
OUT=sys.argv[1]
SIZES={'mobile':(720,1080),'tablet':(1080,1620),'desktop':(1440,2160)}
BG=(253,252,248)
n=0; total=0
for size,(W,H) in SIZES.items():
    root=os.path.join(OUT,size)
    if not os.path.isdir(root): continue
    for chap in sorted(os.listdir(root)):
        d=os.path.join(root,chap)
        for f in sorted(os.listdir(d)):
            if not f.endswith('.png'): continue
            img=Image.open(os.path.join(d,f)).convert('RGB')
            canvas=Image.new('RGB',(W,H),BG)
            canvas.paste(img,(0,0))
            out=os.path.join(d,f[:-4]+'.webp')
            canvas.save(out,'WEBP',quality=82,method=4)
            total+=os.path.getsize(out)
            os.remove(os.path.join(d,f)); n+=1
print(f'converted {n} pages, webp bytes total {total}')
