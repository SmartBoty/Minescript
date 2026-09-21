from __future__ import annotations
import socket
from typing import Any, TYPE_CHECKING
from system.lib.java import eval_pyjinn_script as eps, JavaObject as java_JavaObject
from uuid import uuid4
from threading import get_ident, Thread, Lock
import json
from concurrent.futures import Future
from system.lib.minescript import log, echo
from weakref import WeakKeyDictionary
from time import sleep
from queue import Queue
import builtins
import sys

concurrent = {}
js = WeakKeyDictionary()
garbage_lock = Lock()
garbage = Queue()
java_types = {}
java_classes = {}
thread_amr_vars = {}
amrl = Lock()
global_amr_override = None

supress_java_error_messages = False
debug_level = 0
def debug_log(*msg,level=0):
    if (level <= debug_level or debug_level >= 9) and debug_level:
        op = log if (not debug_level >= 9) or level == debug_level else echo
        op(" ".join(msg))

def next_ufcid(): return f"{get_ident()}@{uuid4()}"

call_lock = Lock()
def run_call(data:dict):
    future = Future()
    concurrent[data["ufcid"]] = future
    with call_lock:
        writer.write(json.dumps(data)+"\n")
        writer.flush()
    result = future.result()
    if result["fail"]:
        if supress_java_error_messages: raise JavaException()
        else: raise JavaException(result["reason"])
    return result

def convert(obj:JavaObject|java_JavaObject) -> java_JavaObject|JavaObject:
    """
    Converts a javapy.py object into a java.py object (builtin)

    OR

    Converts a java.py object (builtin) into a javapy.py object
    """
    if isinstance(obj,JavaObject):
        uuid = submit_object(obj)
        return _convert_from(uuid)
    elif isinstance(obj,java_JavaObject):
        id,runtime_type,*name = _convert_to(obj).split(";")
        return JavaObject(id,";".join(name))
    else: raise ValueError(f"Cannot determine wether type '{type(obj).__class__}' is from java.py (builtin) or javapy.py!")

def request_object(uuid) -> JavaObject:
    """
    Request a previously submitted object from a uuid.

    Global, any process can request the object if they have the uuid
    """
    debug_log(f"Requesting object: {uuid}")
    ufcid = next_ufcid()
    result = run_call({"ufcid":ufcid,"type":4,"uuid":uuid})
    if not result["java_type"]: return result["value"]
    else: return JavaObject(result["id"],result["name"],result["runtime_type"])

def submit_object(obj):
    """
    Submit a javapy object, returns the uuid wich it was stored under
    """
    debug_log(f"Submitting object: {repr(obj)}")
    ufcid = next_ufcid()
    result = run_call({"ufcid":ufcid,"type":5,"obj_id":js[obj]["id"]})
    return result["uuid"]

def resolve_class(clss:str):
    debug_log(f"Resolving class: {clss}")
    ufcid = next_ufcid()
    result = run_call({"ufcid":ufcid,"type":0,"class":clss})
    return result["id"], result["name"], result["runtime_type"]

def resolve_member(member:str,obj:JavaObject):
    debug_log(f"Resolving member {member} of {repr(obj)}")
    ufcid = next_ufcid()
    result = run_call({"ufcid":ufcid,"type":1,"member":member,"obj_id":js[obj]["id"]})
    if result["field"]:
        if not result["java_field"]: return result["value"]
        else: return JavaObject(result["id"],result["name"],result["runtime_type"])
    else: return JavaMember(obj,member)

def resolve_member_as_method(member:str, obj:JavaObject):
    ufcid = next_ufcid()
    run_call({"ufcid":ufcid,"type":13,"obj":js[obj]["id"],"method":member})
    return JavaMethod(member,obj)

def resolve_member_as_field(member:str, obj:JavaObject):
    ufcid = next_ufcid()
    result = run_call({"ufcid":ufcid,"type":14,"obj":js[obj]["id"],"field":member})
    if not result["java_field"]: return result["value"]
    else: return JavaObject(result["id"],result["name"],result["runtime_type"])

