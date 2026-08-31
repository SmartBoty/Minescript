from __future__ import annotations
import socket
from system.lib.java import eval_pyjinn_script as eps
from uuid import uuid4
from threading import get_ident, Thread, Lock
import json
from concurrent.futures import Future
from system.lib.minescript import log, echo
from weakref import WeakKeyDictionary
from time import sleep
from queue import Queue

concurrent = {}
js = WeakKeyDictionary()
garbage_lock = Lock()
garbage = Queue()

debug_level = 0
def debug_log(*msg,level=0):
    if (level <= debug_level or debug_level >= 9) and debug_level:
        op = log if (not debug_level >= 9) or level == debug_level else echo
        op(" ".join(msg))

def next_ufcid(): return f"{get_ident()}@{uuid4()}"

call_lock = Lock()
def run_call(data:dict):
    with call_lock:
        writer.write(json.dumps(data)+"\n")
    writer.flush()
    future = Future()
    concurrent[data["ufcid"]] = future
    result = future.result()
    if result["fail"]: raise JavaException(result["reason"])
    return result

def request_object(uuid) -> JavaObject:
    debug_log(f"Requesting object: {uuid}")
    ufcid = next_ufcid()
    result = run_call({"ufcid":ufcid,"type":4,"uuid":uuid})
    if not result["java_type"]: return result["value"]
    else: return JavaObject(result["id"],result["name"])

def submit_object(obj):
    debug_log(f"Submitting object: {repr(obj)}")
    ufcid = next_ufcid()
    result = run_call({"ufcid":ufcid,"type":5,"obj_id":js[obj]["id"]})
    return result["uuid"]

def resolve_class(clss:str):
    debug_log(f"Resolving class: {clss}")
    ufcid = next_ufcid()
    result = run_call({"ufcid":ufcid,"type":0,"class":clss})
    return result["id"], result["name"]

def resolve_member(member:str,obj:JavaObject):
    debug_log(f"Resolving member {member} of {repr(obj)}")
    ufcid = next_ufcid()
    result = run_call({"ufcid":ufcid,"type":1,"member":member,"obj_id":js[obj]["id"]}) # {"ufcid":payload["ufcid"],"fail":False,"field":True,"java_field":True,"value":None,"id":jo.id,"name":str(jo.obj)}
    if result["field"]:
        if not result["java_field"]: return result["value"]
        else: return JavaObject(result["id"],result["name"])
    else: return JavaMethod(obj,member)

def normalize_items(items):
    out_normal = []
    out_java = []
    for item in items:
        if isinstance(item, JavaObject):
            out_normal.append(None)
            out_java.append(js[item]["id"])
        else:
            out_normal.append(item)
            out_java.append(None)
    return out_normal, out_java

class JavaException(Exception): pass

class JavaObject:
    def __init__(self, id, name):
        js[self] = {}
        js[self]["id"] = id
        js[self]["name"] = name
        js[self]["type"] = "JavaObject"

    def __str__(self):
        return f"{js[self]["id"]} {js[self]["name"]}"

    def __repr__(self):
        return f"<{js[self]["type"]} {js[self]["name"]}>"

    def __call__(self,*args) -> JavaObject:
        debug_log(f"Resolving constructor call of {js[self]["name"]}{args}")
        ufcid = next_ufcid()
        normal_args, java_args = normalize_items(args)
        result = run_call({"ufcid":ufcid,"type":3,"obj_id":js[self]["id"],"args":normal_args,"java_args":java_args})
        if not result["java_type"]: return result["value"]
        else: return JavaObject(result["id"],result["name"])

    def __getattr__(self, name:str) -> JavaObject:
        return resolve_member(name, self)

    def __del__(self):
        #echo(f"Garbage collecting: {js[self]["id"]}")
        garbage.put(js[self]["id"])

class JavaMethod(JavaObject):
    def __init__(self, parent:JavaObject, name:str):
        js[self] = {}
        js[self]["type"] = "JavaMethod"
        js[self]["parent"] = parent
        js[self]["id"] = -1
        js[self]["name"] = name

    def __call__(self, *args) -> JavaObject:
        debug_log(f"Resolving method call of {js[js[self]["parent"]]["name"]}.{js[self]["name"]}{args}")
        ufcid = next_ufcid()
        normal_args, java_args = normalize_items(args)
        result = run_call({"ufcid":ufcid,"type":2,"method":js[self]["name"],"obj_id":js[js[self]["parent"]]["id"],"args":normal_args,"java_args":java_args})
        if not result["java_type"]: return result["value"]
        else: return JavaObject(result["id"],result["name"])

    def __del__(self): pass

