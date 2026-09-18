import inspect
from typing import TYPE_CHECKING

overloaded = {}

class SignatureDulicateElementException(Exception): pass

def _resolve_signature(args:tuple,kwargs:dict):
    resolved_args = []
    resolved_kwargs = {}
    for arg in args:
        resolved_args.append({"type":type(arg),"value":arg})
    for key, value in kwargs.items():
        resolved_kwargs[key] = {"type":type(value),"value":value}
    return {"args":resolved_args,"kwargs":resolved_kwargs}

def _mathches_signature(call_signature, func_signature):
    func_signature_types = [func_signature[key]["type"] for key in func_signature]
    func_signature_keys = list(func_signature.keys())
    found_posargs = []
    completed = []
    i = -1
    for sig in call_signature["args"]:
        i += 1
        if i == len(func_signature_types): break
        if isinstance(sig["type"], func_signature_types[i]) or sig["type"] == func_signature_types[i]:
            if func_signature[func_signature_keys[i]]["kind"] == inspect.Parameter.VAR_POSITIONAL:
                found_posargs.append(sig["value"])
                completed.append(func_signature_keys[i])
                i -= 1
            elif func_signature[func_signature_keys[i]]["kind"] == inspect.Parameter.KEYWORD_ONLY:
                call_signature["kwargs"].update(func_signature[func_signature_keys[i]])
            else:
                found_posargs.append(sig["value"])
                completed.append(func_signature_keys[i])
    missing = call_signature["args"][len(found_posargs):]
    for key in func_signature_keys[len(found_posargs):]:
        if func_signature[key]["kind"] == inspect.Parameter.POSITIONAL_ONLY:
            return False
    if not missing:
        i = len(found_posargs)
        for key, value in call_signature["kwargs"].items():
            i += 1
            if key in completed:
                raise SignatureDulicateElementException(key)
            elif key not in func_signature:
                return False
            else:
                if isinstance(value["type"], func_signature[key]["type"]) or value["type"] == func_signature[key]["type"]:
                    pass
                else:
                    return False
        return True
    return False

def _pretty_signature_types(call_signature):
    pretty = []
    for item in call_signature["args"]:
        pretty.append(item["type"].__name__)
    for item in call_signature["kwargs"]:
        pretty.append(f"{item}={call_signature["kwargs"][item]["type"].__name__}")
    return ", ".join(pretty)

class overload:
    def __init__(self, func):
        self.func = func
        sig = {}
        override_annotation = False
        for name, param in inspect.signature(func).parameters.items():
            annotation = param.annotation
            if annotation is inspect._empty:
                annotation = object
            sig[name] = {"type": annotation, "kind":param.kind}
        self.sig = sig
        self.init = False
        self.method_type = "function"
        self.qname = func.__qualname__
        self.class_id = str(__file__) + self.qname.split(".")[0]
        self.id = self.class_id + self.qname
        self.name = func.__name__
        if __file__ not in overloaded:
            overloaded[__file__] = {}
        if self.id not in overloaded[__file__]:
            overloaded[__file__][self.id] = []
        if self.name not in overloaded[__file__]:
            overloaded[__file__][self.name] = []
        overloaded[__file__][self.id].append(self)
        overloaded[__file__][self.name].append(self)
    def __str__(self):
        return f"{self.func}"

    def __set_name__(self, owner, name):
        self.clss = owner
        if self.clss not in overloaded:
            overloaded[self.clss] = {self.name:[]}
        for obj in overloaded[__file__][self.id]:
            if obj.id == self.id:
                obj.method_type = "method"
                overloaded[self.clss][self.name].append(obj)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        self.method_type = "method"
        self.instance = instance
        return self

    def __call__(self,*args,**kwargs):
        if self.method_type == "method":
            args = (self.instance,) + args
            clss = self.clss
        else:
            clss = __file__
        for overload in overloaded[clss][self.name]:
            if not overload.method_type == self.method_type: continue
            try:
                matches = _mathches_signature(_resolve_signature(args,kwargs),overload.sig)
            except SignatureDulicateElementException as e:
                raise TypeError(f"{self.name}() got multiple values for argument '{e}'")
            if matches:
                return overload.func(*args,**kwargs)
        if self.method_type == "method":
            raise AttributeError(f"'{self.clss.__name__}' object has no attribute '{self.func.__name__}' with a matching signature")
        else: raise TypeError(f"'{self.name}' has no matching signature: {self.name}({_pretty_signature_types(_resolve_signature(args,kwargs))})")

if TYPE_CHECKING:
    class overload:
        """
        Overloads a method/function, allowing multiple signatures to resolve to different functions under the same name

        Can be used on both methods and function
        """