from __future__ import annotations
import inspect
import ast
from functools import wraps
import json
from uuid import uuid4
from threading import get_ident, Thread, Lock
import socket
from system.lib.java import eval_pyjinn_script as eps
from concurrent.futures import Future
import sys
import os
from time import sleep
import builtins
from system.lib.minescript import log, echo

debug_level = 0
def debug_log(*msg,level=0):
    if (level <= debug_level or debug_level >= 9) and debug_level:
        op = log if debug_level < 9 else echo
        op(" ".join(msg))

concurrent = {}
registered_python_functions = {}
cached = []

class JavaObj:
    def __init__(self, path="", name=""):
        if path and name: self.__dict__["path"] = f"{path}.{name}"
        else: self.__dict__["path"] = path or name

    def __getattr__(self, name):
        if not name.startswith("__") and name.endswith("__"):
            return JavaObj(self.path, name)
        return self

    def __call__(self) -> JavaObj:
        raise AttributeError("Jynnton JavaObj is not callable in python context")

class JavaClass(JavaObj):
    def __init__(self, _class, name=None):
        self._class = _class
        writer.write(json.dumps({"type":5,"class":_class,"name":name if name is not None else _class.split(".")[-1].split("$")[-1]}, separators=(",", ":"))+"\n")
        writer.flush()

class JynntonCommonsMeta(type):
    @property
    def mc(self):
        code = 'mc = JavaClass("net.minecraft.client.Minecraft").getInstance()'
        writer.write(json.dumps({"type": 6, "code": code}, separators=(",", ":"))+"\n")

class JynntonCommons(metaclass=JynntonCommonsMeta): pass

class JynntonFlags:
    mc:str="common@mc"
    @staticmethod
    def JavaClass(_class): return f"class@{_class}"

class PyjinnContextLeave(Exception): pass
class InvalidPyjinnAccessError(Exception): pass
class DummyObject: pass

class Pyjinn:
    def __init__(self):
        self.lock = Lock()
        self.initialized = False
        self.id = None
    
    def __enter__(self, *_, **__):
        ufcid = f"{get_ident()}@{uuid4()}"
        self.future = Future()
        frame = inspect.currentframe().f_back
        src, start_line = inspect.getsourcelines(frame)
        current_line = frame.f_lineno - start_line
        with self.lock:
            if self.initialized is False or self.initialized == current_line:
                self.initialized = current_line
            else: raise InvalidPyjinnAccessError("Cannot reuse the same Pyjinn context manager!")
        if not self.id:
            self.id = f"{get_ident()}@{uuid4()}"
            debug_log(f"Entering uncached Pyjinn context: {self.id}")
            lines = []
            base_indent = None
            for line in src[current_line:]:
                stripped = line.lstrip()
                if not stripped or stripped.startswith("#") or stripped.startswith("with"): continue
                indent = len(line) - len(line.lstrip())
                if base_indent is None: base_indent = indent
                elif indent < base_indent: break
                lines.append(line)
            if lines[0].startswith("with"): lines = lines[1:]
            code = "".join((line[base_indent:] for line in lines))
            payload = {"type":7,"id":self.id,"ufcid":ufcid,"code":code}
            tree = ast.parse(code)
            #classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
            local_env = {}
            funcs = []
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    _register_pyjinn_function(node.name, ast.unparse(node), False, ())
                    exec(f"@static_decorate(\"{node.name}\",True,False)\ndef {node.name}(*args,**kwargs): pass", globals(), local_env)
                    funcs.append(node.name)
                elif isinstance(node, ast.AsyncFunctionDef):
                    _register_pyjinn_function(node.name, ast.unparse(node), True, ())
                    exec(f"@static_decorate(\"{node.name}\",True,True)\ndef {node.name}(*args,**kwargs): pass", globals(), local_env)
                    funcs.append(node.name)
            for func_name in funcs: setattr(builtins, func_name, local_env[func_name])
        else:
            debug_log(f"Entering cached Pyjinn context: {self.id}")
            payload = {"type":8,"id":self.id,"ufcid":ufcid}
        writer.write(json.dumps(payload, separators=(",", ":"))+"\n")
        writer.flush()
        concurrent[ufcid] = self.future
        def burn(frame, event, arg):
            if event == 'line': raise PyjinnContextLeave
            return burn
        sys.settrace(burn)
        frame.f_trace = burn
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.settrace(None)
        if exc_type is PyjinnContextLeave:
            payload = self.future.result()["payload"]
            for key, value in payload.items():
                _jynnton_globals.skip = True
                if key not in _jynnton_globals.names:
                    debug_log(f"Adding field '{key}' from __exit__")
                    JynntonGlobals.add_field(key,value)
                else:
                    debug_log(f"Setting field {key} to {value} from __exit__")
                    setattr(JynntonGlobals,key,value)
            debug_log(f"Returning from Pyjinn context: {self.id}, updated: {list(payload.keys())}")
            return True
        return False