class JavaClass(JavaObject):
    def __init__(self, clss):
        id, name = resolve_class(clss)
        js[self] = {}
        js[self]["id"] = id
        js[self]["name"] = name
        js[self]["type"] = "JavaClass"

bridge = socket.socket()
bridge.bind(("127.0.0.1", 0))
bridge.listen(1)
port = bridge.getsockname()[1]

script = eps(
r"""
import pyjinn_json as json
Socket = JavaClass("java.net.Socket")
BufferedWriter = JavaClass("java.io.BufferedWriter")
OutputStreamWriter = JavaClass("java.io.OutputStreamWriter")
StandardCharsets = JavaClass("java.nio.charset.StandardCharsets")
BufferedReader = JavaClass("java.io.BufferedReader")
InputStreamReader = JavaClass("java.io.InputStreamReader")
mappings = JavaClass("net.minescript.common.Minescript").mappingsLoader.get()
Class = JavaClass("java.lang.Class")
Array = JavaClass("java.lang.reflect.Array")
Object = JavaClass("java.lang.Object")
JavaClassType = JavaClass("org.pyjinn.interpreter.JavaClass")
UUID = JavaClass("java.util.UUID")
TypeChecker = JavaClass("org.pyjinn.interpreter.Script$TypeChecker")
mappings = JavaClass("net.minescript.common.Minescript").mappingsLoader.get()
Set = JavaClass("java.util.Set")

def as_array(items,specific_type=Object):
    array = Array.newInstance(type(specific_type),len(items))
    for i,arg in enumerate(items):
        Array.set(array, i, arg)
    return array

def as_class_array(items):
    array = Array.newInstance(type(Class),len(items))
    for i, arg in enumerate(items):
        if isinstance(arg, JavaClassType): arg = type(arg)
        elif not isinstance(arg, Class): arg = arg.getClass()
        Array.set(array, i, arg)
    return array

def can_jsonify(obj):
    try: json.dumps(obj)
    except: return False
    if isinstance(obj, (type(0),type(""),type(True),type([]))): return True
    return False

def return_call(data):
    writer.write(json.dumps(data)+"\n")
    writer.flush()

def next_id():
    global current_id
    current_id += 1
    return current_id

def invoke(self,method,args):
    static = True
    if self.type == "JavaClass": clss = self.obj
    elif isinstance(self.obj, JavaClassType): clss = type(self.obj)
    else:
        clss = self.obj.getClass()
        static = False
    classes = as_class_array(args)
    array_args = as_array(args)
    m = TypeChecker.findBestMatchingMethod(clss, static, lambda*_:Set.of(method), method, classes, None)
    if not m.isEmpty():
        if static: result = m.get().invoke(__script__.mainModule().globals(),clss,array_args)
        else: result = m.get().invoke(__script__.mainModule().globals(),self.obj,array_args)
        return result
    raise Exception(f"NoSuchMethod: {method}({str(classes)[1:-1]})")

def construct(self,args):
    static = True
    if self.type == "JavaClass": clss = self.obj
    elif isinstance(self.obj, JavaClassType): clss = type(self.obj)
    else:
        clss = self.obj.getClass()
        static = False
    classes = as_class_array(args)
    array_args = as_array(args)
    ctor = TypeChecker.findBestMatchingConstructor(clss, classes, None)
    if not ctor.isEmpty():
        if static: result = ctor.get().newInstance(__script__.mainModule().globals(),array_args)
        else: result = ctor.get().newInstance(__script__.mainModule().globals(),array_args)
        return result
    return Exception(f"NoSuchConstructor: {str(classes)[1:-1]}")

class JavaClassObject:
    def __init__(self, clss):
        self.obj = Class.forName(mappings.getRuntimeClassName(clss))
        self.id = next_id()
        cached_java_objects[self.id] = self
        self.type = "JavaClass"

class JavaObject:
    def __init__(self, obj):
        self.obj = obj
        self.id = next_id()
        cached_java_objects[self.id] = self
        self.type = "JavaObject"

bridge = Socket("127.0.0.1", """ + str(port) + r""")
bridge.setSoTimeout(1)
writer = BufferedWriter(OutputStreamWriter(bridge.getOutputStream(), StandardCharsets.UTF_8))
reader = BufferedReader(InputStreamReader(bridge.getInputStream(), StandardCharsets.UTF_8))
current_id = -1
cached_java_objects = {}
if "javapy" not in __script__.vars["game"]: __script__.vars["game"]["javapy"] = {}

def _main(_):
    global cached_java_objects
    lines = []
    iters = 0
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
                return_call({"ufcid":payload["ufcid"],"id":jco.id,"name":jco.obj.getName(),"fail":False})
            except Exception as e:
                return_call({"ufcid":payload["ufcid"],"fail":True,"reason":e.getMessage()})
        elif payload["type"] == 1: # resolve member {"ufcid":ufcid,"type":1,"member":member,"obj_id":obj.id}
            obj = cached_java_objects[payload["obj_id"]]
            if obj.type == "JavaClass":
                object = obj.obj
            elif isinstance(obj.obj, JavaClassType): object = type(obj.obj)
            else: object = obj.obj.getClass()
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
                else:
                    java_field = True
                    jo = JavaObject(field)
                    id = jo.id
                    value = None
                    name = str(jo.obj)
                return_call({"ufcid":payload["ufcid"],"fail":False,"field":True,"java_field":java_field,"value":value,"id":id,"name":name})
            elif got_method:
                return_call({"ufcid":payload["ufcid"],"fail":False,"field":False,"java_field":None,"value":None,"id":None,"name":None})
            else: return_call({"ufcid":payload["ufcid"],"fail":True,"reason":f"NoSuchMemberException: {obj.obj} has no member named {payload["member"]}"})
        elif payload["type"] == 2: # method call {"ufcid":ufcid,"type":2,"method":js[self]["name"],"obj_id":js[js[self]["parent"]]["id"],"args":normal_args,"java_args":java_args}
            obj = cached_java_objects[payload["obj_id"]]
            normal_args = payload["args"]
            java_args = payload["java_args"]
            args = []
            for i in range(len(normal_args)):
                if normal_args[i] is None:
                    args.append(cached_java_objects[java_args[i]].obj)
                else: args.append(normal_args[i])
            try: result = invoke(obj,payload["method"],args)
            except Exception as e:
                return_call({"ufcid":payload["ufcid"],"fail":True,"reason":e.getMessage()})
                continue
            if can_jsonify(result):
                json.dumps(result)
                java_type = False
                value = result
                id = None
                name = None
            else:
                java_type = True
                value = None
                jo = JavaObject(result)
                id = jo.id
                name = str(jo.obj)
            return_call({"ufcid":payload["ufcid"],"fail":False,"java_type":java_type,"value":value,"id":id,"name":name})
        elif payload["type"] == 3: # constructor call {"ufcid":ufcid,"type":3,"obj_id":js[self]["id"],"args":normal_args,"java_args":java_args}
            obj = cached_java_objects[payload["obj_id"]]
            normal_args = payload["args"]
            java_args = payload["java_args"]
            args = []
            for i in range(len(normal_args)-1):
                if normal_args[i] is None:
                    args.append(cached_java_objects[java_args[i]].obj)
                else: args.append(normal_args[i])
            try: result = construct(obj,args).obj
            except Exception as e:
                return_call({"ufcid":payload["ufcid"],"fail":True,"reason":e.getMessage()})
                continue
            if can_jsonify(result):
                java_type = False
                value = result
                id = None
                name = None
            else:
                java_type = True
                value = None
                jo = JavaObject(result)
                id = jo.id
                name = str(jo.obj)
            return_call({"ufcid":payload["ufcid"],"fail":False,"java_type":java_type,"value":value,"id":id,"name":name})
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
                return_call({"ufcid":payload["ufcid"],"fail":True,"reason":e.getMessage()})

add_event_listener("render",_main)
""")

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
        debug_log(f"Garbage collecting: {id}")
        run_call({"ufcid":0,"type":6,"id":id})
        debug_log(f"Garbage collected: {id}", level=8)

Thread(target=__reader__,daemon=True).start()
Thread(target=__garbage_collector__,daemon=True).start()