def resolve_type(obj:JavaObject):
    debug_log(f"Resolving type of {repr(obj)}")
    ufcid = next_ufcid()
    result = run_call({"ufcid":ufcid,"type":9,"id":js[obj]["id"]})
    typ = JavaType(result["id"],result["name"])
    js[obj]["runtime_type"] = typ
    return typ

def normalize_items(items):
    out_normal = []
    out_java = []
    for item in items:
        if isinstance(item, JavaObject):
            out_normal.append(None)
            if item in js:
                out_java.append(js[item]["id"])
            elif item in java_types:
                out_java.append(java_types[item]["id"])
            else: raise ValueError("Object doesnt exist!")
        else:
            out_normal.append(item)
            out_java.append(None)
    return out_normal, out_java

class type:
    def __new__(cls, obj) -> JavaObject:
        """
        Returns the runtime class of the JavaObject. For any other object, it uses the builtin protocol
        """
        if isinstance(obj, JavaObject):
            return js[obj]["runtime_type"] if "runtime_type" in js[obj] else resolve_type(obj)
        else: return builtins.type(obj)

class JavaException(Exception): pass

class JavaObject:
    def __init__(self, id, name, runtime_type):
        js[self] = {}
        js[self]["id"] = id
        js[self]["name"] = name
        js[self]["type"] = "JavaObject"
        js[self]["runtime_type"] = JavaType(runtime_type["id"], runtime_type["name"])

    def __str__(self):
        return js[self]["name"]

    def __repr__(self):
        return f"<{js[self]["type"]} {js[self]["id"]} {js[self]["name"]}>"

    def __call__(self,*args) -> JavaObject:
        ufcid = next_ufcid()
        normal_args, java_args = normalize_items(args)
        if js[self]["type"] == "FixedReturnFunction":
            debug_log(f"Resolving FixedReturnFunction call of {js[self]["name"]}")
            #result = run_call({"ufcid":ufcid,"type":11,"id":js[self]["id"]})
            #if not result["java_type"]: return result["value"]
            #else: return JavaObject(result["id"],result["name"],result["runtime_type"])
            return js[self]["obj"]
        else:
            debug_log(f"Resolving constructor call of {js[self]["name"]}{args}")
            result = run_call({"ufcid":ufcid,"type":3,"obj_id":js[self]["id"],"args":normal_args,"java_args":java_args})
            if not result["java_type"]: return result["value"]
            else: return JavaObject(result["id"],result["name"],result["runtime_type"])

    def __getattr__(self, name:str) -> JavaObject:
        with amrl:
            if global_amr_override is None:
                use_alt = thread_amr_vars[get_ident()]
            else: use_alt = global_amr_override
        if use_alt:
            debug_log(f"Resolving alternative member access: {js[self]["name"]}.{name}")
            frame = sys._getframe(1)
            if frame.f_code.co_code[frame.f_lasti + 1] & 1:
                debug_log(f"Resolved member '{name}' as a <METHOD> access")
                return resolve_member_as_method(name, self)
            else:
                debug_log(f"Resolved member '{name}' as a <FIELD> access")
                return resolve_member_as_field(name, self)
        else: return resolve_member(name, self)

    def __del__(self):
        #echo(f"Garbage collecting: {js[self]["id"]}")
        try: garbage.put(js[self]["id"])
        except Exception as e: debug_log(f"Failed to garbage collect: {e}")

    def __contains__(self, item):
        debug_log(f"Resolving __contains__ for {repr(self)}")
        ufcid = next_ufcid()
        if isinstance(item, JavaObject):
            java_type = True
            obj = js[item]["id"]
        else:
            java_type = False
            obj = item
        result = run_call({"ufcid":ufcid,"type":12,"java_type":java_type,"iterable_id":js[self]["id"],"obj":obj})
        return result["result"]

    def __iter__(self):
        i = -1
        ufcid = next_ufcid()
        while True:
            i += 1
            result = run_call({"ufcid":ufcid,"type":7,"id":js[self]["id"],"index":i,"is_iter":True})
            if result["stop"]: return
            if not result["java_type"]: yield result["value"]
            else: yield JavaObject(result["id"],result["name"],result["runtime_type"])

    def __getitem__(self, key):
        ufcid = next_ufcid()
        result = run_call({"ufcid":ufcid,"type":7,"id":js[self]["id"],"index":key,"is_iter":False})
        if not result["java_type"]: return result["value"]
        else: return JavaObject(result["id"],result["name"],result["runtime_type"])

    def __instancecheck__(self, other):
        self_id = java_types[js[self]["runtime_type"]]["id"]
        if isinstance(other, tuple):
            for obj in other:
                return any(self_id == java_types[js[obj]["runtime_type"]]["id"])
        else: return self_id == java_types[js[other]["runtime_type"]]["id"]

    def __len__(self):
        ufcid = next_ufcid()
        return run_call({"ufcid":ufcid,"type":8,"id":js[self]["id"]})["length"]

