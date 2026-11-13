"""
`javapy.py` made by <[@SmartBoty](https://github.com/SmartBoty)>

Original source (and `README`): [javapy on github](https://github.com/SmartBoty/Minescript/tree/main/javapy)

Bugreports and suggestions are welcome in the discord thread! [javapy on discord](https://discord.com/channels/930220988472389713/1543638360143437845)

`javapy` is licensed under [MIT](https://github.com/SmartBoty/Minescript/blob/main/javapy/LICENSE)
"""
# == Config == #
debug = False
# ============ #

import sys
from weakref import WeakKeyDictionary
from uuid import uuid4
from threading import get_ident, Lock, Thread
import json
from system.lib.java import eval_pyjinn_script as eps, JavaObject as BuiltinJavaObject
from system.lib.minescript import echo
from concurrent.futures import Future
import socket
from typing import TYPE_CHECKING
from queue import Queue
import inspect
import ast
from time import sleep
import builtins

_bridge = socket.socket()
_bridge.bind(("127.0.0.1", 0))
_bridge.listen(1)
_port = _bridge.getsockname()[1]
js = WeakKeyDictionary()
"""
Dictionary containing all java refference objects
"""
_concurrent = {}
_writer_lock = Lock()
_gc_queue = Queue()
_class_cache = {}

def _debug(*msg):
    if debug: echo("§d[§aJavapy§d] §b",*msg)
def new_ufcid():
    """
    Creates a thread- safe/unique identifier

    `UFCID`™ is short for `(universally) unique function call identifier`™
    """
    return f"{get_ident()}@{uuid4()}"
def _resolve_class(clss):
    global _class_cache
    """
    Not part of the public API

    Internal implementation of `JavaClass()`
    """
    _debug("Resolving class",clss)
    if clss not in _class_cache:
        jobj = JavaObject(type="JavaClass", **run_call({"type":_OpCodes.JavaClass,"class":clss}))
        _class_cache[clss] = jobj
        js[jobj]["clss"] = clss
    return _class_cache[clss]
def _resolve_field(self, field):
    """
    Not part of the public API

    Internal implementation of `obj.foo`
    """
    _debug("Resolving field",field)
    result = run_call({"type":_OpCodes.Field,"field":field,"of":ref(self)})
    if result["java_type"]:
        return JavaObject(**result["value"])
    else: return result["value"]
def _resolve_method(self, method, args):
    """
    Not part of the public API

    Internal implementation of `obj.foo()`
    """
    _debug("Resolving method:",method,"of",self)
    result = run_call({"type":_OpCodes.Method,"method":method,"of":ref(self),"args":wrap_items(args)})
    if result["java_type"]:
        return JavaObject(**result["value"])
    else: return result["value"]
def _resolve_ctor(self, args):
    """
    Not part of the public API

    Internal implementation of `obj()`
    """
    _debug("Resolving ctor / pyjinn func call:",self)
    result = run_call({"type":_OpCodes.Ctor,"of":ref(self),"args":wrap_items(args)})
    if result["java_type"]:
        return JavaObject(**result["value"])
    else: return result["value"]
def _resolve_jc_to_ctor(clss, args):
    """
    Not part of the public API

    Internal implementation of `_JavaClassToContructorInvoker()`
    """
    _debug("Resolving JavaClass resolving to constructor:",clss)
    result = run_call({"type":_OpCodes.ConstructJavaClass,"class":clss,"args":wrap_items(args)})
    if result["java_type"]: return JavaObject(**result["value"])
    else: return result["value"]
def run_call(call, fire_and_forget=False):
    """
    Not part of the public API

    Carries out a callrequest to Pyjinn, and propagates result

    Every function, method and class of `javapy.py` eventually reaches this function

    raises `JavaException` when something went wrong
    
    returns `None` if `fire_and_forget` is `True`, and will not block untill the call completes (Exception propagation will behave incorrectly!)
    """
    _debug(f"Running call ({fire_and_forget}):",call)
    if fire_and_forget:
        call["ufcid"] = -1
        with _writer_lock:
            _writer.write(json.dumps(call,separators=(',', ':')) + "\n")
            _writer.flush()
    else:
        ufcid = new_ufcid()
        call["ufcid"] = ufcid
        future = Future()
        _concurrent[ufcid] = future
        with _writer_lock:
            _writer.write(json.dumps(call,separators=(',', ':')) + "\n")
            _writer.flush()
        result = future.result()
        if result["fail"]: raise JavaException("\n"+result["reason"])
        else:
            for i in result["new_classes"]:
                _class_cache[i[1]] = JavaObject(ref_id=i[0],str=i[1])
            return result["result"]