class DynamicField:
    def __init__(self, name, value):
        debug_log(f"Adding field '{name}' from __init__")
        self.name = name
        self.value = value

    def __get__(self, instance, owner):
        debug_log(f"Grabbing '{self.name}'  from __get__")
        ufcid = f"{get_ident()}@{uuid4()}"
        future = Future()
        concurrent[ufcid] = future
        writer.write(json.dumps({"type":10,"ufcid":ufcid},separators=(",", ":"))+"\n")
        writer.flush()
        payload = future.result()["payload"]
        debug_log(f"Payload: '{payload}' from __get__")
        for key, value in payload.items():
            _jynnton_globals.skip = True
            if key not in _jynnton_globals.names:
                debug_log(f"Adding field '{key}' from __get__")
                instance.add_field(key,value)
            else:
                debug_log(f"Setting field {key} to {value} from __get__")
                setattr(instance,key,value)
        instance.__dict__[self.name] = payload[self.name]
        return payload[self.name]

    def __set__(self, instance, value):
        debug_log(f"Setting detected for '{self.name}' from __set__")
        if _jynnton_globals.skip:
            debug_log(f"Skipped setting '{self.name}' in pyjinn from __set__")
            _jynnton_globals.skip = False
        else:
            debug_log(f"Setting '{self.name}' in pyjinn from __set__")
            writer.write(json.dumps({"type":9,"name":self.name,"value":value},separators=(",", ":"))+"\n")
            writer.flush()
        instance.__dict__[self.name] = value

_jynnton_globals = DummyObject()
class _JynntonGlobals:
    def __init__(self):
        _jynnton_globals.names = []
        _jynnton_globals.skip = False

    def add_field(self,key,value):
        debug_log(f"Adding field {key} as {value} from add_field")
        _jynnton_globals.names.append(key)
        setattr(_JynntonGlobals, key, DynamicField(key,value))

    def __getattr__(self, name) -> _JynntonGlobals:
        if not name.startswith("__"):
            ufcid = f"{get_ident()}@{uuid4()}"
            future = Future()
            concurrent[ufcid] = future
            writer.write(json.dumps({"type":10,"ufcid":ufcid},separators=(",", ":"))+"\n")
            writer.flush()
            payload = future.result()["payload"]
            for key, value in payload.items():
                _jynnton_globals.skip = True
                if key not in _jynnton_globals.names:
                    JynntonGlobals.add_field(key,value)
                else: setattr(JynntonGlobals,key,value)
            self.__dict__[name] = payload[name]
            return payload[name]

    def __setattr__(self, name, value):
        if not name.startswith("__"):
            setattr(_JynntonGlobals, name, DynamicField(name,value))
            ufcid = f"{get_ident()}@{uuid4()}"
            writer.write(json.dumps({"type":9,"name":name,"value":value,"ufcid":ufcid},separators=(",", ":"))+"\n")
            writer.flush()
            future = Future()
            concurrent[ufcid] = future
            future.result()

