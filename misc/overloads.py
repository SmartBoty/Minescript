from weakref import WeakKeyDictionary
from typing import TYPE_CHECKING, get_type_hints
import inspect
import sys

class OverloadException(Exception): pass
class ParamMissmatch(OverloadException): pass
_overloaded = WeakKeyDictionary()
_sig_matchers = {
    0: isinstance,
    1: lambda a,b: (type(a) == b) or b == object,
    2: lambda a,b: type(a) == b
}

def _convert_argtypes(args, kwargs):
    out = [type(arg).__name__ for arg in args]
    out += [f"{k}={type(v).__name__}" for k,v in kwargs.items()]
    return ", ".join(out)
def _matches_signature(func, args, kwargs, strictness):
    type_hints = get_type_hints(func)
    sig = inspect.signature(func)
    try:
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
    except TypeError: return False
    for name, value in bound.arguments.items():
        param = sig.parameters[name]
        annotation = type_hints.get(name, object)
        matcher = _sig_matchers[strictness]
        if param.kind is inspect.Parameter.VAR_POSITIONAL:
            if not all(matcher(arg, annotation) for arg in value): return False
        elif param.kind is inspect.Parameter.VAR_KEYWORD:
            if not all(matcher(arg, annotation) for arg in value.values()): return False
        else:
            if not matcher(value, annotation): return False
    return True

temp = []

class overload:
    def __new__(cls, func=None, /, **kwargs):
        obj = super().__new__(cls)
        if func is None:
            return lambda func: (obj.__init__(func,**kwargs),obj)[-1]
        return obj

    def __init__(self, func=None, *, strictness=0):
        self.func = func
        self.id = func.__module__ + func.__qualname__
        self.strictness = strictness
        self.module = sys.modules[func.__module__]
        self.clss = self.module
        self.name = func.__name__
        self.instance = []
        self.isstatic = isinstance(func,staticmethod)
        if self.module not in _overloaded:
            _overloaded[self.module] = {}
        if self.id not in _overloaded[self.module]:
            _overloaded[self.module][self.id] = []
        _overloaded[self.module][self.id].append(self)

    def __get__(self, instance, owner):
        for overload in _overloaded[self.clss][self.id]:
            if instance is not None and not overload.isstatic:
                overload.instance = [instance]
            else: overload.instance = []
        return self

    def __set_name__(self, owner, name):
        if owner not in _overloaded:
            _overloaded[owner] = {}
        if self.id not in _overloaded[owner]:
            _overloaded[owner][self.id] = []
        for overload in _overloaded[self.module].pop(self.id):
            _overloaded[owner][self.id].append(overload)
            overload.clss = owner
        if len(_overloaded[self.module]) < 1: _overloaded.pop(self.module)

    def __call__(self, *args, **kwargs):
        args = list(args)
        overloads = _overloaded[self.clss][self.id]
        for overload in overloads:
            a = (overload.instance + args) if not overload.isstatic else args
            if _matches_signature(overload.func, a, kwargs, overload.strictness):
                return overload.func(*a, **kwargs)
        raise ParamMissmatch(f"{self.clss.__name__}.{self.name}({_convert_argtypes(a, kwargs)})")

if TYPE_CHECKING:
    class overload:
        """
        Create an overload over a method / function, based on type annotations

        Overloads are resolved in decleration order

        Strictness values:
        - `0` (default): all args are matched with `isinstance`
        - `1`: all args-s types are matched directly, with `object` being a wildcard
        - `2`: all args-s types are matched directly, no wildcard. Not indented to be used with methods that have `self` or `cls` as one of their args

        Compatible with `@staticmethod` decorator, but it must be under `@overload`:
        ```
        class SomeClass:
            @overload
            @staticmethod
            def foo(): ...
        ```
        """
        def __init__(self, *, strictness=0, field=False):...