class JavaMethod(JavaObject):
    def __init__(self, member, obj):
        self.member = member
        self.obj = obj

    def __call__(self,*args):
        normal_args, java_args = normalize_items(args)
        ufcid = next_ufcid()
        result = run_call({"ufcid":ufcid,"type":2,"method":self.member, "obj_id":js[self.obj]["id"],"args":normal_args,"java_args":java_args})
        del self
        if not result["java_type"]: return result["value"]
        else: return JavaObject(result["id"],result["name"],result["runtime_type"])

class JavaMember(JavaObject):
    def __init__(self, parent:JavaObject, name:str):
        js[self] = {}
        js[self]["type"] = "JavaMember"
        js[self]["parent"] = parent
        js[self]["id"] = -1
        js[self]["name"] = name

    def __call__(self, *args) -> JavaObject:
        debug_log(f"Resolving method call of {js[js[self]["parent"]]["name"]}.{js[self]["name"]}{args}")
        ufcid = next_ufcid()
        normal_args, java_args = normalize_items(args)
        result = run_call({"ufcid":ufcid,"type":2,"method":js[self]["name"],"obj_id":js[js[self]["parent"]]["id"],"args":normal_args,"java_args":java_args})
        if not result["java_type"]: return result["value"]
        else: return JavaObject(result["id"],result["name"],result["runtime_type"])

    def __del__(self): pass

class JavaClass(JavaObject):
    def __init__(self, clss):
        """
        Resolves a java class
        """
        if self in js: return
        id, name, runtime_type = resolve_class(clss)
        js[self] = {}
        js[self]["id"] = id
        js[self]["name"] = name
        js[self]["type"] = "JavaClass"
        js[self]["runtime_type"] = JavaType(runtime_type["id"], runtime_type["name"])
        java_classes[clss] = self

    def __new__(cls, clss) -> JavaClass:
        if clss in java_classes:
            return java_classes[clss]
        else:
            return super().__new__(cls)

class JavaType(JavaObject):
    def __init__(self, id, name):
        java_types[self] = {"id":id,"name":name,"type":"JavaType"}
        js[self] = java_types[self]

    def __str__(self):
        return java_types[self]["name"]

    def __repr__(self):
        return f"<JavaType {java_types[self]["id"]} {java_types[self]["name"]}>"

    def __del__(self): pass

class FixedReturnFunction(JavaObject):
    def __new__(cls, obj:JavaObject) -> JavaObject:
        debug_log(f"Creating FixedReturnFunction from {repr(obj)}")
        if isinstance(obj, JavaObject):
            obj_id = js[obj]["id"]
            java = True
        else: java = False
        ufcid = next_ufcid()
        result = run_call({"ufcid":ufcid,"type":10,"returns":obj_id,"java":java})
        java_obj = JavaObject(result["id"],result["name"],result["runtime_type"])
        js[java_obj]["type"] = "FixedReturnFunction"
        js[java_obj]["obj"] = obj
        return java_obj