def add_event_listener(event,func):
    payload = json.dumps({"type":4,"event":event,"name":func.__name__,"async":func.is_async}, separators=(",", ":"))
    writer.write(payload + "\n")
    writer.flush()

def register_python_function(func):
    try: returns = any(has_return(child) for child in ast.iter_child_nodes(ast.parse(inspect.getsource(func).split("\n",1)[-1]).body[0]))
    except: returns = True
    registered_python_functions[func.__name__] = func
    payload = json.dumps({"type":2, "funcs":[func.__name__], "returns":returns}, separators=(",", ":"))
    writer.write(payload + "\n")
    writer.flush()
    return func

def _register_pyjinn_function(name,src,is_async,include):
    writer.write(json.dumps({"type":0,"name":name,"code":src,"async":is_async,"include":include}, separators=(",", ":"))+"\n")
    writer.flush()

def call_function(name,is_async,returns,args,kwargs):
    debug_log(f"Calling '{name}' with: {args} {kwargs}")
    if returns: ufcid = f"{get_ident()}@{uuid4()}"
    else: ufcid = -1
    payload = json.dumps({"type":1,"name":name,"async":is_async,"returns":returns,"ufcid":ufcid,"args":args,"kwargs":kwargs}, separators=(",", ":"))
    writer.write(payload+"\n")
    writer.flush()
    if returns:
        future = Future()
        concurrent[ufcid] = future
        payload = future.result()
        debug_log(f"Returning from '{name}' with {payload["result"]}")
        if payload["fail"]: raise Exception(payload["result"])
        else: return payload["result"]

def has_return(node):
    if isinstance(node, ast.Return): return True
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and node: return False

def static_decorate(name, returns, is_async):
    def decorate(func):
        func.Jynnton_ID = str(uuid4())
        func.returns = returns
        func.name = name
        func.is_async = is_async
        @wraps(func)
        def wrapper(*args,**kwargs):
            return call_function(func.name,func.is_async,func.returns,args,kwargs)
        return wrapper
    return decorate
setattr(builtins, "static_decorate", static_decorate)

def as_pyjinn(*include:list[JynntonFlags]):
    if len(include) > 1:
        if isinstance(include[0], list): include = include[0]
    def decorate(func):
        code = inspect.getsource(func)
        code = code.split("\n",1)[-1]
        code_body = ast.parse(code).body
        for node in code_body:
            if isinstance(node, (ast.AsyncFunctionDef)):
                is_async = True
                name = node.name
            elif isinstance(node, (ast.FunctionDef)):
                is_async = False
                name = node.name
        func.Jynnton_ID = str(uuid4())
        func.returns = any(has_return(child) for child in ast.iter_child_nodes(code_body[0]))
        func.name = name
        func.is_async = is_async
        _register_pyjinn_function(name,code,is_async,include)
        @wraps(func)
        def wrapper(*args,**kwargs):
            return call_function(func.name,func.is_async,func.returns,args,kwargs)
        return wrapper
    return decorate

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
Minescript = JavaClass("net.minescript.common.Minescript")
BoundFunction = JavaClass("org.pyjinn.interpreter.Script$BoundFunction")
PyjClass = JavaClass("org.pyjinn.interpreter.Script$PyjClass")
Array = JavaClass("java.lang.reflect.Array")
Object = JavaClass("java.lang.Object")
HashMap = JavaClass("java.util.HashMap")
ClassLevelMethod = JavaClass("org.pyjinn.interpreter.Script$ClassLevelMethod")
CtorFunction = JavaClass("org.pyjinn.interpreter.Script$CtorFunction")
PyjClassContainer = JavaClass("org.pyjinn.interpreter.Script$PyjClassContainer")
Class = JavaClass("java.lang.Class")
Random = JavaClass("java.util.Random")()

def reflect_field(_class, field_name, raw=False):
    clss = _class.getClass()
    f = mappings.getRuntimeFieldName(clss, field_name)
    field = clss.getDeclaredField(f)
    field.setAccessible(True)
    if not raw: return field.get(_class)
    else: return field

