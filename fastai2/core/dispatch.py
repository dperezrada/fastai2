#AUTOGENERATED! DO NOT EDIT! File to edit: dev/01b_core.dispatch.ipynb (unless otherwise specified).

__all__ = ['type_hints', 'anno_ret', 'cmp_instance', 'TypeDispatch', 'DispatchReg', 'typedispatch']

#Cell
from .imports import *
from .foundation import *
from .utils import *
from ..test import *

#Cell
def type_hints(f):
    "Same as `typing.get_type_hints` but returns `{}` if not allowed type"
    return typing.get_type_hints(f) if isinstance(f, typing._allowed_types) else {}

#Cell
def anno_ret(func):
    "Get the return annotation of `func`"
    if not func: return None
    ann = type_hints(func)
    if not ann: return None
    return ann.get('return')

#Cell
cmp_instance = functools.cmp_to_key(lambda a,b: 0 if a==b else 1 if issubclass(a,b) else -1)

#Cell
def _p2_anno(f):
    "Get the 1st 2 annotations of `f`, defaulting to `object`"
    hints = type_hints(f)
    ann = [o for n,o in hints.items() if n!='return']
    while len(ann)<2: ann.append(object)
    return ann[:2]

#Cell
class _TypeDict:
    def __init__(self): self.d,self.cache = {},{}

    def _reset(self):
        self.d = {k:self.d[k] for k in sorted(self.d, key=cmp_instance, reverse=True)}
        self.cache = {}

    def add(self, t, f):
        "Add type `t` and function `f`"
        if not isinstance(t,tuple): t=(t,)
        for t_ in t: self.d[t_] = f
        self._reset()

    def all_matches(self, k):
        "Find first matching type that is a super-class of `k`"
        if k not in self.cache:
            types = [f for f in self.d if k==f or (isinstance(k,type) and issubclass(k,f))]
            self.cache[k] = [self.d[o] for o in types]
        return self.cache[k]

    def __getitem__(self, k):
        "Find first matching type that is a super-class of `k`"
        res = self.all_matches(k)
        return res[0] if len(res) else None

    def __repr__(self): return self.d.__repr__()
    def first(self): return first(self.d.values())

#Cell
class TypeDispatch:
    "Dictionary-like object; `__getitem__` matches keys of types using `issubclass`"
    def __init__(self, *funcs):
        self.funcs = _TypeDict()
        for o in funcs: self.add(o)
        self.inst = None

    def add(self, f):
        "Add type `t` and function `f`"
        a0,a1 = _p2_anno(f)
        t = self.funcs.d.get(a0)
        if t is None:
            t = _TypeDict()
            self.funcs.add(a0, t)
        t.add(a1, f)

    def first(self): return self.funcs.first().first()
    def returns(self, x): return anno_ret(self[type(x)])
    def returns_none(self, x):
        r = anno_ret(self[type(x)])
        return r if r == NoneType else None

    def _attname(self,k): return getattr(k,'__name__',str(k))
    def __repr__(self):
        r = [f'({self._attname(k)},{self._attname(l)}) -> {getattr(v, "__name__", v.__class__.__name__)}'
             for k in self.funcs.d for l,v in self.funcs[k].d.items()]
        return '\n'.join(r)

    def __call__(self, *args, **kwargs):
        ts = L(args).map(type)[:2]
        f = self[tuple(ts)]
        if not f: return args[0]
        if self.inst is not None: f = types.MethodType(f, self.inst)
        return f(*args, **kwargs)

    def __get__(self, inst, owner):
        self.inst = inst
        return self

    def __getitem__(self, k):
        "Find first matching type that is a super-class of `k`"
        k = L(k if isinstance(k, tuple) else (k,))
        while len(k)<2: k.append(object)
        r = self.funcs.all_matches(k[0])
        if len(r)==0: return None
        for t in r:
            o = t[k[1]]
            if o is not None: return o
        return None

#Cell
class DispatchReg:
    "A global registry for `TypeDispatch` objects keyed by function name"
    def __init__(self): self.d = defaultdict(TypeDispatch)
    def __call__(self, f):
        nm = f'{f.__qualname__}'
        self.d[nm].add(f)
        return self.d[nm]

typedispatch = DispatchReg()