def wrap_item(item):
    """
    Not part of the public API

    Internal wrapper to wrap singular args
    """
    if item in js: return {"java_type":True,"value":ref(item)}
    else: return {"java_type":False,"value":item}
def wrap_items(items):
    """
    Not part of the public API

    Converts `list[Any]` into `tuple[list[Any|None], list[int|None]]`, where the second list is a list of `ref_id`-s
    """
    args = []
    java_args = []
    for i in items:
        if i in js:
            java_args.append(ref(i))
            args.append(None)
        else:
            java_args.append(None)
            args.append(i)
    return args,java_args
def unwrap_items(items):
    """
    Not part of the public API

    Converts `list[list[Any|None], list[int|None]]` (where the second list is a list of `ref_id`-s) into `list[Any|JavaObject]`
    """
    args, java_args = items
    out = []
    for i in range(len(args)):
        if java_args[i] is None:
            out.append(args[i])
        else: out.append(js[java_args[i]])
    return out
def ref(item):
    """
    Returns the `ref_id` of any object that has a java side refference

    raises `TypeError` if there is no java side object
    """
    self = js.get(item)
    if self is not None: return self["ref"]
    else: raise TypeError(f"{item!r} ({builtins.type(item).__name__}) does not have a java side refference!")
def set_limit(limit):
    """
    Changes the max instructions javapy is allowed to read per frame

    Higher numbers may cause FPS lag and / or faster execution when multithreaded

    Default is 50
    """
    _debug("Changing read limit to",limit)
    run_call({"type":_OpCodes.SetLimit,"limit":limit},fire_and_forget=True)
def _get_many(names, of):
    """
    Not part of the public API

    Condenses many `script.get()` calls into one
    """
    return run_call({"type":_OpCodes.GETMANY,"names":names,"of":ref(of)})
def _get_names_from(ast_body):
    """
    Helper for AST

    Grabs all variable, function and class names from an ast tree body
    """
    names = []
    for node in ast_body:
        if builtins.isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.append(node.name)
        elif builtins.isinstance(node, ast.ClassDef): #TODO
            names.append(node.name)
        elif builtins.isinstance(node, ast.Assign):
            names += [n.id for n in node.targets]
        #elif builtins.isinstance(node, ast.With):
        #    return _get_names_from(node.body)
    return names
def add_event_listener(event,callback, keepalive=False):
    """
    Equivalent to its Pyjinn counterpart for the majority

    if `keepalive` is `True`, the script will never exit on its own (does not block)
    """
    run_call({"type":_OpCodes.AEL,"on":ref(callback),"event":event},fire_and_forget=True)
    if keepalive:
        def worker():
            while True: sleep(1000)
        Thread(target=worker).start()
def request(uuid):
    result = run_call({"type":_OpCodes.Request,"uuid":uuid})
    if result["java_type"]:
        return JavaObject(**result["value"])
    else: return result["value"]
def submit(obj):
    uuid = new_ufcid()
    run_call({"type":_OpCodes.Submit,"uuid":uuid,"obj":wrap_item(obj)})
    return uuid
def convert(obj):
    if obj in js:
        return _grab_from_pyjinn(submit(obj))
    else: return JavaObject(**run_call({"type":_OpCodes.Conv,"uuid":_put_to_pyjinn(obj)}))
def isinstance(obj, classes):
    """
    Custom `isisntance()` implementation to work with `JavaObject`-s

    Uses the builtin if types are not `JavaObject`
    """
    if type(classes) == tuple:
        return any(isinstance(obj, clss) for clss in classes)
    else:
        if classes in js:
            objt = type(obj)
            clss = type(classes)
            return type(obj) == type(classes)
        else: return builtins.isinstance(obj,classes)

class JavaException(Exception):
    """
    Base class for all of `javapy.py`-s exceptions
    """
    pass

class _OpCodes:
    """
    Not part of the public API

    Holds some OP codes used by the Python <---> Pyjinn IPC
    """
    JavaClass = 0
    Field = 1
    Method = 2
    Ctor = 3
    Batch = 4
    Debatch = 5
    ConstructJavaClass = 6
    GC = 7
    SetLimit = 8
    GetItem = 9
    SetItem = 10
    SetAttr = 11
    Iter = 12
    EPS = 13
    GET = 14
    GETMANY = 15
    AEL = 16
    Submit = 17
    Request = 18
    Conv = 19