def as_array(items,specific_type=Object):
    array = Array.newInstance(type(specific_type),len(items))
    for i,arg in enumerate(items):
        Array.set(array, i, arg)
    return array

def __init__(self,*_): return self

log("[Jynnton] Waking up ...")
bridge = Socket("127.0.0.1", """ + str(port) + r""")
bridge.setSoTimeout(1)
writer = BufferedWriter(OutputStreamWriter(bridge.getOutputStream(), StandardCharsets.UTF_8))
reader = BufferedReader(InputStreamReader(bridge.getInputStream(), StandardCharsets.UTF_8))
portid = "Jynnton_globals:" + str(""" + str(port) + r""")
pcc = type(PyjClassContainer).getDeclaredConstructor(as_array(["".getClass()],Class))
pcc.setAccessible(True)
if "Jynnton" not in __script__.vars["game"]: __script__.vars["game"]["Jynnton"] = {}
__script__.vars["game"]["Jynnton"][portid] = {}
__script__.vars["game"]["Jynnton"][portid]["returns"] = {}

cached_java_objects = []
common_includables = {
    "mc":'mc = JavaClass("net.minecraft.client.Minecraft").getInstance()'
}
cached_scripts = {}
class _JG: pass
JynntonGlobals = _JG()

def rebind_method(method,context=__script__.mainModule().globals()):
    return BoundFunction(method.functionDef(), context, method.defaults(), method.keywordDefaults(), method.code(), method.isCtor(), method.zombieCounter())

def rebind_class(_class,context=__script__.mainModule().globals()):
    name = reflect_field(_class,"name")
    ctor = reflect_field(_class,"ctor")
    isFrozen = reflect_field(_class,"isFrozen")
    instanceMethods = reflect_field(_class,"instanceMethods")
    classLevelMethods = reflect_field(_class,"classLevelMethods")
    hashMethod = reflect_field(_class,"hashMethod")
    strMethod = reflect_field(_class,"strMethod")
    new_instanceMethods = HashMap()
    newClassLevelMethods = HashMap()
    has_init = False
    for key in instanceMethods.keySet():
        if isinstance(instanceMethods.get(key), CtorFunction): has_init = instanceMethods.get(key) ; continue
        new_instanceMethods.put(key,rebind_method(instanceMethods.get(key),context))
    for key in classLevelMethods.keySet():
        newClassLevelMethods.put(key,ClassLevelMethod(classLevelMethods.get(key).isClassmethod(),rebind_method(classLevelMethods.get(key).function(),context)))
    if has_init:
        ctor = CtorFunction(has_init.type(), rebind_method(has_init.function()))
        return PyjClass(name, ctor, isFrozen, new_instanceMethods, newClassLevelMethods, hashMethod, strMethod)
    else:
        ctor = CtorFunction(pcc.newInstance(as_array([name])), __init__)
        return PyjClass(name, ctor, isFrozen, new_instanceMethods, newClassLevelMethods, hashMethod, strMethod)

class CodeScript:
    def __init__(self, code):
        self.code = code
        log(f"[Jynnton] Compiling src: \n{code}")
        self.script = Minescript.loadPyjinnScript(JavaList(["__exec__"]), code)
        self.script.redirectStdout(__script__.stdout)
        self.script.redirectStderr(__script__.stderr)
        for name in __script__.vars.keys(): self.script.vars[name] = __script__.vars[name]
        for key, value in __script__.mainModule().globals().vars().items():
            if key not in base_builtins or key == "JynntonGlobals":
                self.script.mainModule().globals().set(key,value)
    
    def run(self):
        log(f"[Jynnton] Adding code to glopal space:\n{self.code}")
        self.script.exec()
        for key, value in self.script.mainModule().globals().vars().items():
            if key not in base_builtins or key == "JynntonGlobals":
                if isinstance(value,BoundFunction): __script__.mainModule().globals().setBoundFunction(rebind_method(self.script.mainModule().globals().get(key)))
                elif isinstance(value,PyjClass): __script__.mainModule().globals().set(key, rebind_class(self.script.mainModule().globals().get(key)))
                else: __script__.mainModule().globals().set(key,value)
        self.script.exit(0)

