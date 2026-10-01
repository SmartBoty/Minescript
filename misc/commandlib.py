from system.lib.java import eval_pyjinn_script as eps
import socket
from threading import Thread, Lock
import json
import inspect
import uuid

registered = {}
write_lock = Lock()

bridge = socket.socket()
bridge.bind(("127.0.0.1", 0))
bridge.listen(1)
port = bridge.getsockname()[1]
script_loaded = False

eps(r"""
import atexit
import pyjinn_json as json
ClientCommands = JavaClass("net.fabricmc.fabric.api.client.command.v2.ClientCommands")
dispatcher = ClientCommands.getActiveDispatcher()
CommandNode = type(JavaClass("com.mojang.brigadier.tree.CommandNode"))
Component = JavaClass("net.minecraft.network.chat.Component")
mc = JavaClass("net.minecraft.client.Minecraft").getInstance()
Commands = JavaClass("net.minecraft.commands.Commands")
StringArgumentType = JavaClass("com.mojang.brigadier.arguments.StringArgumentType")
FloatArgumentType = JavaClass("com.mojang.brigadier.arguments.FloatArgumentType")
IntegerArgumentType = JavaClass("com.mojang.brigadier.arguments.IntegerArgumentType")
BoolArgumentType = JavaClass("com.mojang.brigadier.arguments.BoolArgumentType")
Socket = JavaClass("java.net.Socket")
BufferedWriter = JavaClass("java.io.BufferedWriter")
OutputStreamWriter = JavaClass("java.io.OutputStreamWriter")
StandardCharsets = JavaClass("java.nio.charset.StandardCharsets")
BufferedReader = JavaClass("java.io.BufferedReader")
InputStreamReader = JavaClass("java.io.InputStreamReader")

bridge = Socket("127.0.0.1", """ + str(port) + r""")
bridge.setSoTimeout(1)
writer = BufferedWriter(OutputStreamWriter(bridge.getOutputStream(), StandardCharsets.UTF_8))
reader = BufferedReader(InputStreamReader(bridge.getInputStream(), StandardCharsets.UTF_8))

class ManagedCommandCallback:
    def __init__(self, ufcid, name, arg_names):
        self.cancelled = False
        self.name = name
        self.arg_names = arg_names
        self.ufcid = ufcid

    def __call__(self,*args):
        if self.cancelled: return 0
        try:
            if len(args):
                ctx = args[0]
                try:
                    call_args = []
                    for name, type in self.arg_names:
                        if type == "varstr":
                            call_args += list(arg_types_extractors[type](ctx, name))
                        else: call_args.append(arg_types_extractors[type](ctx, name))
                except: call_args = []
                return_call({"ufcid":self.ufcid,"args":call_args})
                return 1
        except: return -1

    def cancel(self):
        self.cancelled = True
        on_exit(name=self.name)

registered_commands = []
arg_types = {
    "str": StringArgumentType.word(),
    "varstr": StringArgumentType.greedyString(),
    "float": FloatArgumentType.floatArg(),
    "int": IntegerArgumentType.integer(),
    "bool": BoolArgumentType.bool()
}
arg_types_extractors = {
    "str": lambda ctx, name: StringArgumentType.getString(ctx, name),
    "varstr": lambda ctx, name: StringArgumentType.getString(ctx, name).split(" "),
    "float": lambda ctx, name: FloatArgumentType.getFloat(ctx, name),
    "int": lambda ctx, name: IntegerArgumentType.getInteger(ctx, name),
    "bool": lambda ctx, name: BoolArgumentType.getBool(ctx, name)
}

def on_exit(*_,name=None):
    field = CommandNode.getDeclaredField("children")
    field.setAccessible(True)
    base_children = field.get(mc.getConnection().getCommands().getRoot())
    fabric_children = field.get(dispatcher.getRoot())
    if name is None:
        for name in registered_commands:
            base_children.remove(name)
            fabric_children.remove(name)
    else:
        fabric_children.remove(name)
    try: ClientCommands.refreshCommandCompletions()
    except: pass

def register_command(ufcid, name, arg_names):
    registered_commands.append(name)
    callback = ManagedCommandCallback(ufcid, name, arg_names)
    fabric_command = ClientCommands.literal(name).executes(callback)
    base_command = Commands.literal(name).executes(callback)
    for arg_name,type in arg_names:
        fabric_command.then(ClientCommands.argument(arg_name, arg_types[type]).executes(callback))
        base_command.then(Commands.argument(arg_name, arg_types[type]))
    dispatcher.register(fabric_command)
    mc.getConnection().getCommands().register(base_command)

def return_call(data):
    writer.write(json.dumps(data)+"\n")
    writer.flush()

atexit.register(on_exit)

def _main(_):
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
        if payload["type"] == 0: # Register new command
            register_command(payload["ufcid"], payload["name"], payload["arg_names"])
        elif payload["type"] == 1: pass # Unregister

add_event_listener("render",_main)
""")

conn, _ = bridge.accept()
reader = conn.makefile("r", encoding="utf-8")
writer = conn.makefile("w", encoding="utf-8")

def __reader__():
    while True:
        line = reader.readline()
        data = json.loads(line)
        if data["ufcid"] in registered:
            registered[data["ufcid"]](*data["args"])

Thread(target=__reader__,daemon=True).start()

supported_types = (str, int, float, bool)
var_types = (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL)
def command(func):
    ufcid = str(uuid.uuid1())
    arg_names = []
    for name, param in inspect.signature(func).parameters.items():
        if param.annotation in supported_types:
            if param.kind in var_types:
                if param.annotation == str: arg_names.append([name,"varstr"])
                else: raise TypeError(f"Command '{func.__name__}' may only have 'str' type varargs, not '{param.annotation.__name__}'")
            else:
                arg_names.append([name,param.annotation.__name__])
        else:
            raise TypeError(f"Command '{func.__name__}' cannot have argument of type '{param.annotation.__name__}'. Must be one of: str, int, float, bool")
    with write_lock:
        writer.write(json.dumps({"type":0,"name":func.__name__,"ufcid":ufcid,"arg_names":arg_names})+"\n")
        writer.flush()
    registered[ufcid] = func
    return func