class _MethodInvoker:
    """
    Not part of the public API

    Resolves and calls a method of a `JavaObject` in one call to java
    """
    def __init__(self, parent, name):
        self.parent = parent
        self.name = name

    def __call__(self, *args):
        return _resolve_method(self.parent, self.name, args)

class _JavaClassToContructorInvoker:
    """
    Not part of the public API

    Resolves and constructs a JavaClass in one call to java
    """
    def __init__(self, clss):
            self.clss = clss
    
    def __call__(self, *args):
        return _resolve_jc_to_ctor(self.clss, args)

class JavaObject:
    def __init__(self, ref_id, type="JavaObject", **kwargs):
        js[self] = {"type":type, "ref":ref_id, **kwargs}

    def __getattribute__(self, name):
        if js[self]["type"] == "script":
            if name == "get":
                return lambda n: PyjinnScript.get(self,n)
        frame = sys._getframe(1)
        if frame.f_code.co_code[frame.f_lasti + 1] & 1: return _MethodInvoker(self, name)
        else: return _resolve_field(self, name)

    def __call__(self, *args):
        return _resolve_ctor(self, args)

    def __del__(self):
        try: _gc_queue.put_nowait(ref(self))
        except: pass

    def __getitem__(self, key):
        result = run_call({"type":_OpCodes.GetItem,"key":wrap_item(key),"of":ref(self)})
        if result["java_type"]:
            return JavaObject(**result["value"])
        else: return result["value"]

    def __setitem__(self, key, value):
        run_call({"type":_OpCodes.SetItem,"key":wrap_item(key),"of":ref(self),"to":wrap_item(value)})
        return value

    def __setattr__(self, name, value):
        run_call({"type":_OpCodes.SetAttr,"attr":name,"of":ref(self),"to":wrap_item(value)})
        return value

    def __iter__(self):
        js[self]["iterator"] = -1
        return self

    def __next__(self):
        js[self]["iterator"] += 1
        result = run_call({"type":_OpCodes.Iter,"of":ref(self),"idx":js[self]["iterator"]})
        if result["stop"]: raise StopIteration
        if result["java_type"]:
            return JavaObject(**result["value"])
        else: return result["value"]

    def __str__(self): return js[self]["str"]
    def __repr__(self): return str(self)

    def __instancecheck__(self, obj):
        return obj in js

class JavaClass(JavaObject):
    def __new__(cls, clss):
        frame = sys._getframe(1)
        if frame.f_code.co_code[frame.f_lasti + 8] == 34: return _JavaClassToContructorInvoker(clss)
        else: return _resolve_class(clss)

class PyjinnScript(JavaObject):
    def __new__(cls, src):
        return JavaObject(type="script",**run_call({"type":_OpCodes.EPS,"src":src}))

    @staticmethod
    def get(self, name):
        _debug("Redirected attribute 'get' to PyjinnScript")
        result = run_call({"type":_OpCodes.GET,"name":name,"of":ref(self)})
        if result["java_type"]: return JavaObject(**result["value"])
        else: return result["value"]

def eval_pyjinn_script(src:str):
    """
    Evaluates sourcecode as Pyjinn sourcecode, and returns a handle to the underlying pyjinn script instance
    """
    return PyjinnScript(src)

class _PyjinnContextLeave(Exception): pass

class Pyjinn:
    """
    Pyjinn context manager to mimic `Jynnton`-s `Pyjinn` context manager

    Instantiation is optional, but without it threadsafety may become a problem
    """
    def __enter__(self):
        _debug("Gathering src for Pyjinn context...")
        frame = sys._getframe(1)
        module = inspect.getmodule(frame)
        src, start_line = inspect.getsourcelines(frame)
        current_line = frame.f_lineno - start_line - 1
        base_indent = None
        source = []
        lines = src[current_line:]
        stripped = lines.pop(0).lstrip()
        if not stripped.rstrip().endswith(":"):
            source = [stripped[5:].strip()]
        else:
            for line in lines:
                line = line[:-1]
                stripped = line.lstrip()
                indent = len(line) - len(stripped)
                if base_indent is None: base_indent = indent
                elif indent < base_indent and stripped: break
                source.append(line[base_indent:])
        src = "\n".join(source)
        _debug("Gathered:\n",src)
        names = _get_names_from(ast.parse(src).body)
        obj = PyjinnScript(src)
        for i, objdef in enumerate(_get_many(names, obj)):
            if objdef["java_type"]:
                val = JavaObject(**objdef["value"])
            else: val = objdef["value"]
            setattr(module,names[i],val)
        def burn(f, event, arg):
            if event == "line" and f == frame: raise _PyjinnContextLeave
            return burn
        sys.settrace(burn)
        frame.f_trace = burn
        return self

    def __exit__(self, exc_type, exc, tb):
        sys.settrace(None)
        if exc_type == _PyjinnContextLeave: return True

    def __call__(self):
        return builtins.type(self)()