def exec(code, run=True):
    script = CodeScript(code)
    if run: script.run()
    return script

def return_call(data):
    writer.write(json.dumps(data)+"\n")
    writer.flush()

async def run_async_function(name,ufcid,returns,args,kwargs):
    try: result = await __script__.mainModule().globals().get(name)(*args,**kwargs) ; fail = False
    except Exception as e: result = e.getMessage() ; fail = True
    if returns: return_call({"ufcid":ufcid,"result":result,"fail":fail})
    else: return_call({"ufcid":-1,"result":result,"fail":fail})

def _main(_):
    global cached_scripts, JynntonGlobals
    lines = []
    iters = 0
    while True:
        iters += 1
        if iters > 50: log("[Jynnton] Overloaded! Exiting reader...") ; break
        try:
            line = reader.readLine()
            if line: lines.append(line)
            else: break
        except Exception as e:
            if "SocketTimeout" not in str(e): log(f"[Jynnton] Exception caught! {e}")
            break
    for line in lines:
        payload = json.loads(line)
        if payload["type"] == 0: # Function init -> {"type":0,"name":name,"code":src,"async":is_async,"include":include}
            code = payload["code"]
            for includable in payload["include"]:
                typ,val = includable.split("@")
                if val not in cached_java_objects:
                    cached_java_objects.append(val)
                    if typ == "common": code += f"\n{common_includables[val]}"
                    elif typ == "class": code += f'\n{val.split(".")[-1]} = JavaClass("{val}")'
            exec(code)
        elif payload["type"] == 1: # Function call -> {"type":1,"name":name,"async":is_async,"returns":returns,"ufcid":ufcid,"args":args,"kwargs":kwargs}
            name = payload["name"]
            if payload["async"]: run = lambda: EventLoop().run(lambda this: run_async_function(name,payload["ufcid"],payload["returns"],payload["args"],payload["kwargs"]))
            else: run = lambda: __script__.mainModule().globals().get(name)(*payload["args"],**payload["kwargs"])
            try: result = run() ; fail = False
            except Exception as e: result = e.getMessage() ; fail = True
            if not payload["async"]: return_call({"ufcid":payload["ufcid"],"result":result,"fail":fail})
        elif payload["type"] == 2: # Python function register -> {"type":2,"funcs":out}
            for func in payload["funcs"]:
                code = (
'''
async def ''' + func + '''(*args,**kwargs):
    ufcid = str(Random.nextInt())
    return_call({"ufcid":ufcid,"func":"''' + func + '''","args":args,"kwargs":kwargs,"returns": ''' + str(payload["returns"]) + '''})
    while ''' + str(payload["returns"]) + ''':
        el = EventLoop()
        await el.sleep(0)
        if ufcid in [key for key in __script__.vars["game"]["Jynnton"][portid]["returns"]]:
            dat = __script__.vars["game"]["Jynnton"][portid]["returns"][ufcid]
            del __script__.vars["game"]["Jynnton"][portid]["returns"][ufcid]
            return dat
''')
                log(f"[Jynnton] Adding Python function to global space: \n{code}")
                exec(code)
        elif payload["type"] == 3: # Python func return -> {"type":3,"result":globals().get(data["func"])(),"ufcid":data["ufcid"]}
            __script__.vars["game"]["Jynnton"][portid]["returns"][payload["ufcid"]] = payload["result"]
        elif payload["type"] == 4: # add_event_listener {"type":4,"event":event,"name":func.__name__,"async":is_async}
            if payload["async"]: add_event_listener(payload["event"],lambda event: EventLoop().run(lambda this: run_async_function(payload["name"],-1,False,[event],{}))) # name,ufcid,returns,args,kwargs
            else: add_event_listener(payload["event"],__script__.mainModule().globals().get(payload["name"]))
        elif payload["type"] == 5: # javaclass register -> {"type":5,"class":_class,"name":name if name is not None else _class.split(".")[-1].split("$")[-1]}
            exec(f'{payload["name"]} = JavaClass("{payload["class"]}")')
        elif payload["type"] == 6: # plain ace -> {"type":6,"code":code}
            exec(payload["code"])
        elif payload["type"] == 7: # uncached ace
            cached_scripts[payload["id"]] = exec(payload["code"],False)
            cached_scripts[payload["id"]].run()
            return_call({"ufcid":payload["ufcid"],"payload":JynntonGlobals.__dict__})
        elif payload["type"] == 8: # cached ace
            cached_scripts[payload["id"]].run()
            return_call({"ufcid":payload["ufcid"],"payload":JynntonGlobals.__dict__})
        elif payload["type"] == 9: # set global
            JynntonGlobals.__dict__[payload["name"]] = payload["value"]
            return_call({"ufcid":payload["ufcid"]})
        elif payload["type"] == 10: # Sync globals
            return_call({"ufcid":payload["ufcid"],"payload":JynntonGlobals.__dict__})

