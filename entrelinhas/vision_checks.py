"""Local OCR (legacy Tesseract) and measurements of rendered pixels.

No generative model, external API or document transmission. Raster estimates
are labeled, and confidence is never treated as proof of correct recognition.
"""
import csv
from io import StringIO
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import ctypes
import numpy as np
from PIL import ImageOps
import pypdfium2 as pdfium

ROOT=Path(__file__).resolve().parent
PDF_LOCK=threading.RLock()


def executable():
    for p in [ROOT/'.runtime/tools/tesseract/tesseract.exe',Path('C:/Program Files/Tesseract-OCR/tesseract.exe')]:
        if p.is_file():return str(p)
    return shutil.which('tesseract')


def ocr(image):
    exe=executable()
    if not exe:return [],'Reconhecimento local de texto indisponível neste computador.'
    image=ImageOps.exif_transpose(image).convert('RGB')
    scale=min(3,max(1,1800/max(image.size)))
    scaled=image.resize((round(image.width*scale),round(image.height*scale))) if scale!=1 else image
    if scaled.width*scaled.height>16_000_000:return [],'Imagem excede o limite de reconhecimento de texto.'
    data=ROOT/'.runtime/tools/tessdata'
    with tempfile.TemporaryDirectory(prefix='entrelinhas-ocr-') as tmp:
        # Recognition uses a contrast-enhanced grayscale copy. Measurements
        # below always use the unchanged original pixels, never this copy.
        prepared=ImageOps.autocontrast(scaled.convert('L'))
        if np.median(np.asarray(prepared))<128:prepared=ImageOps.invert(prepared)
        path=Path(tmp)/'image.png';prepared.save(path)
        args=[exe,str(path),'stdout','--oem','0','--psm','11','-l','por+eng','--tessdata-dir',str(data),'tsv']
        try:
            output=subprocess.run(args,capture_output=True,timeout=35,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if output.returncode:return [],'O reconhecimento local não concluiu esta imagem.'
            words=[]
            for row in csv.DictReader(StringIO(output.stdout.decode('utf-8',errors='replace')),delimiter='\t'):
                text=row.get('text','').strip()
                if not text or row.get('level')!='5':continue
                confidence=float(row['conf'])
                if confidence<30:continue
                words.append({'text':text,'confidence':round(confidence,1),'x':int(row['left'])/scale,'y':int(row['top'])/scale,
                              'w':int(row['width'])/scale,'h':int(row['height'])/scale,'line':(row['block_num'],row['par_num'],row['line_num'])})
            return words,''
        except subprocess.TimeoutExpired:return [],'O reconhecimento excedeu o tempo limite; tente uma imagem menor.'


def raster_colors(image,box):
    x,y,w,h=box
    patch=np.asarray(image.convert('RGB').crop((max(0,int(x)-2),max(0,int(y)-2),min(image.width,int(x+w)+3),min(image.height,int(y+h)+3))))
    if patch.size<30:return None
    pixels=patch.reshape(-1,3).astype(float)
    # Two-color separation; reject photographs and gradients rather than infer
    # a precise foreground/background from arbitrary multicolored content.
    luminance=pixels@np.array([.2126,.7152,.0722])
    low=np.percentile(luminance,5);high=np.percentile(luminance,95)
    if high-low<8:return None
    a=pixels[luminance<=(low+(high-low)*.18)];b=pixels[luminance>=(high-(high-low)*.18)]
    if len(a)<3 or len(b)<3:return None
    ca=np.median(a,axis=0);cb=np.median(b,axis=0)
    if np.max(np.std(a,axis=0))>18 or np.max(np.std(b,axis=0))>18:return None
    border=np.concatenate([patch[0],patch[-1],patch[:,0],patch[:,-1]]).astype(float)
    background=np.median(border,axis=0)
    if np.linalg.norm(background-ca)<np.linalg.norm(background-cb):fg,bg=cb,ca
    else:fg,bg=ca,cb
    def hexcolor(c):return '#'+''.join(f'{round(v):02X}' for v in c)
    return hexcolor(fg),hexcolor(bg)


def ocr_blocks(image,prefix,width=None,height=None):
    words,error=ocr(image);blocks=[]
    sx=(width or image.width)/image.width;sy=(height or image.height)/image.height
    for index,w in enumerate(words):
        colors=raster_colors(image,(w['x'],w['y'],w['w'],w['h']))
        blocks.append({'id':f'{prefix}-ocr{index}','type':'text','text':w['text'],'x':w['x']*sx,'y':w['y']*sy,'w':w['w']*sx,'h':w['h']*sy,
                       'background':colors[1] if colors else None,'ocr':True,'confidence':w['confidence'],
                       'runs':[{'text':w['text'],'size':None,'bold':False,'color':colors[0] if colors else None,'estimated':True}]})
    return blocks,error


class PdfPixels:
    """Independent in-memory original and text-free rendering; source untouched."""
    def __init__(self,path,index):
        self.doc=pdfium.PdfDocument(str(path));self.page=self.doc[index]
        self.width,self.height=self.page.get_size();self.scale=min(3,2400/max(self.width,self.height))
        self.foreground=[]
        for obj in list(self.page.get_objects(filter=[pdfium.raw.FPDF_PAGEOBJ_TEXT])):
            r,g,b,a=(ctypes.c_uint() for _ in range(4))
            if pdfium.raw.FPDFPageObj_GetFillColor(obj,r,g,b,a):
                self.foreground.append((obj.get_bounds(),(r.value,g.value,b.value,a.value)))
        self.original=self.render()
        for obj in list(self.page.get_objects(filter=[pdfium.raw.FPDF_PAGEOBJ_TEXT])):
            self.page.remove_obj(obj);obj.close()
        self.page.gen_content()
        self.background=self.render()
    def render(self):
        bitmap=self.page.render(scale=self.scale,draw_annots=False);image=bitmap.to_pil().convert('RGB').copy();bitmap.close();return image
    def measure(self,box,color,contrast):
        x0,top,x1,bottom=box
        coords=(max(0,int(x0*self.scale)),max(0,int(top*self.scale)),min(self.background.width,int(x1*self.scale)+1),min(self.background.height,int(bottom*self.scale)+1))
        bg=np.asarray(self.background.crop(coords))
        if not bg.size:return None
        rgba=None
        for (left,down,right,up),candidate in self.foreground:
            if left<=x0+2 and right>=x1-2 and self.height-up<bottom and self.height-down>top:rgba=candidate;break
        if not color and rgba:color='#'+''.join(f'{v:02X}' for v in rgba[:3])
        if not color:return None
        original=np.asarray(self.original.crop(coords))
        change=np.max(np.abs(original.astype(float)-bg.astype(float)),axis=2)
        # Borders and underlines inside the word box are not its background.
        # Compare only pixels changed by removal of text when visible glyphs
        # exist. Otherwise keep the fallback so invisible text is still caught.
        mask=change>=max(3,float(change.max())*.65)
        samples=bg[mask] if mask.any() else bg.reshape(-1,3)
        values=np.unique((samples//4)*4,axis=0)
        if len(values)>250:values=values[::max(1,len(values)//250)]
        alpha=rgba[3]/255 if rgba else 1
        fg=np.array([int(color[i:i+2],16) for i in (1,3,5)])
        pairs=[]
        for rgb in values:
            bghex='#'+''.join(f'{int(v):02X}' for v in rgb)
            effective=fg*alpha+rgb*(1-alpha)
            fghex='#'+''.join(f'{round(v):02X}' for v in effective)
            pairs.append((contrast(fghex,bghex),fghex,bghex))
        return min(pairs) if pairs else None
    def close(self):self.page.close();self.doc.close()