Pyjinn = Pyjinn()

class type:
    """
    Custom `type()` implementation to work with `JavaObject`-s

    Uses the builtin for any other object
    """
    def __new__(cls, obj):
        if obj in js:
            r = js[obj]["class"]
            return [obj for obj in js if js[obj]["ref"] == r][0]
        else: return builtins.type(obj)

_s = eps(
r"""
import atexit
from pyjinn_plus import inspect
import pyjinn_json as json
Socket = JavaClass("java.net.Socket")
BufferedWriter = JavaClass("java.io.BufferedWriter")
OutputStreamWriter = JavaClass("java.io.OutputStreamWriter")
StandardCharsets = JavaClass("java.nio.charset.StandardCharsets")
BufferedReader = JavaClass("java.io.BufferedReader")
InputStreamReader = JavaClass("java.io.InputStreamReader")
JavaClassType = JavaClass("org.pyjinn.interpreter.JavaClass")
Class = JavaClass("java.lang.Class")
TypeChecker = JavaClass("org.pyjinn.interpreter.Script$TypeChecker")
Array = JavaClass("java.lang.reflect.Array")
Object = JavaClass("java.lang.Object")
Set = JavaClass("java.util.Set")
Assignment = JavaClass("org.pyjinn.interpreter.Script$Assignment")
Script = JavaClass("org.pyjinn.interpreter.Script")
IllegalArgumentException = JavaClass("java.lang.IllegalArgumentException")
UnsupportedOperationException = JavaClass("java.lang.UnsupportedOperationException")
IndexOutOfBoundsException = JavaClass("java.lang.IndexOutOfBoundsException")
Minescript = JavaClass("net.minescript.common.Minescript")

bridge = Socket("127.0.0.1", """ + str(_port) + r""")
bridge.setSoTimeout(1)
writer = BufferedWriter(OutputStreamWriter(bridge.getOutputStream(), StandardCharsets.UTF_8))
reader = BufferedReader(InputStreamReader(bridge.getInputStream(), StandardCharsets.UTF_8))
java_objects = {}
java_id = 0
read_limit = 50
scripts = []
call_method = [m for m in type(Script.Function).getDeclaredMethods() if m.getName() == "call"][0]
call_method.setAccessible(True)
if "javapy" not in __script__.vars["game"]:
    __script__.vars["game"]["javapy"] = {}
cache = {}
cache_id = 0
new_classes = []
java_classes = {}

def grab_from_pyjinn(uuid):
    return __script__.vars["game"]["javapy"][uuid]

def put_to_pyjinn(obj):
    global cache, cache_id
    cache[cache_id] = obj
    cache_id += 1
    return cache_id - 1

class PyjScriptObjectWrapper:
    def __init__(self,obj,script):
        self.obj = obj
        self.script = script
    
    def __call__(self,*args):
        return call_method.invoke(self.obj,as_array([self.script.mainModule().globals(),as_array(args)]))

class OpCodes:
    JavaClass = 0
    Field = 1
    Method = 2
    Ctor = 3
    Batch = 4
    Debatch = 5
    ConstructJavaClass = 6
    GC = 7
    SetLimit = 8
    GetItem = 9
    SetItem = 10
    SetAttr = 11
    Iter = 12
    EPS = 13
    GET = 14
    GETMANY = 15
    AEL = 16
    Submit = 17
    Request = 18
    Conv = 19

def get_java_obj(ref):
    obj = java_objects[ref]
    return obj
    
def return_call(data):
    writer.write(json.dumps(data) + "\n")

def unwrap_item(item):
    if item["java_type"]: return java_objects[item["value"]]
    else: return item["value"]
    
def unwrap_items(items):
    args, java_args = items
    out = []
    for i in range(len(args)):
        if java_args[i] is None:
            out.append(args[i])
        else:
            out.append(java_objects[java_args[i]])
    return out

def as_class(obj):
    if isinstance(obj, JavaClassType): return type(obj)
    elif isinstance(obj, Class): return obj
    else: return obj.getClass()

def as_array(items, specific_type=Object):
    array = Array.newInstance(type(specific_type),len(items))
    for i,arg in enumerate(items):
        Array.set(array, i, arg)
    return array

def classes_of(items):
    return TypeChecker.getTypes(as_array(items))

def add_obj(obj):
    global java_id
    java_objects[java_id] = obj
    java_id += 1
    return java_id - 1

def add_type(obj):
    global java_classes, java_id
    type = as_class(obj)
    if type not in java_classes:
        java_objects[java_id] = type
        java_classes[type] = java_id
        new_classes.append([java_id,type.toString()])
        java_id += 1
        return java_id - 1
    return java_classes[type]

def construct(obj, args):
    if isinstance(obj, PyjScriptObjectWrapper):
        return obj(*args)
    ctor = TypeChecker.findBestMatchingConstructor(as_class(obj), classes_of(args), None)
    if not ctor.isEmpty():
        return ctor.get().newInstance(__script__.mainModule().globals(), as_array(args))
    raise Exception(f"NoSuchConstructor: {as_class(obj).getName()}({", ".join([as_class(arg).getName() for arg in args])})")

method_func = lambda _, method: Set.of(method)
def invoke(obj, method, args):
    if isinstance(obj, (JavaClassType, Class)): static = True
    else: static = False
    clss = as_class(obj)
    m = TypeChecker.findBestMatchingMethod(clss, static, method_func, method, classes_of(args), None)
    if not m.isEmpty():
        return m.get().invoke(__script__.mainModule().globals(), (clss if static else obj), as_array(args))
    raise Exception(f"NoSuchMethod: {as_class(obj).getName()}.{method}({", ".join([as_class(arg).getName() for arg in args])})")

primitive_types = (str,int,float,bool)
def is_primitive(item):
    return (item is None or isinstance(item, primitive_types))

def handle_instruction(payload):
    global java_objects, read_limit
    result = {}
    if payload["type"] == OpCodes.Batch:
        vars = {}
        instructions = payload["instructions"]
        for inst in instructions:
            op = inst["op"]
            if op == OpCodes.JavaClass:
                vars[inst["store"]] = add_obj(JavaClassType.of(Class.forName(inst["class"])))
            elif op == OpCodes.Field:
                obj = java_objects[inst["of"]]
                vars[inst["store"]] = add_obj(as_class(obj).getField(inst["field"]).get(obj))
            elif op == OpCodes.Method:
                obj = java_objects[inst["of"]]
                vars[inst["store"]] = add_obj(invoke(obj,inst["method"], unwrap_items(inst["args"])))
            elif op == OpCodes.Ctor:
                vars[inst["store"]] = add_obj(construct(java_objects[inst["of"]], unwrap_items(inst["args"])))
            elif op == OpCodes.ConstructJavaClass:
                vars[inst["store"]] = add_obj(construct(JavaClassType.of(Class.forName(inst["class"])), unwrap_items(inst["args"])))
            else: raise Exception("Unknown batched op: " + str(op))
        result = vars
    elif payload["type"] == OpCodes.Method:
        obj = get_java_obj(payload["of"])
        if isinstance(obj, PyjScriptObjectWrapper):
            obj = obj.obj
        res = invoke(obj,payload["method"],unwrap_items(payload["args"]))
        if is_primitive(res):
            result = {"java_type":False,"value":res}
        else: result = {"java_type":True,"value":{"ref_id":add_obj(res),"str":str(res),"class":add_type(res)}}
    elif payload["type"] == OpCodes.Field:
        obj = get_java_obj(payload["of"])
        res = as_class(obj).getField(payload["field"]).get(obj)
        if is_primitive(res):
            result = {"java_type":False,"value":res}
        else: result = {"java_type":True,"value":{"ref_id":add_obj(res),"str":str(res),"class":add_type(res)}}
    elif payload["type"] == OpCodes.Ctor:
        obj = get_java_obj(payload["of"])
        res = construct(obj,unwrap_items(payload["args"]))
        if is_primitive(res):
            result = {"java_type":False,"value":res}
        else: result = {"java_type":True,"value":{"ref_id":add_obj(res),"str":str(res),"class":add_type(res)}}
    elif payload["type"] == OpCodes.JavaClass:
        obj = JavaClassType.of(Class.forName(payload["class"]))
        result = {"ref_id":add_obj(obj),"str":str(obj),"class":add_type(obj)}
    elif payload["type"] == OpCodes.Debatch:
        result = []
        for ref in payload["refs"]:
            if ref is None: result.append(None)
            else: result.append(java_objects[ref])
    elif payload["type"] == OpCodes.ConstructJavaClass:
        res = construct(JavaClassType.of(Class.forName(payload["class"])),unwrap_items(payload["args"]))
        if is_primitive(res):
            result = {"java_type":False,"value":res}
        else: result = {"java_type":True,"value":{"ref_id":add_obj(res),"str":str(res),"class":add_type(res)}}
    elif payload["type"] == OpCodes.GC:
        del java_objects[payload["ref"]]
    elif payload["type"] == OpCodes.SetLimit:
        read_limit = payload["limit"]
    elif payload["type"] == OpCodes.GetItem:
        obj = get_java_obj(payload["of"])
        key = unwrap_item(payload["key"])
        res = obj[key]
        if is_primitive(res):
            result = {"java_type":False,"value":res}
        else: result = {"java_type":True,"value":{"ref_id":add_obj(res),"str":str(res),"class":add_type(res)}}
    elif payload["type"] == OpCodes.SetItem:
        obj = get_java_obj(payload["of"])
        key = unwrap_item(payload["key"])
        to = unwrap_item(payload["to"])
        Assignment.assignArray(obj, key, to)
    elif payload["type"] == OpCodes.SetAttr:
        obj = get_java_obj(payload["of"])
        key = payload["attr"]
        to = unwrap_item(payload["to"])
        try:
            if not Assignment.assignField(obj,key,to): raise IllegalArgumentException(f"Unsupported expression type for lhs of assignment: {obj}")
        except UnsupportedOperationException:
            try: as_class(obj).getField(key).set(obj, to)
            except: raise IllegalArgumentException(f"Unsupported expression type for lhs of assignment: {obj}")
    elif payload["type"] == OpCodes.Iter:
        obj = get_java_obj(payload["of"])
        key = payload["idx"]
        try:
            res = obj[key]
            stop = False
        except IndexOutOfBoundsException:
            res = None
            stop = True
        if is_primitive(res):
            result = {"java_type":False,"value":res,"stop":stop}
        else: result = {"java_type":True,"value":{"ref_id":add_obj(res),"str":str(res),"class":add_type(res)},"stop":stop}
    elif payload["type"] == OpCodes.EPS:
        script = Minescript.loadPyjinnScript(JavaList(["__eval_pyjinn_script__"]), payload["src"])
        script.redirectStdout(__script__.stdout)
        script.redirectStderr(__script__.stderr)
        scripts.append(script)
        result = {"ref_id":add_obj(script),"str":str(script),"class":add_type(script)}
        script.vars["job"] = __script__.vars["job"]
        script.vars["game"] = __script__.vars["game"]
        script.exec()
    elif payload["type"] == OpCodes.GET:
        script = get_java_obj(payload["of"])
        obj = script.get(payload["name"])
        if is_primitive(obj): result = {"java_type":False,"value":obj}
        else: result = {"java_type":True,"value":{"ref_id":add_obj(PyjScriptObjectWrapper(obj,script)),"str":str(obj),"class":add_type(obj)}}
    elif payload["type"] == OpCodes.GETMANY:
        script = get_java_obj(payload["of"])
        result = []
        for name in payload["names"]:
            obj = script.get(name)
            if is_primitive(obj): res = {"java_type":False,"value":obj}
            else: res = {"java_type":True,"value":{"ref_id":add_obj(PyjScriptObjectWrapper(obj,script)),"str":str(obj),"class":add_type(script)}}
            result.append(res)
    elif payload["type"] == OpCodes.AEL:
        add_event_listener(payload["event"],get_java_obj(payload["on"]))
    elif payload["type"] == OpCodes.Request:
        res = __script__.vars["game"]["javapy"][payload["uuid"]]
        if is_primitive(res):
            result = {"java_type":False,"value":res}
        else: result = {"java_type":True,"value":{"ref_id":add_obj(res),"str":str(res),"class":add_type(res)}}
    elif payload["type"] == OpCodes.Submit:
        __script__.vars["game"]["javapy"][payload["uuid"]] = unwrap_item(payload["obj"])
    elif payload["type"] == OpCodes.Conv:
        obj = cache[payload["uuid"]]
        del cache[payload["uuid"]]
        result = {"ref_id":add_obj(obj),"str":str(obj),"class":add_type(obj)}
    else: raise Exception(f"No such instruction: {payload["type"]}")
    return_call({"ufcid":payload["ufcid"],"result":result, "fail":False, "new_classes":new_classes})
    new_classes.clear()

def main(_):
    lines = []
    iters = 0
    if not reader.ready(): return
    while True:
        iters += 1
        if iters > read_limit: log("[Javapy] Overloaded! Exiting reader...") ; break
        try:
            if not reader.ready(): break
            line = reader.readLine()
            if line: lines.append(line)
            else: break
        except Exception as e:
            if "SocketTimeout" not in str(e): log(f"Exception caught! {e}")
            break
    try:
        for line in lines:
            payload = json.loads(line)
            handle_instruction(payload)
            try: pass
            except Exception as e:
                return_call({"ufcid":payload["ufcid"],"fail":True,"reason":str(e)})
    finally: writer.flush()

add_event_listener("render",main)
atexit.register(lambda: [s.exit() for s in scripts])
""")