class PyjinnScript(JavaObject):
    init = None
    def __new__(cls):
        debug_log("Resolving creation of __script__")
        if PyjinnScript.init: return PyjinnScript.init
        ufcid = next_ufcid()
        result = run_call({"ufcid":ufcid,"type":11})
        return JavaObject(result["id"],result["name"],result["runtime_type"])

class _AlternativeMemberResolverHandler:
    def __enter__(self):
        thread_amr_vars[get_ident()] = True

    def __exit__(self, exc_type, exc, tb):
        thread_amr_vars[get_ident()] = False

    def enable(self):
        global global_amr_override
        global_amr_override = True

    def disable(self):
        global global_amr_override
        global_amr_override = False

    def clear(self):
        global global_amr_override
        global_amr_override = None

Alternative_Member_Resolver = _AlternativeMemberResolverHandler()
Alternative_Member_Resolver.enable()

bridge = socket.socket()
bridge.bind(("127.0.0.1", 0))
bridge.listen(1)
port = bridge.getsockname()[1]
script_loaded = False

def __convert_from(*args):
    global _convert_from
    while not script_loaded: pass
    _convert_from = script.get("convert_from")
    return _convert_from(*args)
_convert_from = __convert_from

def __convert_to(*args):
    global _convert_to
    while not script_loaded: pass
    _convert_to = script.get("convert_to")
    return _convert_to(*args)
_convert_to = __convert_to

