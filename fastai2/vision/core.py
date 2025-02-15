#AUTOGENERATED! DO NOT EDIT! File to edit: dev/08_vision.core.ipynb (unless otherwise specified).

__all__ = ['Image', 'ToTensor', 'imagenet_stats', 'cifar_stats', 'mnist_stats', 'n_px', 'shape', 'aspect', 'load_image',
           'PILBase', 'PILImage', 'PILImageBW', 'PILMask', 'OpenMask', 'TensorPoint', 'TensorPointCreate',
           'get_annotations', 'TensorBBox', 'LabeledBBox', 'image2tensor', 'encodes', 'encodes', 'PointScaler',
           'BBoxLabeler', 'decodes', 'encodes', 'decodes']

#Cell
from ..test import *
from ..torch_basics import *
from ..data.all import *

from PIL import Image

#Cell
imagenet_stats = ([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
cifar_stats    = ([0.491, 0.482, 0.447], [0.247, 0.243, 0.261])
mnist_stats    = ([0.131], [0.308])

#Cell
if not hasattr(Image,'_patched'):
    _old_sz = Image.Image.size.fget
    @patch_property
    def size(x:Image.Image): return Tuple(_old_sz(x))
    Image._patched = True

#Cell
@patch_property
def n_px(x: Image.Image): return x.size[0] * x.size[1]

#Cell
@patch_property
def shape(x: Image.Image): return x.size[1],x.size[0]

#Cell
@patch_property
def aspect(x: Image.Image): return x.size[0]/x.size[1]

#Cell
@patch
def reshape(x: Image.Image, h, w, resample=0):
    "`resize` `x` to `(w,h)`"
    return x.resize((w,h), resample=resample)

#Cell
@patch
def resize_max(x: Image.Image, resample=0, max_px=None, max_h=None, max_w=None):
    "`resize` `x` to `max_px`, or `max_h`, or `max_w`"
    h,w = x.shape
    if max_px and x.n_px>max_px: h,w = Tuple(h,w).mul(math.sqrt(max_px/x.n_px))
    if max_h and h>max_h: h,w = (max_h    ,max_h*w/h)
    if max_w and w>max_w: h,w = (max_w*h/w,max_w    )
    return x.reshape(round(h), round(w), resample=resample)

#Cell
def load_image(fn, mode=None, **kwargs):
    "Open and load a `PIL.Image` and convert to `mode`"
    im = Image.open(fn, **kwargs)
    im.load()
    im = im._new(im.im)
    return im.convert(mode) if mode else im

#Cell
class PILBase(Image.Image, metaclass=BypassNewMeta):
    _bypass_type=Image.Image
    _show_args = {'cmap':'viridis'}
    _open_args = {'mode': 'RGB'}
    @classmethod
    def create(cls, fn, **kwargs)->None:
        "Open an `Image` from path `fn`"
        if isinstance(fn,Tensor): fn = fn.numpy()
        if isinstance(fn,ndarray): return cls(Image.fromarray(fn))
        return cls(load_image(fn, **merge(cls._open_args, kwargs)))

    def show(self, ctx=None, **kwargs):
        "Show image using `merge(self._show_args, kwargs)`"
        return show_image(self, ctx=ctx, **merge(self._show_args, kwargs))

#Cell
class PILImage(PILBase): pass

#Cell
class PILImageBW(PILImage): _show_args,_open_args = {'cmap':'Greys'},{'mode': 'L'}

#Cell
class PILMask(PILBase): _open_args,_show_args = {'mode':'L'},{'alpha':0.5, 'cmap':'tab20'}

#Cell
OpenMask = Transform(PILMask.create)
OpenMask.loss_func = CrossEntropyLossFlat(axis=1)
PILMask.create = OpenMask

#Cell
class TensorPoint(TensorBase):
    "Basic type for points in an image"
    _show_args = dict(s=10, marker='.', c='r')

    @classmethod
    def create(cls, t, sz=None)->None:
        "Convert an array or a list of points `t` to a `Tensor`"
        return cls(tensor(t).view(-1, 2).float(), sz=sz)

    def show(self, ctx=None, **kwargs):
        if 'figsize' in kwargs: del kwargs['figsize']
        x = self.view(-1,2)
        ctx.scatter(x[:, 0], x[:, 1], **{**self._show_args, **kwargs})
        return ctx

#Cell
TensorPointCreate = Transform(TensorPoint.create)
TensorPointCreate.loss_func = MSELossFlat()
TensorPoint.create = TensorPointCreate

#Cell
def get_annotations(fname, prefix=None):
    "Open a COCO style json in `fname` and returns the lists of filenames (with maybe `prefix`) and labelled bboxes."
    annot_dict = json.load(open(fname))
    id2images, id2bboxes, id2cats = {}, collections.defaultdict(list), collections.defaultdict(list)
    classes = {o['id']:o['name'] for o in annot_dict['categories']}
    for o in annot_dict['annotations']:
        bb = o['bbox']
        id2bboxes[o['image_id']].append([bb[0],bb[1], bb[0]+bb[2], bb[1]+bb[3]])
        id2cats[o['image_id']].append(classes[o['category_id']])
    id2images = {o['id']:ifnone(prefix, '') + o['file_name'] for o in annot_dict['images'] if o['id'] in id2bboxes}
    ids = list(id2images.keys())
    return [id2images[k] for k in ids], [(id2bboxes[k], id2cats[k]) for k in ids]

#Cell
from matplotlib import patches, patheffects

def _draw_outline(o, lw):
    o.set_path_effects([patheffects.Stroke(linewidth=lw, foreground='black'), patheffects.Normal()])

def _draw_rect(ax, b, color='white', text=None, text_size=14, hw=True, rev=False):
    lx,ly,w,h = b
    if rev: lx,ly,w,h = ly,lx,h,w
    if not hw: w,h = w-lx,h-ly
    patch = ax.add_patch(patches.Rectangle((lx,ly), w, h, fill=False, edgecolor=color, lw=2))
    _draw_outline(patch, 4)
    if text is not None:
        patch = ax.text(lx,ly, text, verticalalignment='top', color=color, fontsize=text_size, weight='bold')
        _draw_outline(patch,1)

#Cell
class TensorBBox(TensorPoint):
    "Basic type for a tensor of bounding boxes in an image"
    @classmethod
    def create(cls, x, sz=None)->None: return cls(tensor(x).view(-1, 4).float(), sz=sz)

    def show(self, ctx=None, **kwargs):
        x = self.view(-1,4)
        for b in x: _draw_rect(ctx, b, hw=False, **kwargs)
        return ctx

#Cell
class LabeledBBox(Tuple):
    "Basic type for a list of bounding boxes in an image"
    def show(self, ctx=None, **kwargs):
        for b,l in zip(self.bbox, self.lbl):
            if l != '#na#': ctx = retain_type(b, self.bbox).show(ctx=ctx, text=l)
        return ctx

    bbox,lbl = add_props(lambda i,self: self[i])

#Cell
def image2tensor(img):
    "Transform image to byte tensor in `c*h*w` dim order."
    res = tensor(img)
    if res.dim()==2: res = res.unsqueeze(-1)
    return res.permute(2,0,1)

#Cell
PILImage  ._tensor_cls = TensorImage
PILImageBW._tensor_cls = TensorImageBW
PILMask   ._tensor_cls = TensorMask

#Cell
@ToTensor
def encodes(self, o:PILBase): return o._tensor_cls(image2tensor(o))
@ToTensor
def encodes(self, o:PILMask): return o._tensor_cls(image2tensor(o)[0])

#Cell
def _scale_pnts(y, sz, do_scale=True, y_first=False):
    if y_first: y = y.flip(1)
    res = y * 2/tensor(sz).float() - 1 if do_scale else y
    return TensorPoint(res, sz=sz)

def _unscale_pnts(y, sz): return TensorPoint((y+1) * tensor(sz).float()/2, sz=sz)

#Cell
class PointScaler(Transform):
    "Scale a tensor representing points"
    order = 1
    def __init__(self, do_scale=True, y_first=False): self.do_scale,self.y_first = do_scale,y_first
    def _grab_sz(self, x):
        self.sz = [x.shape[-1], x.shape[-2]] if isinstance(x, Tensor) else x.size
        return x

    def _get_sz(self, x):
        sz = getattr(x, '_meta', {}).get('sz', None)
        assert sz is not None or self.sz is not None, "Size could not be inferred, pass it in the init of your TensorPoint with `sz=...`"
        return self.sz if sz is None else sz

    def setup(self, dl):
        its = dl.do_item(0)
        for t in its:
            if isinstance(t, TensorPoint): self.c = t.numel()

    def encodes(self, x:(PILBase,TensorImageBase)): return self._grab_sz(x)
    def decodes(self, x:(PILBase,TensorImageBase)): return self._grab_sz(x)

    def encodes(self, x:TensorPoint): return _scale_pnts(x, self._get_sz(x), self.do_scale, self.y_first)
    def decodes(self, x:TensorPoint): return _unscale_pnts(x, self._get_sz(x))

#Cell
class BBoxLabeler(Transform):
    def setup(self, dl): self.vocab = dl.vocab
    def before_call(self): self.bbox,self.lbls = None,None

    def decode (self, x, **kwargs):
        self.bbox,self.lbls = None,None
        return self._call('decodes', x, **kwargs)

    def decodes(self, x:TensorMultiCategory):
        self.lbls = [self.vocab[a] for a in x]
        return x if self.bbox is None else LabeledBBox(self.bbox, self.lbls)

    def decodes(self, x:TensorBBox):
        self.bbox = x
        return self.bbox if self.lbls is None else LabeledBBox(self.bbox, self.lbls)

#Cell
#LabeledBBox can be sent in a tl with MultiCategorize (depending on the order of the tls) but it is already decoded.
@MultiCategorize
def decodes(self, x:LabeledBBox): return x

#Cell
@PointScaler
def encodes(self, x:TensorBBox):
    pnts = self.encodes(TensorPoint(x.view(-1,2), sz=x._meta.get('sz', None)))
    return TensorBBox(pnts.view(-1, 4), sz=x._meta.get('sz', None))

@PointScaler
def decodes(self, x:TensorBBox):
    pnts = self.decodes(TensorPoint(x.view(-1,2), sz=x._meta.get('sz', None)))
    return TensorBBox(pnts.view(-1, 4), sz=x._meta.get('sz', None))