__atexit_register__(lambda: return_call({"ufcid":-2}))

base_builtins = ["builtins"] + list(__script__.mainModule().globals().vars().keys()) + [reflect_field(builtin,"name") for builtin in reflect_field(__script__.mainModule().globals(),"BUILTINS")] + ["__has_explicit_Minescript_import__","set_chat_input","player_hand_items","get_block","echo","player_press_drop","player_press_forward","player_press_sneak","getblock","_SleepRequest","__script__","ManagedCallback","player_inventory_select_slot","getblocklist","screen_name","player_name","player_orientation","get_entities","_System","Script","add_event_listener","BlockPacker","player_get_targeted_entity","players","player_press_left","get_player","execute","get_block_region","echo_json","player_press_attack","__name__","set_interval","append_chat_history","player_get_targeted_block","container_get_items","log","job_info","_EventRequest","show_chat_screen","screenshot","sys","player_press_jump","player_press_backward","player_set_orientation","chat_input","player_position","BlockPack","player_press_pick_item","_Coroutine","Minescript","BlockRegion","player","player_press_sprint","player_press_right","remove_event_listener","player_inventory","player_look_at","player_press_swap_hands","version_info","get_players","Rotation","Rotations","get_block_list","combine_rotations","set_timeout","EventLoop","press_key_bind","entities","chat","player_health","_RuntimeException","world_info","player_press_use"]
log("[Jynnton] Starting main loop")
add_event_listener("render",_main)
""")

conn, _ = bridge.accept()
reader = conn.makefile("r", encoding="utf-8")
writer = conn.makefile("w", encoding="utf-8")

JynntonGlobals = _JynntonGlobals()

def __reader__():
    while True:
        line = reader.readline()
        data = json.loads(line)
        if data["ufcid"] in concurrent: concurrent.pop(data["ufcid"]).set_result(data)
        elif data["ufcid"] == 0:
            sys.stderr.write(f"Developer exception (How have you managed to do this?):\n{data["result"]}")
            os._exit(-1)
        elif data["ufcid"] == -1:
            if data["fail"]:
                sys.stderr.write((f"The following could not be raised on the main thread:\n{data["result"]}\n \nNOTICE:\n The above error is the result of a non returning function call from Jynnton. For debugging purposes, add a 'return' to it",)[0])
                os._exit(-1)
        elif data["ufcid"] == -2: os._exit(0)
        elif data["ufcid"]:
            res = registered_python_functions[data["func"]](*data["args"],**data["kwargs"])
            if data["returns"]:
                writer.write(json.dumps({"type":3,"result":res,"ufcid":data["ufcid"]},separators=(",", ":"))+"\n")
                writer.flush()

Thread(target=__reader__,daemon=True).start()
Thread(target=lambda: sleep(1), daemon=False).start()