def __start__():
    global script, script_loaded
    try: script = eps(
r"""
import pyjinn_json as json
Socket = JavaClass("java.net.Socket")
BufferedWriter = JavaClass("java.io.BufferedWriter")
OutputStreamWriter = JavaClass("java.io.OutputStreamWriter")
StandardCharsets = JavaClass("java.nio.charset.StandardCharsets")
BufferedReader = JavaClass("java.io.BufferedReader")
InputStreamReader = JavaClass("java.io.InputStreamReader")
Minescript = JavaClass("net.minescript.common.Minescript")
mappings = Minescript.mappingsLoader.get()
Class = JavaClass("java.lang.Class")
Array = JavaClass("java.lang.reflect.Array")
Object = JavaClass("java.lang.Object")
JavaClassType = JavaClass("org.pyjinn.interpreter.JavaClass")
UUID = JavaClass("java.util.UUID")
TypeChecker = JavaClass("org.pyjinn.interpreter.Script$TypeChecker")
mappings = JavaClass("net.minescript.common.Minescript").mappingsLoader.get()
Set = JavaClass("java.util.Set")
ArrayIndexOutOfBoundsException = JavaClass("java.lang.ArrayIndexOutOfBoundsException")
#Modifier = JavaClass("java.lang.reflect.Modifier")

def unpack_args(normal_args, java_args):
    args = []
    for i in range(len(normal_args)):
        if normal_args[i] is None and java_args[i] is not None:
            args.append(cached_java_objects[java_args[i]].obj)
        else: args.append(normal_args[i])
    return args

def get_type_class_of(obj):
    if isinstance(obj.obj, Class): clss = obj.obj
    elif isinstance(obj.obj, JavaClassType): clss = type(obj.obj)
    else: clss = obj.obj.getClass()
    return clss

def resolve_type(obj):
    global cached_java_types
    clss = get_type_class_of(obj)
    if not clss in cached_java_types:
        jo = JavaObject(clss)
        cached_java_types[clss] = jo
    return cached_java_types[clss]

def convert_from(uuid):
    obj = __script__.vars["game"]["javapy"][uuid]
    del __script__.vars["game"]["javapy"][uuid]
    return obj

def convert_to(obj):
    obj = JavaObject(obj)
    return f"{obj.id};{obj.obj}"

def as_array(items,specific_type=Object):
    array = Array.newInstance(type(specific_type),len(items))
    for i,arg in enumerate(items):
        Array.set(array, i, arg)
    return array

def as_class_array(items):
    array = Array.newInstance(type(Class),len(items))
    for i, arg in enumerate(items):
        if isinstance(arg, JavaClassType): arg = type(arg)
        elif not isinstance(arg, Class): arg = arg.getClass() if arg is not None else null
        Array.set(array, i, arg)
    return array

can_jsonify_types = (type(0),type(""),type(True),type(None))
def can_jsonify(obj):
    if isinstance(obj, can_jsonify_types): return True
    return False

def return_call(data):
    writer.write(json.dumps(data)+"\n")
    writer.flush()

def next_id():
    global current_id
    current_id += 1
    return current_id

def resolve_callable_method(self,clss,method,args):
    classes = as_class_array(args)
    m = TypeChecker.findBestMatchingMethod(clss, True, method_func, method, classes, None)
    try:
        m
        force_skip = False
    except: force_skip = True
    if not m.isEmpty() or force_skip:
        return (True, m.get())
    else:
        m = TypeChecker.findBestMatchingMethod(clss, False, method_func, method, classes, None)
        try: m
        except: raise Exception(f"Failed to find suitable method: {method}")
        if not m.isEmpty():
            return (False, m.get())
    raise Exception(f"NoSuchMethod: {method}({str(classes)[1:-1]}) (jpy)")

method_func = lambda _, method: Set.of(method)
def invoke(self,method,args):
    if isinstance(self.obj, JavaClassType): clss = type(self.obj)
    else: clss = self.obj.getClass()
    array_args = as_array(args)
    isstatic, method = resolve_callable_method(self,clss,method,args)
    if isstatic:
        return method.invoke(__script__.mainModule().globals(),clss,array_args)
    else:
        return method.invoke(__script__.mainModule().globals(),self.obj,array_args)

def construct(self,args):
    if isinstance(self.obj, JavaClassType): clss = type(self.obj)
    else: clss = self.obj.getClass()
    classes = as_class_array(args)
    array_args = as_array(args)
    classes = as_class_array(args)
    array_args = as_array(args)
    ctor = TypeChecker.findBestMatchingConstructor(clss, classes, None)
    if not ctor.isEmpty():
        return ctor.get().newInstance(__script__.mainModule().globals(),array_args)
    raise Exception(f"NoSuchConstructor: {self.obj}({str(classes)[1:-1]})")

class JavaClassObject:
    def __init__(self, clss):
        self.obj = JavaClassType.of(Class.forName(mappings.getRuntimeClassName(clss)))
        self.id = next_id()
        cached_java_objects[self.id] = self

class JavaObject:
    def __init__(self, obj):
        self.obj = obj
        self.id = next_id()
        cached_java_objects[self.id] = self
        self.type = "JavaObject"

bridge = Socket("127.0.0.1", """ + str(port) + r""")
null = bridge.setSoTimeout(1)
writer = BufferedWriter(OutputStreamWriter(bridge.getOutputStream(), StandardCharsets.UTF_8))
reader = BufferedReader(InputStreamReader(bridge.getInputStream(), StandardCharsets.UTF_8))
current_id = -1
cached_java_objects = {}
cached_java_types = {}
if "javapy" not in __script__.vars["game"]: __script__.vars["game"]["javapy"] = {}
scripts = []

def _main(_):
    global cached_java_objects, runtime_type_id
    lines = []
    iters = 0
    if not reader.ready(): return
    while True:
        iters += 1
        if iters > 50: log("Overloaded! Exiting reader...") ; break
        try:
            line = reader.readLine()
            if line: lines.append(line)
            else: break
        except Exception as e:
            if "SocketTimeout" not in str(e): log(f"Exception caught! {e}")
            break
    for line in lines:
        payload = json.loads(line)
        if payload["type"] == 0: # resolve_class {"ufcid":ufcid,"type":0,"class":clss}
            try:
                jco = JavaClassObject(payload["class"])
                runtime_type = resolve_type(jco)
                return_call({"ufcid":payload["ufcid"],"id":jco.id,"name":str(jco.obj),"fail":False,"runtime_type":{"name":str(runtime_type.obj),"id":runtime_type.id}})
            except Exception as e:
                return_call({"ufcid":payload["ufcid"],"fail":True,"reason":str(e)})
        elif payload["type"] == 1: # resolve member {"ufcid":ufcid,"type":1,"member":member,"obj_id":obj.id}
            obj = cached_java_objects[payload["obj_id"]]
            object = get_type_class_of(obj)
            #if isinstance(obj.obj, Class): object = obj.obj
            #elif isinstance(obj.obj, JavaClassType): object = type(obj.obj)
            #else: object = obj.obj.getClass()
            try:
                field = object.getField(payload["member"]).get(obj.obj)
                got_field = True
            except:
                field = None
                got_field = False
            got_method = False
            for method in object.getMethods():
                if method.getName() == payload["member"]:
                    got_method = True
                    break
            if got_field:
                if can_jsonify(field):
                    java_field = False
                    id = None
                    value = field
                    name = None
                    runtime_type = None
                else:
                    java_field = True
                    jo = JavaObject(field)
                    id = jo.id
                    value = None
                    name = str(jo.obj)
                    runtime_type = resolve_type(jo)
                return_call({"ufcid":payload["ufcid"],"fail":False,"field":True,"java_field":java_field,"value":value,"id":id,"name":name,"runtime_type":{"name":str(runtime_type.obj),"id":runtime_type.id}})
            elif got_method:
                return_call({"ufcid":payload["ufcid"],"fail":False,"field":False,"java_field":None,"value":None,"id":None,"name":None})
            else: return_call({"ufcid":payload["ufcid"],"fail":True,"reason":f"NoSuchMemberException: {obj.obj} has no member named {payload["member"]} (jpy)"})
        elif payload["type"] == 2: # method call {"ufcid":ufcid,"type":2,"method":js[self]["name"],"obj_id":js[js[self]["parent"]]["id"],"args":normal_args,"java_args":java_args}
            obj = cached_java_objects[payload["obj_id"]]
            normal_args = payload["args"]
            java_args = payload["java_args"]
            args = []
            for i in range(len(normal_args)):
                if normal_args[i] is None and java_args[i] is not None:
                    args.append(cached_java_objects[java_args[i]].obj)
                else: args.append(normal_args[i])
            try:
                result = invoke(obj,payload["method"],args)
            except Exception as e:
                return_call({"ufcid":payload["ufcid"],"fail":True,"reason":str(e)})
                continue
            if can_jsonify(result):
                java_type = False
                value = result
                id = None
                name = None
                runtime_type_name = None
                runtime_type_id = None
            else:
                java_type = True
                value = None
                jo = JavaObject(result)
                id = jo.id
                name = str(jo.obj)
                runtime_type = resolve_type(jo)
                runtime_type_name = str(runtime_type.obj)
                runtime_type_id = runtime_type.id
            return_call({"ufcid":payload["ufcid"],"fail":False,"java_type":java_type,"value":value,"id":id,"name":name,"runtime_type":{"name":runtime_type_name,"id":runtime_type_id}})
        elif payload["type"] == 3: # constructor call {"ufcid":ufcid,"type":3,"obj_id":js[self]["id"],"args":normal_args,"java_args":java_args}
            obj = cached_java_objects[payload["obj_id"]]
            normal_args = payload["args"]
            java_args = payload["java_args"]
            args = []
            for i in range(len(normal_args)-1):
                if normal_args[i] is None:
                    args.append(cached_java_objects[java_args[i]].obj)
                else: args.append(normal_args[i])
            try: result = construct(obj,args)
            except Exception as e:
                return_call({"ufcid":payload["ufcid"],"fail":True,"reason":str(e)})
                continue
            if can_jsonify(result):
                java_type = False
                value = result
                id = None
                name = None
                runtime_type_name = None
                runtime_type_id = None
            else:
                java_type = True
                value = None
                jo = JavaObject(result)
                id = jo.id
                name = str(jo.obj)
                runtime_type = resolve_type(jo)
                runtime_type_name = str(runtime_type.obj)
                runtime_type_id = runtime_type.id
            return_call({"ufcid":payload["ufcid"],"fail":False,"java_type":java_type,"value":value,"id":id,"name":name,"runtime_type":{"name":runtime_type_name,"id":runtime_type_id}})
        elif payload["type"] == 4: # request object {"ufcid":ufcid,"type":4,"uuid":uuid}
            if payload["uuid"] in __script__.vars["game"]["javapy"]:
                obj = __script__.vars["game"]["javapy"][payload["uuid"]]
                del __script__.vars["game"]["javapy"][payload["uuid"]]
                if can_jsonify(obj):
                    java_type = False
                    value = obj
                    id = None
                    name = None
                else:
                    java_type = True
                    value = None
                    jo = JavaObject(obj)
                    id = jo.id
                    name = jo.obj.getClass().getName()
                return_call({"ufcid":payload["ufcid"],"fail":False,"java_type":java_type,"value":value,"id":id,"name":name})
            else: return_call({"ufcid":payload["ufcid"],"fail":True,"reason":f"KeyError: {payload["uuid"]}"})
        elif payload["type"] == 5: # submit object {"ufcid":ufcid,"type":4,"obj_id":js[obj]["id"]}
            uuid = UUID.randomUUID().toString()
            __script__.vars["game"]["javapy"][uuid] = cached_java_objects[payload["obj_id"]]
            return_call({"ufcid":payload["ufcid"],"fail":False,"uuid":uuid})
        elif payload["type"] == 6: # Garbage collection
            try:
                del cached_java_objects[payload["id"]]
                return_call({"ufcid":payload["ufcid"],"fail":False})
            except Exception as e:
                return_call({"ufcid":payload["ufcid"],"fail":True,"reason":str(e)})
        elif payload["type"] == 7: # subscripting
            obj = cached_java_objects[payload["id"]].obj
            try:
                res = obj[payload["index"]]
                if can_jsonify(res):
                    java_type = False
                    id = None
                    name = None
                    value = res
                    runtime_type_name = None
                    runtime_type_id = None
                else:
                    java_type = True
                    jo = JavaObject(res)
                    id = jo.id
                    name = str(jo.obj)
                    value = None
                    runtime_type = resolve_type(jo)
                    runtime_type_name = str(runtime_type.obj)
                    runtime_type_id = runtime_type.id
                return_call({"ufcid":payload["ufcid"],"fail":False,"java_type":java_type,"value":value,"id":id,"name":name,"stop":False,"runtime_type":{"name":runtime_type_name,"id":runtime_type_id}})
            except Exception as e:
                if isinstance(e, ArrayIndexOutOfBoundsException) and payload["is_iter"]:
                    return_call({"ufcid":payload["ufcid"],"fail":False,"stop":True})
                else: return_call({"ufcid":payload["ufcid"],"fail":True,"reason":str(e)})
        elif payload["type"] == 8: # __len__
            obj = cached_java_objects[payload["id"]].obj
            try:
                length = len(obj)
                return_call({"ufcid":payload["ufcid"],"fail":False,"length":length})
            except Exception as e:
                return_call({"ufcid":payload["ufcid"],"fail":True,"reason":str(e)})
        elif payload["type"] == 9: # type res
            obj = cached_java_objects[payload["id"]]
            try:
                runtime_type = resolve_type(obj)
                return_call({"ufcid":payload["ufcid"],"fail":False,"name":str(runtime_type.obj),"id":runtime_type.id})
            except Exception as e:
                return_call({"ufcid":payload["ufcid"],"fail":True,"reason":str(e)})
        elif payload["type"] == 10: # FixedReturnFunction def
            if payload["java"]:
                returns = cached_java_objects[payload["returns"]].obj
            else: returns = payload["returns"]
            jo = JavaObject(lambda *_: returns)
            jo.java_return = payload["java"]
            runtime_type = resolve_type(jo)
            return_call({"ufcid":payload["ufcid"],"id":jo.id,"name":str(jo.obj),"runtime_type":{"id":runtime_type.id,"name":str(runtime_type.obj)},"fail":False})
        elif payload["type"] == 11: # grabs __script__ handle
            script = Minescript.loadPyjinnScript(JavaList(["__eval__.pyj"]), "from minescript import *")
            script.redirectStdout(__script__.stdout)
            script.redirectStderr(__script__.stderr)
            script.vars["game"] = __script__.vars["game"]
            scripts.append(script)
            script.exec()
            jo = JavaObject(script)
            runtime_type = resolve_type(jo)
            return_call({"ufcid":payload["ufcid"],"fail":False,"id":jo.id,"name":str(jo.obj),"runtime_type":{"name":str(runtime_type.obj),"id":runtime_type.id}})
        elif payload["type"] == 12: # __contains__ aka 'x in y'
            iterable_obj = cached_java_objects[payload["iterable_id"]].obj
            if payload["java_type"]: obj = cached_java_objects[payload["obj"]].obj
            else: obj = payload["obj"]
            try:
                result = obj in iterable_obj
                return_call({"ufcid":payload["ufcid"],"fail":False,"result":result})
            except Exception as e:
                return_call({"ufcid":payload["ufcid"],"fail":True,"reason":str(e)})
        elif payload["type"] == 13: # alt resolve method
            obj = cached_java_objects[payload["obj"]].obj
            if isinstance(obj, JavaClassType): clss = type(obj)
            else: clss = obj.getClass()
            try:
                for method in clss.getMethods():
                    if method.getName() == payload["method"]:
                        return_call({"ufcid":payload["ufcid"],"fail":False})
                        return
                raise Exception(f"NoSuchMethod: {obj} has no method named '{payload["method"]}'")
            except Exception as e:
                return_call({"ufcid":payload["ufcid"],"fail":True,"reason":str(e)})
        elif payload["type"] == 14: # alt resolve field
            obj = cached_java_objects[payload["obj"]]
            clss = get_type_class_of(obj)
            try:
                field = clss.getField(payload["field"]).get(obj.obj)
                if can_jsonify(field):
                    java_field = False
                    id = None
                    value = field
                    name = None
                    runtime_type = None
                else:
                    java_field = True
                    jo = JavaObject(field)
                    id = jo.id
                    value = None
                    name = str(jo.obj)
                    runtime_type = resolve_type(jo)
                return_call({"ufcid":payload["ufcid"],"fail":False,"java_field":java_field,"value":value,"id":id,"name":name,"runtime_type":{"name":str(runtime_type.obj),"id":runtime_type.id}})
            except Exception as e:
                return_call({"ufcid":payload["ufcid"],"fail":True,"reason":str(e)})
        else:
            return_call({"ufcid":payload["ufcid"],"fail":True,"reason":f"Javapy: Unexpected opcode: {payload["type"]}"})

__script__.atExit(lambda status: [script.exit(status) for script in scripts])

add_event_listener("render",_main)
""")
    except: pass
    script_loaded = True
Thread(target=__start__).start()

conn, _ = bridge.accept()
reader = conn.makefile("r", encoding="utf-8")
writer = conn.makefile("w", encoding="utf-8")

def __reader__():
    while True:
        line = reader.readline()
        data = json.loads(line)
        if data["ufcid"] in concurrent: concurrent.pop(data["ufcid"]).set_result(data)

def __garbage_collector__():
    while True:
        id = garbage.get()
        debug_log(f"Garbage collecting: {id}", level=8)
        run_call({"ufcid":0,"type":6,"id":id})
        debug_log(f"Garbage collected: {id}", level=8)

Thread(target=__reader__,daemon=True).start()
Thread(target=__garbage_collector__,daemon=True).start()

__script__ = PyjinnScript()

if TYPE_CHECKING:
    class FixedReturnFunction(JavaObject):
        def __init__(self, obj) -> JavaObject:
            """
            Creates a pyjinn function that has a fixed return value. This object can be passed down as arguments to java calls
        
            Equal to `lambda *_: obj`
            """

__all__ = [
    "JavaObject",
    "JavaMember",
    "JavaException"
    "type",
    "__script__",
    "FixedReturnFunction",
    "JavaType",
    "JavaMethod"
]