_conn, _ = _bridge.accept()
_reader = _conn.makefile("r", encoding="utf-8")
_writer = _conn.makefile("w", encoding="utf-8")
_grab_from_pyjinn = _s.get("grab_from_pyjinn")
_put_to_pyjinn = _s.get("put_to_pyjinn")

def __reader__():
    while True:
        line = _reader.readline()
        data = json.loads(line)
        if data["ufcid"] == -1:
            if data["fail"]:
                print("Javapy system error:\n"+str(data["reason"]),file=sys.stderr)
        elif data["ufcid"] in _concurrent:
            _debug("Returning from call with:",data)
            _concurrent.pop(data["ufcid"]).set_result(data)
Thread(target=__reader__,daemon=True).start()

def __garbage_collector__():
    while True:
        run_call({"type":_OpCodes.GC,"ref":_gc_queue.get()},fire_and_forget=True)
Thread(target=__garbage_collector__,daemon=True).start()

__script__ = PyjinnScript("None")
if TYPE_CHECKING:
    class JavaObject:
        """
        Not part of the public API

        Generate a refference holder pointing to the java side object with the refference id `ref_id`
        ```py
        obj = JavaObject(0,**{"str":"<Some java object>","class":1}) # Assuming there is an object at refference # 0, and a type reference at # 1
        print(obj) # '<Some java object>'
        ```
        Supports iteration

        Every `javapy.py` function that returns some sort of java side object, will eventually reach this class
        """
        def __init__(self, ref_id, type="JavaObject", **kwargs) -> JavaObject: ...
        def __getattr__(self, name) -> JavaObject: ...
        def __call__(self, *args) -> JavaObject: ...
    class JavaClass(JavaObject):
        """
        Resolve and evaluate a JavaClass

        raises `JavaException` if resolution failed
        """
        def __init__(self, clss) -> JavaObject: ...
    class PyjinnScript(JavaObject):
        """
        Not part of the public API, use `eval_pyjinn_script` instead

        Evaluates sourcecode as Pyjinn sourcecode, and returns a handle to the underlying pyjinn script instance.

        Redirects `.get` attribute access from `JavaObject` to `PyjinnScript.get()`
        """
        def __init__(self, src) -> JavaObject: ...
    def submit(obj:JavaObject) -> str:
        """
        Submit an object to Pyjinn, returns the uuid it was stored under, to `__script__.vars["game"]["javapy"]`
        """
    def request(uuid:str) -> JavaObject:
        """
        Request an object from Pyjinn stored under `uuid` in `__script__.vars["game"]["javapy"]`
        """
    def convert(obj:BuiltinJavaObject|JavaObject) -> BuiltinJavaObject|JavaObject:
        """
        Converts a `java.py` (builtin) object into a `javapy.py` object, and vice versa
        """
__all__ = [
    "JavaException",
    "JavaClass",
    "ref",
    "eval_pyjinn_script",
    "__script__",
    "Pyjinn",
    "add_event_listener",
    "JavaObject",
    "request",
    "submit",
    "convert",
    "type",
    "isinstance"
]
